import sys
import time
import logging
import multiprocessing
import os
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QPainter, QColor, QFont
from mss import mss

# Add parent directory to path to allow imports from core and component
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from component.translation_worker import TranslationWorker

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
            # Calculate optimal font size based on box height (approx 70%)
            # Clamp between 10 and 24 to avoid tiny or huge text
            target_height = h * 0.7
            font_size = max(10, min(24, int(target_height)))
            
            font = QFont("Arial", font_size)
            font.setBold(True)
            painter.setFont(font)
            
            # Calculate text dimensions
            metrics = painter.fontMetrics()
            # Allow width to expand if needed, but keep height constrained to original line + padding
            # We want the text to be readable, so we prioritize font size over fitting in original width
            text_rect = metrics.boundingRect(QRect(0, 0, 0, 0), Qt.AlignCenter, text)
            
            # Calculate new background rect centered on the original box
            new_w = max(w, text_rect.width() + 10) # Add padding
            new_h = max(h, text_rect.height() + 4)
            
            # Center the new rect on the original rect
            center_x = x + w // 2
            center_y = y + h // 2
            new_x = center_x - new_w // 2
            new_y = center_y - new_h // 2
            
            bg_rect = QRect(new_x, new_y, new_w, new_h)
            
            # Draw background (semi-transparent black)
            painter.fillRect(bg_rect, QColor(0, 0, 0, 200))
            
            # Draw text
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(bg_rect, Qt.AlignCenter, text)

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
                # Wait at most 2 seconds for worker to finish
                if not worker.wait(2000):
                    logger.warning("Worker did not finish in time, forcing close...")
                
                overlay.close()
                app.quit()
        
        timer.timeout.connect(check_stop)
        timer.start(100) # Check every 100ms 

        sys.exit(app.exec_())
