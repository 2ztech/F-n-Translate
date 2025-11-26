import sys
import time
import logging
import multiprocessing
import queue
import os
import hashlib
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QRect
from PyQt5.QtGui import QPainter, QColor, QFont
from mss import mss
from PIL import Image
import pytesseract

# Add parent directory to path to allow imports from core
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from core.translate_core import TranslationService

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
        self.show()

    def update_translations(self, translations):
        self.translations = translations
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        font = QFont("Arial", 12)
        font.setBold(True)
        painter.setFont(font)
        
        for text, (x, y, w, h) in self.translations:
            # Draw background
            bg_rect = QRect(x, y, w, h)
            painter.fillRect(bg_rect, QColor(0, 0, 0, 180))
            
            # Draw text
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(bg_rect, Qt.AlignCenter | Qt.TextWordWrap, text)

class TranslationCache:
    def __init__(self, max_size=1000):
        self.cache = {}
        self.max_size = max_size

    def get(self, text, target_lang):
        key = hashlib.md5(f"{text}:{target_lang}".encode()).hexdigest()
        return self.cache.get(key)

    def set(self, text, target_lang, translation):
        key = hashlib.md5(f"{text}:{target_lang}".encode()).hexdigest()
        if len(self.cache) >= self.max_size:
            # Simple eviction: remove a random item (or first one)
            self.cache.pop(next(iter(self.cache)))
        self.cache[key] = translation

class TranslationWorker(QThread):
    result_ready = pyqtSignal(list)
    
    def __init__(self, monitor, source_lang, target_lang, logger):
        super().__init__()
        self.monitor = monitor
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.logger = logger
        self.running = True
        self.translator = None
        self.cache = TranslationCache()

    def group_lines(self, data):
        """Group words into lines based on Y-coordinate proximity"""
        lines = []
        n_boxes = len(data['text'])
        
        current_line = []
        last_y = -1
        last_h = 0
        
        for i in range(n_boxes):
            if int(data['conf'][i]) > 60:
                text = data['text'][i].strip()
                if not text:
                    continue
                    
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                
                # Check if this word belongs to the current line
                # Heuristic: Y difference is small compared to height
                if current_line and abs(y - last_y) < h / 2:
                    current_line.append({'text': text, 'x': x, 'y': y, 'w': w, 'h': h})
                else:
                    # Start a new line
                    if current_line:
                        lines.append(self.merge_line(current_line))
                    current_line = [{'text': text, 'x': x, 'y': y, 'w': w, 'h': h}]
                    last_y = y
                    last_h = h
        
        if current_line:
            lines.append(self.merge_line(current_line))
            
        return lines

    def merge_line(self, words):
        """Merge a list of word dicts into a single line dict"""
        full_text = " ".join([w['text'] for w in words])
        x = words[0]['x']
        y = words[0]['y']
        # Width is from start of first word to end of last word
        w = (words[-1]['x'] + words[-1]['w']) - x
        # Height is max height of words
        h = max([w['h'] for w in words])
        return {'text': full_text, 'x': x, 'y': y, 'w': w, 'h': h}

    def run(self):
        try:
            self.translator = TranslationService()
            self.logger.info("Translation Service Initialized")
        except Exception as e:
            self.logger.error(f"Failed to init translator: {e}")
            return

        with mss() as sct:
            # Debug Capture
            try:
                debug_shot = sct.grab(self.monitor)
                mss.tools.to_png(debug_shot.rgb, debug_shot.size, output="debug_capture.png")
                self.logger.info(f"Debug capture saved to debug_capture.png. Monitor: {self.monitor}")
            except Exception as e:
                self.logger.error(f"Failed to save debug capture: {e}")

            while self.running:
                try:
                    start_time = time.time()
                    
                    # Capture
                    sct_img = sct.grab(self.monitor)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                    
                    # OCR
                    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                    
                    # Group into lines
                    lines = self.group_lines(data)
                    
                    translations = []
                    
                    for line in lines:
                        text = line['text']
                        x, y, w, h = line['x'], line['y'], line['w'], line['h']
                        
                        # Check Cache
                        cached = self.cache.get(text, self.target_lang)
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
                            self.cache.set(text, self.target_lang, translated)
                            self.logger.info(f"Translated: {text[:20]}... -> {translated[:20]}...")
                            
                        except Exception as e:
                            self.logger.error(f"Translation error for '{text}': {e}")
                            translations.append((text, (x, y, w, h))) # Fallback
                    
                    self.result_ready.emit(translations)
                    
                    # Cleanup
                    del img
                    del sct_img
                    
                    # Small sleep to prevent CPU hogging, but keep it responsive
                    time.sleep(0.1)
                        
                except Exception as e:
                    self.logger.error(f"Worker loop error: {e}")
                    time.sleep(1)

    def stop(self):
        self.running = False
        self.wait()

class LiveTranslationProcess(multiprocessing.Process):
    def __init__(self, monitor_index, source_lang, target_lang, status_queue, command_queue):
        super().__init__()
        self.monitor_index = monitor_index
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.status_queue = status_queue
        self.command_queue = command_queue
        self.daemon = True # Ensure process dies if parent dies

    def run(self):
        logger = setup_logging()
        logger.info(f"Process started for monitor {self.monitor_index}")

        app = QApplication(sys.argv)
        
        with mss() as sct:
            monitors = sct.monitors
            # Fix Monitor Indexing:
            # MSS monitors: [0] = All, [1] = Primary, [2] = Secondary...
            # UI index: 0 = Primary, 1 = Secondary...
            # So UI 0 -> MSS 1
            mss_index = self.monitor_index + 1
            
            if mss_index >= len(monitors):
                logger.error(f"Invalid monitor index: {mss_index}. Available: {len(monitors)}")
                return
            
            monitor = monitors[mss_index]
            logger.info(f"Capturing Monitor {mss_index}: {monitor}")
            monitor_rect = (monitor["left"], monitor["top"], monitor["width"], monitor["height"])

        overlay = OverlayWindow(monitor_rect)
        
        worker = TranslationWorker(monitor, self.source_lang, self.target_lang, logger)
        worker.result_ready.connect(overlay.update_translations)
        worker.start()
        
        # Check for stop command
        timer = QTimer()
        def check_stop():
            if not self.command_queue.empty():
                try:
                    cmd = self.command_queue.get_nowait()
                    if cmd == "STOP":
                        logger.info("Stop command received. Shutting down...")
                        worker.stop()
                        overlay.close()
                        app.quit()
                except queue.Empty:
                    pass
        
        timer.timeout.connect(check_stop)
        timer.start(100)

        sys.exit(app.exec_())
