import sys
import time
import logging
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from mss import mss
from PIL import Image, ImageDraw
import pytesseract

# Adjust imports based on project structure
# Assuming this file is in component/ and needs to import from core/
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.translate_core import TranslationService
from core.dbmanager import get_db_manager

class TextStabilizer:
    def __init__(self, history_size=5, stability_threshold=3):
        self.history = [] # List of lists of text blocks
        self.history_size = history_size
        self.stability_threshold = stability_threshold

    def add_frame(self, text_blocks):
        self.history.append(text_blocks)
        if len(self.history) > self.history_size:
            self.history.pop(0)

    def get_stable_blocks(self):
        if not self.history:
            return []

        candidates = self.history[-1]
        stable_blocks = []

        for candidate in candidates:
            matches = 0
            for frame in self.history[:-1]:
                for block in frame:
                    if self.is_similar(candidate, block):
                        matches += 1
                        break
            
            if matches >= self.stability_threshold - 1:
                stable_blocks.append(candidate)
        
        return stable_blocks

    def is_similar(self, block1, block2):
        x_overlap = max(0, min(block1['x'] + block1['w'], block2['x'] + block2['w']) - max(block1['x'], block2['x']))
        y_overlap = max(0, min(block1['y'] + block1['h'], block2['y'] + block2['h']) - max(block1['y'], block2['y']))
        area1 = block1['w'] * block1['h']
        area2 = block2['w'] * block2['h']
        
        overlap_area = x_overlap * y_overlap
        if overlap_area < 0.5 * min(area1, area2): 
            return False
        return True 

