import sys
import time
import logging
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from mss import mss
from PIL import Image
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
        """Group words into lines based on Y-coordinate proximity"""
        lines = []
        n_boxes = len(data['text'])
        
        valid_boxes = []
        for i in range(n_boxes):
            if int(data['conf'][i]) > 60 and data['text'][i].strip():
                valid_boxes.append({
                    'text': data['text'][i].strip(),
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'w': data['width'][i],
                    'h': data['height'][i]
                })
        
        valid_boxes.sort(key=lambda b: (b['y'], b['x']))
        
        current_line = []
        
        for box in valid_boxes:
            if not current_line:
                current_line.append(box)
                continue
                
            last_box = current_line[-1]
            
            y_diff = abs(box['y'] - last_box['y'])
            height_avg = (box['h'] + last_box['h']) / 2
            
            # Relaxed horizontal proximity to merge words with larger gaps
            x_dist = box['x'] - (last_box['x'] + last_box['w'])
            
            if y_diff < height_avg * 0.6 and x_dist < height_avg * 5: # Increased from 3 to 5
                current_line.append(box)
            else:
                lines.append(self.merge_line(current_line))
                current_line = [box]
        
        if current_line:
            lines.append(self.merge_line(current_line))
            
        merged_lines = []
        if not lines:
            return []
            
        current_block = lines[0]
        for i in range(1, len(lines)):
            next_line = lines[i]
            
            y_dist = next_line['y'] - (current_block['y'] + current_block['h'])
            x_diff = abs(next_line['x'] - current_block['x'])
            
            # Relaxed vertical merging for paragraphs
            if y_dist < current_block['h'] * 2.0 and x_diff < current_block['w'] * 0.8:
                current_block = self.merge_blocks(current_block, next_line)
            else:
                merged_lines.append(current_block)
                current_block = next_line
        
        merged_lines.append(current_block)
            
        return merged_lines

    def merge_line(self, words):
        full_text = " ".join([w['text'] for w in words])
        x = words[0]['x']
        y = words[0]['y']
        w = (words[-1]['x'] + words[-1]['w']) - x
        h = max([w['h'] for w in words])
        return {'text': full_text, 'x': x, 'y': y, 'w': w, 'h': h}

    def merge_blocks(self, block1, block2):
        full_text = block1['text'] + " " + block2['text']
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
                    # Capture
                    sct_img = sct.grab(self.monitor)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                    
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
