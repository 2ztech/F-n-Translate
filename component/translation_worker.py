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
        """
        Phase 1: Merge Words -> Lines using Tesseract's internal 'line_num'.
        Phase 2: Merge Lines -> Paragraphs using dynamic spacing.
        """
        n_boxes = len(data['text'])
        
        # --- PHASE 1: WORDS TO LINES (Using Tesseract IDs) ---
        # We group by (block_num, line_num) to guarantee perfect line assembly
        lines_map = {}
        
        for i in range(n_boxes):
            # Check confidence and empty text
            if int(data['conf'][i]) > 40 and data['text'][i].strip():
                # Key = Unique Line ID
                key = (data['block_num'][i], data['line_num'][i])
                
                if key not in lines_map:
                    lines_map[key] = []
                
                lines_map[key].append({
                    'text': data['text'][i].strip(),
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'w': data['width'][i],
                    'h': data['height'][i]
                })

        # Consolidate Words into Line Blocks
        lines = []
        for key, words in lines_map.items():
            # Sort words by X to ensure correct reading order
            words.sort(key=lambda w: w['x'])
            
            full_text = " ".join([w['text'] for w in words])
            x = min(w['x'] for w in words)
            y = min(w['y'] for w in words)
            # Calculate union rectangle
            right = max(w['x'] + w['w'] for w in words)
            bottom = max(w['y'] + w['h'] for w in words)
            
            lines.append({
                'text': full_text,
                'x': x,
                'y': y,
                'w': right - x,
                'h': bottom - y
            })

        if not lines:
            return []

        # --- PHASE 2: LINES TO PARAGRAPHS (Dynamic Logic) ---
        # Sort by Y top-down
        lines.sort(key=lambda b: b['y'])
        
        paragraphs = []
        current_block = lines[0].copy()

        for i in range(1, len(lines)):
            next_line = lines[i]
            
            # Dynamic Threshold: 1.5x the height of the current line
            # This adapts to both small footnotes and huge headers automatically
            dynamic_threshold = current_block['h'] * 1.5
            
            current_bottom = current_block['y'] + current_block['h']
            gap = next_line['y'] - current_bottom
            
            # Check Horizontal Alignment (Are they in the same column?)
            # We calculate the horizontal overlap
            x1 = max(current_block['x'], next_line['x'])
            x2 = min(current_block['x'] + current_block['w'], next_line['x'] + next_line['w'])
            overlap = max(0, x2 - x1)
            
            # Logic: 
            # 1. Gap is small (same paragraph)
            # 2. Significant horizontal overlap (same column) OR almost aligned left edges
            is_same_col = (overlap > 0) or (abs(current_block['x'] - next_line['x']) < 50)
            
            if gap < dynamic_threshold and is_same_col:
                # MERGE
                new_bottom = max(current_bottom, next_line['y'] + next_line['h'])
                current_block['text'] += "\n" + next_line['text'] # Use newline to preserve structure
                current_block['h'] = new_bottom - current_block['y']
                
                # Expand width to cover the widest line
                max_right = max(current_block['x'] + current_block['w'], next_line['x'] + next_line['w'])
                current_block['x'] = min(current_block['x'], next_line['x'])
                current_block['w'] = max_right - current_block['x']
            else:
                paragraphs.append(current_block)
                current_block = next_line.copy()

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
        frame_count = 0
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

        with mss() as sct:
            while not self.stop_event.is_set():
                try:
                    # Capture screen while overlay is visible
                    sct_img = sct.grab(self.monitor)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                    
                    # DIGITAL MASKING: Erase the overlay's vision from the capture
                    draw = ImageDraw.Draw(img)
                    img_w, img_h = img.size
                    
                    # Mask Padding (Inflate the black box)
                    pad = 15  # Pixels to expand the mask
                    
                    for block in self.active_blocks:
                        r = block['rect']
                        # Inflate the box!
                        x0 = max(0, r[0] - pad)
                        y0 = max(0, r[1] - pad)
                        x1 = min(img_w, r[0] + r[2] + pad)
                        y1 = min(img_h, r[1] + r[3] + pad)
                        
                        if x1 > x0 and y1 > y0:
                            draw.rectangle([x0, y0, x1, y1], fill="black")
                    
                    # CRITICAL: Also mask the Debug Console area if it's always in the bottom left
                    # This prevents the recursive loop "Documents/lump/Project..."
                    # draw.rectangle([0, img_h - 150, 400, img_h], fill="black")
                    
                    if self.stop_event.is_set(): break

                    if last_img:
                        diff = self.get_image_diff(last_img, img)
                        # Only skip if screen is static AND we have already processed enough frames to be stable
                        if diff < 5.0 and frame_count > self.stabilizer.history_size:
                            time.sleep(0.2)
                            continue
                    
                    last_img = img.copy()
                    frame_count += 1

                    # OCR
                    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                    
                    if self.stop_event.is_set(): break

                    # Group into lines
                    current_lines = self.group_lines(data)
                    
                    # STABILIZER FEEDBACK: 
                    # If we have current active_blocks, include them as "existing" candidates
                    # to prevent the stabilizer from dropping masked blocks.
                    all_candidates = list(current_lines)
                    for block in self.active_blocks:
                        if block['misses'] < 2: # Only feed back truly active ones
                            candidate = {
                                'text': block['text'],
                                'x': block['rect'][0],
                                'y': block['rect'][1],
                                'w': block['rect'][2],
                                'h': block['rect'][3]
                            }
                            # Avoid duplicates if OCR actually found it too
                            if not any(self.stabilizer.is_similar(candidate, c) for c in current_lines):
                                all_candidates.append(candidate)

                    # Stabilize
                    self.stabilizer.add_frame(all_candidates)
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
