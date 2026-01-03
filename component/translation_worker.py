import sys
import time
import logging
import numpy as np
import cv2
from PyQt5.QtCore import QThread, pyqtSignal
from mss import mss
from PIL import Image, ImageDraw
import pytesseract

# Adjust imports based on project structure
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.translate_core import TranslationService
from core.dbmanager import get_db_manager

class TextStabilizer:
    def __init__(self, history_size=5, stability_threshold=2):
        self.history = [] 
        self.history_size = history_size
        self.stability_threshold = stability_threshold # Low threshold = Faster display

    def add_frame(self, text_blocks):
        self.history.append(text_blocks)
        if len(self.history) > self.history_size:
            self.history.pop(0)

    def get_stable_blocks(self):
        if not self.history: return []
        candidates = self.history[-1]
        stable_blocks = []
        for candidate in candidates:
            matches = 0
            for frame in self.history[:-1]:
                for block in frame:
                    if self.is_similar(candidate, block):
                        matches += 1
                        break
            # Needs (Threshold - 1) matches. If thresh is 2, needs 1 match. Fast.
            if matches >= self.stability_threshold - 1:
                stable_blocks.append(candidate)
        return stable_blocks

    def is_similar(self, block1, block2):
        # Check geometric overlap to see if it's the same text box
        x_overlap = max(0, min(block1['x'] + block1['w'], block2['x'] + block2['w']) - max(block1['x'], block2['x']))
        y_overlap = max(0, min(block1['y'] + block1['h'], block2['y'] + block2['h']) - max(block1['y'], block2['y']))
        area1 = block1['w'] * block1['h']
        area2 = block2['w'] * block2['h']
        if area1 == 0 or area2 == 0: return False
        overlap_area = x_overlap * y_overlap
        return overlap_area > 0.6 * min(area1, area2)

    def reset(self):
        self.history = []

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
        
        # Stability Settings
        self.stabilizer = TextStabilizer(history_size=5, stability_threshold=2)
        
        self.last_emitted_signature = None
        self.last_ocr_results = []
        self.last_raw_img = None
        
        # Motion Buffer
        self.scroll_streak = 0 

    def get_image_diff(self, img1, img2):
        """Calculates how much the screen changed"""
        if img1 is None or img2 is None: return 100.0
        thumb1 = img1.resize((64, 64), Image.Resampling.NEAREST).convert('L')
        thumb2 = img2.resize((64, 64), Image.Resampling.NEAREST).convert('L')
        arr1 = np.array(thumb1)
        arr2 = np.array(thumb2)
        return np.mean((arr1 - arr2) ** 2)

    def get_layout_boxes(self, pil_image):
        """
        Uses OpenCV Morphological Dilation to find paragraph blocks.
        Kernel size (15, 20) ensures Paragraphs are merged, not lines.
        """
        # 1. Convert to grayscale
        img_np = np.array(pil_image)
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        
        # 2. Threshold 
        # Adaptive works best for text on various backgrounds
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY_INV, 11, 2)
        
        # 3. DILATION (The Fix for "Box too small")
        # (15, 20) -> 15px Horizontal merge, 20px Vertical merge.
        # This forces lines to stick together into one big paragraph box.
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 20))
        dilated = cv2.dilate(thresh, kernel, iterations=2)
        
        # 4. Find Contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        blocks = []
        img_h, img_w = img_np.shape[:2]
        min_area = 200 # Ignore noise
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w * h > min_area:
                # Add Padding so Tesseract can see the edges
                pad = 10 
                x_pad = max(0, x - pad)
                y_pad = max(0, y - pad)
                w_pad = min(img_w - x_pad, w + 2*pad)
                h_pad = min(img_h - y_pad, h + 2*pad)
                
                crop = pil_image.crop((x_pad, y_pad, x_pad+w_pad, y_pad+h_pad))
                
                blocks.append({
                    'crop': crop,
                    'rect': (x, y, w, h) # Return the Tight Box for the overlay
                })
        
        return blocks

    def run(self):
        try:
            self.translator = TranslationService()
            self.db_manager = get_db_manager()
            self.logger.info("Translation Service Initialized")
        except Exception as e:
            self.logger.error(f"Failed to init services: {e}")
            return

        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

        with mss() as sct:
            while not self.stop_event.is_set():
                try:
                    # 1. Capture Screen
                    sct_img = sct.grab(self.monitor)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                    
                    if self.stop_event.is_set(): break

                    # 2. SCROLL GUARD (Fix for "Didn't adjust on content change")
                    is_scrolling = False
                    is_static = False
                    
                    if self.last_raw_img:
                        diff = self.get_image_diff(self.last_raw_img, img)
                        
                        if diff > 15.0:
                            self.scroll_streak += 1 # Motion Detected
                        else:
                            self.scroll_streak = 0  # Motion Stopped
                            if diff < 5.0:
                                is_static = True
                        
                        # If moving for > 2 frames, we are definitely scrolling.
                        if self.scroll_streak > 2:
                            is_scrolling = True
                    
                    self.last_raw_img = img.copy()

                    # IF SCROLLING: Clear screen immediately
                    if is_scrolling:
                        self.stabilizer.reset()
                        self.last_ocr_results = []
                        
                        # Signal the UI to hide everything
                        if self.last_emitted_signature is not None:
                            self.result_ready.emit([]) 
                            self.last_emitted_signature = None
                        
                        # Wait briefly for scroll to settle
                        time.sleep(0.02) 
                        continue 

                    raw_blocks = []
                    
                    # 3. OCR Logic
                    if is_static and self.last_ocr_results:
                        # FAST PATH: Reuse old results (CPU Saver)
                        raw_blocks = self.last_ocr_results
                    else:
                        # NEW PATH: Run OpenCV Layout Analysis
                        layout_blocks = self.get_layout_boxes(img)
                        
                        for item in layout_blocks:
                            try:
                                # PSM 6 = Assume single uniform block
                                text = pytesseract.image_to_string(item['crop'], lang=self.source_lang, config='--psm 6')
                                text = text.strip()
                                if text:
                                    x, y, w, h = item['rect']
                                    raw_blocks.append({'text': text, 'x': x, 'y': y, 'w': w, 'h': h})
                            except:
                                pass
                        
                        self.last_ocr_results = raw_blocks

                    # 4. Stabilize
                    self.stabilizer.add_frame(raw_blocks)
                    stable_lines = self.stabilizer.get_stable_blocks()
                    
                    translations = []
                    
                    for line in stable_lines:
                        if self.stop_event.is_set(): break
                        
                        text = line['text']
                        x, y, w, h = line['x'], line['y'], line['w'], line['h']
                        
                        # Cache Check
                        cached = self.db_manager.get_cached_translation(text, self.source_lang, self.target_lang)
                        if cached:
                            translations.append((cached, (x, y, w, h)))
                            continue

                        # Translate
                        try:
                            translated = self.translator.translate(
                                text, 
                                target_lang=self.target_lang, 
                                source_lang=self.source_lang
                            )
                            translations.append((translated, (x, y, w, h)))
                            self.db_manager.cache_translation(text, self.source_lang, self.target_lang, translated)
                            
                        except Exception as e:
                            self.logger.error(f"Translation error: {e}")
                            translations.append((text, (x, y, w, h)))
                    
                    # 5. Anti-Strobe / Update UI
                    current_signature = set()
                    for t, (x, y, w, h) in translations:
                        # Signature (Text + Grid Position) to detect real changes
                        sig = (t, int(x/5), int(y/5), int(w/5), int(h/5))
                        current_signature.add(sig)
                    
                    if current_signature != self.last_emitted_signature:
                        if not self.stop_event.is_set():
                            self.result_ready.emit(translations)
                            self.last_emitted_signature = current_signature
                    
                    del sct_img
                    
                    # High Performance Sleep
                    time.sleep(0.02) 
                        
                except Exception as e:
                    self.logger.error(f"Worker loop error: {e}")
                    time.sleep(1)