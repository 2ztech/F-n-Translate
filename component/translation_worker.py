import sys
import time
import logging
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from PIL import Image
import pytesseract

# Adjust imports based on project structure
import os
import pynput
from pynput import mouse, keyboard
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.translate_core import TranslationService
from core.dbmanager import get_db_manager

class TextStabilizer:
    def __init__(self, history_size=5, stability_threshold=2):
        self.history = [] 
        self.history_size = history_size
        self.stability_threshold = stability_threshold 

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
            # If threshold is 2, we need 1 match from history.
            if matches >= self.stability_threshold - 1:
                stable_blocks.append(candidate)
        return stable_blocks

    def is_similar(self, block1, block2):
        # Check geometric overlap
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
        self.stabilizer = TextStabilizer(history_size=5, stability_threshold=2)
        
        self.last_raw_img = None
        
        # State Variables
        # State Variables
        self.last_movement_time = 0
        self.is_translated = False
        self.masked_regions = [] # Regions to ignore during diff (Digital Masking)
        self.anchor_frame = None # Reference frame for the current translation

        # Input Listeners for Active Detection
        self.mouse_listener = mouse.Listener(on_scroll=self.on_scroll)
        self.key_listener = keyboard.Listener(on_press=self.on_press)
        
    def on_scroll(self, x, y, dx, dy):
        # User scrolled: Immediate invalidation
        self.force_clear("User Scroll")

    def on_press(self, key):
        # Check for navigation keys
        try:
            if key in [keyboard.Key.up, keyboard.Key.down, keyboard.Key.page_up, 
                       keyboard.Key.page_down, keyboard.Key.home, keyboard.Key.end, keyboard.Key.space]:
                 self.force_clear(f"Key {key} pressed")
        except:
            pass

    def force_clear(self, reason):
        # Thread-safe clear trigger (called from listener threads)
        if self.is_translated or len(self.stabilizer.history) > 0:
            self.result_ready.emit([]) 
            self.stabilizer.reset()
            self.is_translated = False
            self.masked_regions = []
            self.anchor_frame = None
            self.last_movement_time = time.time()
            self.logger.info(f"Active Input: {reason}. Overlay cleared.")

    def get_image_diff(self, img1, img2, ignore_rects=[]):
        if img1 is None or img2 is None: return 100.0
        
        # Create copies to apply masks
        # work_img1 = img1.copy()
        # work_img2 = img2.copy()
        # Optimization: We can just draw black rectangles on the PIL images before resizing
        # But we don't want to modify the source images if they are used elsewhere.
        # Since we resize immediately, masking the full image is expensive? 
        # Actually masking the thumbnail is inaccurate because rects are in full resolution.
        # So we must mask full image or translate rects. 
        # Improved: Mask full image copies (or draw on them if they are throwaway).
        # img1 is self.last_raw_img, img2 is current img. We should not modify them in-place.
        
        # To avoid copying full images (slow), let's resize first, then mask?
        # No, rects are absolute.
        # Let's try drawing on copies.
        
        i1 = img1.copy()
        i2 = img2.copy()
        
        if ignore_rects:
            from PIL import ImageDraw
            draw1 = ImageDraw.Draw(i1)
            draw2 = ImageDraw.Draw(i2)
            for (x, y, w, h) in ignore_rects:
                draw1.rectangle([x, y, x+w, y+h], fill=(0,0,0))
                draw2.rectangle([x, y, x+w, y+h], fill=(0,0,0))
        
        thumb1 = i1.resize((64, 64), Image.Resampling.NEAREST).convert('L')
        thumb2 = i2.resize((64, 64), Image.Resampling.NEAREST).convert('L')
        arr1 = np.array(thumb1)
        arr2 = np.array(thumb2)
        return np.mean((arr1 - arr2) ** 2)

    def get_layout_boxes(self, pil_image):
        import cv2
        img_np = np.array(pil_image)
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY_INV, 11, 2)
        
        # Kernel (15, 12): 
        # 15px Horizontal merge (Words -> Lines)
        # 12px Vertical merge (Lines -> Paragraphs)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 12))
        dilated = cv2.dilate(thresh, kernel, iterations=2)
        
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        blocks = []
        img_h, img_w = img_np.shape[:2]
        min_area = 200 
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w * h > min_area:
                pad = 10 
                x_pad = max(0, x - pad)
                y_pad = max(0, y - pad)
                w_pad = min(img_w - x_pad, w + 2*pad)
                h_pad = min(img_h - y_pad, h + 2*pad)
                
                crop = pil_image.crop((x_pad, y_pad, x_pad+w_pad, y_pad+h_pad))
                
                blocks.append({
                    'crop': crop,
                    'rect': (x, y, w, h)
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

        # 1. Try default system path (if added to PATH)
        pytesseract.pytesseract.tesseract_cmd = "tesseract"

        # 2. If that fails, check common Windows paths
        default_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.join(os.getenv('LOCALAPPDATA'), r"Tesseract-OCR\tesseract.exe")
        ]
        
        for path in default_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break
        
        # Init timing to current time so we don't wait immediately on startup
        # Init timing to current time so we don't wait immediately on startup
        self.last_movement_time = time.time()
        
        # Start Input Listeners
        # Start Input Listeners
        self.mouse_listener.start()
        self.key_listener.start()

        from mss import mss
        with mss() as sct:
            while not self.stop_event.is_set():
                try:
                    # 1. Capture Screen
                    sct_img = sct.grab(self.monitor)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                    
                    if self.stop_event.is_set(): break

                    # 2. Motion Detection
                    diff = 0.0
                    if self.last_raw_img:
                        diff = self.get_image_diff(self.last_raw_img, img, self.masked_regions)

                    if self.is_translated and self.anchor_frame:
                        anchor_diff = self.get_image_diff(self.anchor_frame, img, self.masked_regions)
                        if anchor_diff > 10.0: # Moderate threshold for cumulative drift
                             self.result_ready.emit([]) 
                             self.stabilizer.reset()
                             self.is_translated = False
                             self.masked_regions = []
                             self.anchor_frame = None
                             self.logger.info(f"Anchor Drift (Diff: {anchor_diff:.1f}). Overlay cleared.")
                             self.last_movement_time = time.time()
                             continue

                    # LOGIC: HIGH MOVEMENT (SCROLLING / SCENE CHANGE)
                    # Reduced threshold from 30.0 to 15.0 for better responsiveness
                    if diff > 15.0: 
                        self.last_movement_time = time.time() # Reset timer
                        
                        # If we were previously static/translated, CLEAR the overlay now.
                        if self.is_translated or len(self.stabilizer.history) > 0:
                            self.result_ready.emit([]) # Clear UI
                            self.stabilizer.reset()
                            self.is_translated = False
                            self.masked_regions = [] # Clear masks
                            self.anchor_frame = None
                            self.logger.info(f"Screen moving (Diff: {diff:.1f}). Overlay cleared.")
                        
                        self.last_raw_img = img.copy()
                        time.sleep(0.02) # Fast loop while moving
                        continue

                    # LOGIC: STATIC WAIT TIMER
                    # Even if diff is small (e.g. 5.0 - 29.0), we wait for it to settle for 1s.
                    # This lets animations play out without triggering constant re-OCR.
                    if time.time() - self.last_movement_time < 1.0:
                        self.last_raw_img = img.copy()
                        time.sleep(0.05) # Wait state
                        continue

                    # LOGIC: ALREADY TRANSLATED?
                    # If stable for >1s and we already finished translating, do nothing.
                    if self.is_translated:
                        time.sleep(0.1)
                        continue

                    # --- TRANSLATION START ---
                    # Screen is static for > 1.0s and needs translation.
                    
                    # 1. OCR
                    layout_blocks = self.get_layout_boxes(img)
                    raw_blocks = []
                    
                    for item in layout_blocks:
                        try:
                            text = pytesseract.image_to_string(item['crop'], lang=self.source_lang, config='--psm 6')
                            text = text.strip()
                            if text:
                                x, y, w, h = item['rect']
                                raw_blocks.append({'text': text, 'x': x, 'y': y, 'w': w, 'h': h})
                        except:
                            pass

                    # 2. Stabilize (Filter out noise)
                    self.stabilizer.add_frame(raw_blocks)
                    stable_lines = self.stabilizer.get_stable_blocks()
                    
                    # If stabilizer returns nothing yet (needs 2 frames), loop again.
                    if not stable_lines:
                        self.last_raw_img = img.copy()
                        continue

                    translations = []
                    
                    for line in stable_lines:
                        if self.stop_event.is_set(): break
                        
                        text = line['text']
                        x, y, w, h = line['x'], line['y'], line['w'], line['h']
                        
                        # Cache Check
                        cached = self.db_manager.get_cached_text(text, self.source_lang, self.target_lang)
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
                            self.db_manager.cache_text_translation(text, self.source_lang, self.target_lang, translated)
                        except Exception as e:
                            self.logger.error(f"Translation error: {e}")
                            translations.append((text, (x, y, w, h)))
                    
                    # 3. Emit Results
                    if not self.stop_event.is_set():
                        self.result_ready.emit(translations)
                        self.is_translated = True # Done. Wait for movement to reset.
                        # Update Masked Regions for next frame
                        self.masked_regions = [r for t, r in translations]
                        # Set Anchor Frame (Snapshot of what we just translated)
                        self.anchor_frame = img.copy()

                    self.last_raw_img = img.copy()
                    
                    # Cleanup
                    del sct_img
                    time.sleep(0.05)
                        
                except Exception as e:
                    self.logger.error(f"Worker loop error: {e}")
                    time.sleep(1)