class TranslationWorker(QThread):
    result_ready = pyqtSignal(list)
    request_hide = pyqtSignal(bool)
    
    def __init__(self, monitor, source_lang, target_lang, logger, stop_event):
        super().__init__()
        self.monitor = monitor
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.logger = logger
        self.stop_event = stop_event
        self.translator = None
        self.db_manager = None
        self.stabilizer = TextStabilizer(history_size=5, stability_threshold=3)
        self.last_image_hash = None
        self.last_translations = []
        self.active_blocks = [] # List of {'text': ..., 'rect': [x,y,w,h], 'misses': 0, 'hash': ..., 'stable_frames': 0}
        self.max_block_misses = 8 # Increased for better stability

    def get_image_diff(self, img1, img2):
        """Calculate difference between two images using simple MSE on thumbnails"""
        if img1 is None or img2 is None: return 1.0
        
        # Resize to small thumbnail for fast comparison
        thumb1 = img1.resize((64, 64), Image.Resampling.NEAREST).convert('L')
        thumb2 = img2.resize((64, 64), Image.Resampling.NEAREST).convert('L')
        
        arr1 = np.array(thumb1)
        arr2 = np.array(thumb2)
        
        mse = np.mean((arr1 - arr2) ** 2)
        return mse

    def group_lines(self, data):
        """Group words into paragraphs based on proximity"""
        n_boxes = len(data['text'])
        
        valid_boxes = []
        for i in range(n_boxes):
            if int(data['conf'][i]) > 40 and data['text'][i].strip(): # Slightly lower confidence for paragraph parts
                valid_boxes.append({
                    'text': data['text'][i].strip(),
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'w': data['width'][i],
                    'h': data['height'][i]
                })
        
        if not valid_boxes:
            return []
            
        valid_boxes.sort(key=lambda b: (b['y'], b['x']))
        
        # Step 1: Merge into lines
        lines = []
        current_line = []
        
        for box in valid_boxes:
            if not current_line:
                current_line.append(box)
                continue
                
            last_box = current_line[-1]
            y_diff = abs(box['y'] - last_box['y'])
            height_avg = (box['h'] + last_box['h']) / 2
            x_dist = box['x'] - (last_box['x'] + last_box['w'])
            
            # Use a slightly more relaxed horizontal threshold for lines
            if y_diff < height_avg * 0.7 and x_dist < height_avg * 3:
                current_line.append(box)
            else:
                lines.append(self.merge_line(current_line))
                current_line = [box]
        
        if current_line:
            lines.append(self.merge_line(current_line))
            
        # Step 2: Merge lines into paragraphs (User-provided logic)
        y_threshold = 25 
        if not lines:
            return []

        # Sort by Vertical Position (already mostly sorted, but ensuring)
        sorted_boxes = sorted(lines, key=lambda b: b['y'])
        
        paragraphs = []
        current_block = sorted_boxes[0].copy()

        for i in range(1, len(sorted_boxes)):
            next_box = sorted_boxes[i]
            
            # Distance check
            current_bottom = current_block['y'] + current_block['h']
            gap = next_box['y'] - current_bottom
            
            # Logical check for merging
            # We add a horizontal check to prevent merging different columns
            x_dist = max(0, max(current_block['x'], next_box['x']) - min(current_block['x'] + current_block['w'], next_box['x'] + next_box['w']))
            
            if gap < y_threshold and x_dist < 50:
                # Merge them
                new_bottom = max(current_bottom, next_box['y'] + next_box['h'])
                current_block['text'] += "\n" + next_box['text']
                current_block['h'] = new_bottom - current_block['y']
                
                # Expand width
                max_right = max(current_block['x'] + current_block['w'], next_box['x'] + next_box['w'])
                current_block['x'] = min(current_block['x'], next_box['x'])
                current_block['w'] = max_right - current_block['x']
            else:
                paragraphs.append(current_block)
                current_block = next_box.copy()

        paragraphs.append(current_block)
        return self.lock_blocks(paragraphs)

    def lock_blocks(self, current_blocks):
        """Snap blocks to their previous positions and handle persistence with deduplication"""
        threshold = 30 # Slightly increased
        alpha = 0.4 
        
        new_active_blocks = []
        matched_prev_indices = set()
        
        # Helper to calculate how much one rect is contained in another
        def get_containment(r1, r2):
            x1 = max(r1[0], r2[0])
            y1 = max(r1[1], r2[1])
            x2 = min(r1[0] + r1[2], r2[0] + r2[2])
            y2 = min(r1[1] + r1[3], r2[1] + r2[3])
            
            intersection = max(0, x2 - x1) * max(0, y2 - y1)
            area = r1[2] * r1[3]
            if area == 0: return 0
            return intersection / area

        def get_iou(r1, r2): 
            x1 = max(r1[0], r2[0])
            y1 = max(r1[1], r2[1])
            x2 = min(r1[0] + r1[2], r2[0] + r2[2])
            y2 = min(r1[1] + r1[3], r2[1] + r2[3])
            
            intersection = max(0, x2 - x1) * max(0, y2 - y1)
            area1 = r1[2] * r1[3]
            area2 = r2[2] * r2[3]
            union = area1 + area2 - intersection
            
            return intersection / union if union > 0 else 0

        for curr in current_blocks:
            curr_rect = [curr['x'], curr['y'], curr['w'], curr['h']]
            
            # 1. DEDUPLICATION: If this new block is almost entirely contained in any already accepted block, skip it
            is_dupe = False
            for existing in new_active_blocks:
                if get_containment(curr_rect, existing['rect']) > 0.85:
                    is_dupe = True
                    break
            if is_dupe: continue

            # 2. MATCHING: Find best existing block to update
            curr_center_x = curr['x'] + curr['w'] / 2
            curr_center_y = curr['y'] + curr['h'] / 2
            best_prev_idx = -1
            best_score = 0
            
            for i, prev in enumerate(self.active_blocks):
                if i in matched_prev_indices: continue
                
                prev_rect = prev['rect']
                iou = get_iou(curr_rect, prev_rect)
                
                prev_center_x = prev_rect[0] + prev_rect[2] / 2
                prev_center_y = prev_rect[1] + prev_rect[3] / 2
                dist = ((curr_center_x - prev_center_x)**2 + (curr_center_y - prev_center_y)**2)**0.5
                
                score = iou * 100 + (100 - dist if dist < threshold else 0)
                
                if score > best_score:
                    best_score = score
                    best_prev_idx = i
            
            if best_prev_idx != -1:
                prev = self.active_blocks[best_prev_idx]
                prev_rect = prev['rect']
                stable_frames = prev.get('stable_frames', 0) + 1
                
                # MOVEMENT LOCK: If very stable, ignore tiny shifts
                dist_moved = ((curr['x'] - prev_rect[0])**2 + (curr['y'] - prev_rect[1])**2)**0.5
                if stable_frames > 5 and dist_moved < 5:
                    new_rect = prev_rect
                else:
                    new_rect = [
                        int(prev_rect[0] * (1-alpha) + curr['x'] * alpha),
                        int(prev_rect[1] * (1-alpha) + curr['y'] * alpha),
                        int(prev_rect[2] * (1-alpha) + curr['w'] * alpha),
                        int(prev_rect[3] * (1-alpha) + curr['h'] * alpha)
                    ]
                
                new_active_blocks.append({
                    'text': curr['text'],
                    'rect': new_rect,
                    'misses': 0,
                    'hash': hash(curr['text']),
                    'stable_frames': stable_frames
                })
                matched_prev_indices.add(best_prev_idx)
            else:
                new_active_blocks.append({
                    'text': curr['text'],
                    'rect': curr_rect,
                    'misses': 0,
                    'hash': hash(curr['text']),
                    'stable_frames': 0
                })
        
        # Keep missed blocks if they aren't covered by new ones
        for i, prev in enumerate(self.active_blocks):
            if i not in matched_prev_indices and prev['misses'] < self.max_block_misses:
                has_replacement = False
                for newly_added in new_active_blocks:
                    if get_containment(prev['rect'], newly_added['rect']) > 0.7:
                        has_replacement = True
                        break
                
                if not has_replacement:
                    prev['misses'] += 1
                    prev['stable_frames'] = max(0, prev.get('stable_frames', 0) - 1)
                    new_active_blocks.append(prev)
                
        self.active_blocks = new_active_blocks
        return [{'text': b['text'], 'x': b['rect'][0], 'y': b['rect'][1], 'w': b['rect'][2], 'h': b['rect'][3]} for b in self.active_blocks]

    def merge_line(self, words):
        full_text = " ".join([w['text'] for w in words])
        x = words[0]['x']
        y = words[0]['y']
        w = (words[-1]['x'] + words[-1]['w']) - x
        h = max([w['h'] for w in words])
        return {'text': full_text, 'x': x, 'y': y, 'w': w, 'h': h}

    def merge_blocks(self, block1, block2):
        full_text = block1['text'] + "\n" + block2['text']
        x = min(block1['x'], block2['x'])
        y = min(block1['y'], block2['y'])
        w = max(block1['x'] + block1['w'], block2['x'] + block2['w']) - x
        h = (block2['y'] + block2['h']) - y
        return {'text': full_text, 'x': x, 'y': y, 'w': w, 'h': h}

    def run(self):
        try:
            self.translator = TranslationService()
            self.db_manager = get_db_manager()
            self.logger.info("Translation Service & DB Initialized")
        except Exception as e:
            self.logger.error(f"Failed to init services: {e}")
            return

        last_img = None

        with mss() as sct:
            while not self.stop_event.is_set():
                try:
                    # Capture screen while overlay is visible
                    sct_img = sct.grab(self.monitor)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                    
                    # DIGITAL MASKING: Erase the overlay's vision from the capture
                    draw = ImageDraw.Draw(img)
                    img_w, img_h = img.size
                    for block in self.active_blocks:
                        r = block['rect']
                        # Calculate coordinates carefully and ensure x1 >= x0, y1 >= y0
                        # r is [x, y, w, h]
                        x0 = max(0, r[0] - 8)
                        y0 = max(0, r[1] - 8)
                        x1 = min(img_w, r[0] + r[2] + 8)
                        y1 = min(img_h, r[1] + r[3] + 8)
                        
                        if x1 > x0 and y1 > y0:
                            draw.rectangle([x0, y0, x1, y1], fill="black")
                    
                    if self.stop_event.is_set(): break

                    # Check for screen changes
                    if last_img:
                        diff = self.get_image_diff(last_img, img)
                        if diff < 5.0: # Threshold for "no significant change"
                            # Screen is static, sleep and skip OCR
                            time.sleep(0.2)
                            continue
                    
                    last_img = img.copy()

                    # OCR
                    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                    
                    if self.stop_event.is_set(): break

                    # Group into lines
                    lines = self.group_lines(data)
                    
                    # Stabilize
                    self.stabilizer.add_frame(lines)
                    stable_lines = self.stabilizer.get_stable_blocks()
                    
                    translations = []
                    
                    for line in stable_lines:
                        if self.stop_event.is_set(): break
                        
                        text = line['text'].strip()
                        if not text: continue

                        x, y, w, h = line['x'], line['y'], line['w'], line['h']
                        
                        # Check DB Cache
                        cached = self.db_manager.get_cached_translation(text, self.source_lang, self.target_lang)
                        if cached:
                            translations.append((cached, (x, y, w, h)))
                            continue

                        # Translate via API
                        try:
                            translated = self.translator.translate(
                                text, 
                                target_lang=self.target_lang, 
                                source_lang=self.source_lang
                            )
                            translations.append((translated, (x, y, w, h)))
                            
                            self.db_manager.cache_translation(text, self.source_lang, self.target_lang, translated)
                            self.logger.info(f"Translated & Cached: {text[:20]}... -> {translated[:20]}...")
                            
                        except Exception as e:
                            self.logger.error(f"Translation error for '{text}': {e}")
                            translations.append((text, (x, y, w, h)))
                    
                    if not self.stop_event.is_set():
                        self.result_ready.emit(translations)
                    
                    # Cleanup
                    del sct_img
                    # img is kept as last_img, will be collected next loop
                    
                    # Adaptive sleep: 0.5s (2 FPS) to reduce load
                    # Check stop event during sleep
                    for _ in range(5):
                        if self.stop_event.is_set(): break
                        time.sleep(0.1)
                        
                except Exception as e:
                    self.logger.error(f"Worker loop error: {e}")
                    time.sleep(1)
