import sys
import time
import logging
import multiprocessing
import queue
import os
import hashlib
import numpy as np
from collections import Counter
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QRect
from PyQt5.QtGui import QPainter, QColor, QFont
from mss import mss
from PIL import Image
import pytesseract

# Add parent directory to path to allow imports from core
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.translate_core import TranslationService
from core.dbmanager import get_db_manager

# Configure logging
def setup_logging():
    logger = logging.getLogger("LiveService")
    logger.setLevel(logging.DEBUG)
    
    # File handler - Keep detailed logs
    fh = logging.FileHandler('translation_service.log', mode='w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Console handler - Reduce spam, only show INFO/WARNING
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

class OverlayWindow(QWidget):
    def __init__(self, rect):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool | 
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        
        x, y, w, h = rect
        self.setGeometry(x, y, w, h)
        
        self.translations = []
        self.last_update_time = 0
        self.show()

    def update_translations(self, translations):
        # Optimization: Don't repaint if translations haven't changed
        if self.translations == translations:
            return

        self.translations = translations
        self.last_update_time = time.time()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        for text, (x, y, w, h) in self.translations:
            # Draw background
            bg_rect = QRect(x, y, w, h)
            painter.fillRect(bg_rect, QColor(0, 0, 0, 180))
            
            # Dynamic Font Sizing
            font_size = 12
            font = QFont("Arial", font_size)
            font.setBold(True)
            painter.setFont(font)
            
            # Calculate text rect
            metrics = painter.fontMetrics()
            text_rect = metrics.boundingRect(bg_rect, Qt.AlignCenter | Qt.TextWordWrap, text)
            
            # Shrink font if text doesn't fit
            while (text_rect.height() > h or text_rect.width() > w) and font_size > 8:
                font_size -= 1
                font.setPointSize(font_size)
                painter.setFont(font)
                metrics = painter.fontMetrics()
                text_rect = metrics.boundingRect(bg_rect, Qt.AlignCenter | Qt.TextWordWrap, text)
            
            # Draw text
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(bg_rect, Qt.AlignCenter | Qt.TextWordWrap, text)

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
                    
                    # Adaptive sleep: 0.2s is 5 FPS, good for reading
                    time.sleep(0.2)
                        
                except Exception as e:
                    self.logger.error(f"Worker loop error: {e}")
                    time.sleep(1)

class LiveTranslationProcess(multiprocessing.Process):
    def __init__(self, monitor_index, source_lang, target_lang, status_queue, command_queue, stop_event):
        super().__init__()
        self.monitor_index = monitor_index
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.status_queue = status_queue
        self.command_queue = command_queue
        self.stop_event = stop_event
        self.daemon = True 

    def run(self):
        logger = setup_logging()
        logger.info(f"Process started for monitor {self.monitor_index}")

        app = QApplication(sys.argv)
        
        with mss() as sct:
            monitors = sct.monitors
            mss_index = self.monitor_index + 1
            
            if mss_index >= len(monitors):
                logger.error(f"Invalid monitor index: {mss_index}. Available: {len(monitors)}")
                return
            
            monitor = monitors[mss_index]
            logger.info(f"Capturing Monitor {mss_index}: {monitor}")
            monitor_rect = (monitor["left"], monitor["top"], monitor["width"], monitor["height"])

        overlay = OverlayWindow(monitor_rect)
        
        worker = TranslationWorker(monitor, self.source_lang, self.target_lang, logger, self.stop_event)
        worker.result_ready.connect(overlay.update_translations)
        worker.start()
        
        # Check for stop event
        timer = QTimer()
        def check_stop():
            if self.stop_event.is_set():
                logger.info("Stop event detected. Shutting down...")
                worker.wait() 
                overlay.close()
                app.quit()
        
        timer.timeout.connect(check_stop)
        timer.start(50) 

        sys.exit(app.exec_())
