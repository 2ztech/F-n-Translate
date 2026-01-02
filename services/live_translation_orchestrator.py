import sys
import time
import logging
import multiprocessing
import os
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer, QRect, QRectF
from PyQt5.QtGui import QPainter, QColor, QFont, QPainterPath
import ctypes
from ctypes import wintypes
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

class ROISelector(QWidget):
    def __init__(self, monitor):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        
        self.monitor = monitor
        self.setGeometry(monitor['left'], monitor['top'], monitor['width'], monitor['height'])
        
        self.begin = None
        self.end = None
        self.selected_roi = None
        self.is_finished = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw dim background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        
        if self.begin and self.end:
            # Clear the selected area
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(QRect(self.begin, self.end), Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            
            # Draw border
            painter.setPen(QColor(0, 174, 255))
            painter.drawRect(QRect(self.begin, self.end))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.begin = event.pos()
            self.end = self.begin
            self.update()

    def mouseMoveEvent(self, event):
        if self.begin:
            self.end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.begin:
            self.end = event.pos()
            # Normalize ROI
            x1, y1 = self.begin.x(), self.begin.y()
            x2, y2 = self.end.x(), self.end.y()
            
            # Convert to absolute screen coordinates
            abs_x = self.monitor['left'] + min(x1, x2)
            abs_y = self.monitor['top'] + min(y1, y2)
            w = abs(x2 - x1)
            h = abs(y2 - y1)
            
            if w > 10 and h > 10:
                self.selected_roi = (abs_x, abs_y, w, h)
                self.is_finished = True
                self.close()
            else:
                self.begin = None
                self.end = None
                self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

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
        
        self.affinity_active = False
        self.show()
        
        # Delay the affinity call to ensure window is ready
        QTimer.singleShot(500, self._apply_affinity)
            
        self.translations = []
        self.last_update_time = 0

    def _apply_affinity(self):
        # Optional: Attempt to hide from capture, but don't rely on it
        try:
            hwnd = int(self.winId())
            ctypes.windll.user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
            ctypes.windll.user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
            
            result = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)
            if result:
                self.affinity_active = True
                print(f"Overlay affinity activated successfully for HWND {hwnd}")
            else:
                print(f"SetWindowDisplayAffinity returned 0 (Expected on some systems). Using Digital Masking as primary protection.")
        except Exception as e:
            print(f"Optional affinity skip: {e}")
            
        self.translations = []
        self.last_update_time = 0
        self.show()

    def update_translations(self, translations):
        # Filter out "noise" (tiny blocks)
        filtered = []
        for text, rect in translations:
            if rect[2] < 15 or rect[3] < 15: # Discard blocks smaller than 15x15
                continue
            filtered.append((text, rect))
            
        if self.translations == filtered:
            return

        self.translations = filtered
        self.last_update_time = time.time()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        for text, (x, y, w, h) in self.translations:
            if not text.strip():
                continue
                
            # Font auto-sizing loop
            font_size = 22 # Slightly smaller max size for better fit
            min_font_size = 7 # Allow slightly smaller text if needed
            
            while font_size >= min_font_size:
                font = QFont("Arial", font_size)
                font.setBold(True)
                painter.setFont(font)
                
                # Check if text fits in the box with some padding
                metrics = painter.fontMetrics()
                # Use a target rect with padding
                padding = 12 # Increased padding
                target_rect = QRect(x + padding, y + padding, w - 2*padding, h - 2*padding)
                
                flags = Qt.TextWordWrap | Qt.AlignCenter
                calc_rect = metrics.boundingRect(target_rect, flags, text)
                
                if calc_rect.height() <= (h - 2*padding) and calc_rect.width() <= (w - 2*padding):
                    break
                font_size -= 1
            
            # Final font setup
            font = QFont("Arial", font_size)
            font.setBold(True)
            painter.setFont(font)
            
            # Refine the background rect: find the actual text bounding rect and add padding
            padding_x = 10
            padding_y = 6
            metrics = painter.fontMetrics()
            
            # Use original width constraint for bounding calculation
            temp_rect = QRect(x, y, w, h)
            text_rect = metrics.boundingRect(temp_rect, Qt.TextWordWrap | Qt.AlignCenter, text)
            
            # Calculate tight background rect
            bg_w = min(w, text_rect.width() + padding_x * 2)
            bg_h = min(h, text_rect.height() + padding_y * 2)
            bg_x = x + (w - bg_w) // 2
            bg_y = y + (h - bg_h) // 2
            
            bg_rect = QRect(bg_x, bg_y, bg_w, bg_h)
            
            # Draw rounded background (semi-transparent black)
            path = QPainterPath()
            path.addRoundedRect(QRectF(bg_rect), 4, 4) # Even sleeker radius
            
            # Draw subtle shadow/border effect
            painter.fillPath(path, QColor(0, 0, 0, 230)) # Slightly darker for better contrast
            
            # Add thin light border for premium feel
            painter.setPen(QColor(255, 255, 255, 60)) # Slightly more visible border
            painter.drawPath(path)
            
            # Draw text
            painter.setPen(QColor(255, 255, 255))
            # Use small internal padding for the text area
            text_inner_rect = bg_rect.adjusted(2, 2, -2, -2)
            painter.drawText(text_inner_rect, Qt.TextWordWrap | Qt.AlignCenter, text)

class LiveTranslationProcess(multiprocessing.Process):
    def __init__(self, monitor_index, source_lang, target_lang, status_queue, command_queue, stop_event, roi=None):
        super().__init__()
        self.monitor_index = monitor_index
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.status_queue = status_queue
        self.command_queue = command_queue
        self.stop_event = stop_event
        self.roi = roi
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
            
            if self.roi:
                monitor_rect = self.roi
                # Update monitor dict for MSS to capture specific region
                monitor = {
                    "left": self.roi[0],
                    "top": self.roi[1],
                    "width": self.roi[2],
                    "height": self.roi[3]
                }
            else:
                monitor_rect = (monitor["left"], monitor["top"], monitor["width"], monitor["height"])

        overlay = OverlayWindow(monitor_rect)
        
        worker = TranslationWorker(monitor, self.source_lang, self.target_lang, logger, self.stop_event)
        worker.result_ready.connect(overlay.update_translations)
        
        # We no longer connect request_hide to overlay visibility.
        # The overlay stays visible for a smooth experience.
        # Protection is handled via Digital Masking in TranslationWorker.
        
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
