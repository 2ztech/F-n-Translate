# src/component/screen_capture_manager.py
import logging
import time
from queue import Queue
from threading import Thread, Event
from typing import Optional, Tuple

from PyQt5.QtCore import QObject, pyqtSignal
from mss import mss

from .ocr_worker import OCRWorker
from .text_processor import TextProcessor
from .translated_window import TranslatedTextWindow

logger = logging.getLogger("ScreenCaptureManager")

class ScreenCaptureManager(QObject):
    """
    Main orchestrator for the live screen capture and translation feature.
    Manages the entire pipeline: capture -> OCR -> process -> translate -> display.
    """
    
    # Signals to communicate with the main UI
    translation_ready = pyqtSignal(str)  # Emits translated text
    status_update = pyqtSignal(str)      # Emits status messages
    error_occurred = pyqtSignal(str)     # Emits error messages
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        
        # Configuration
        self.capture_interval = 1.0  # seconds between captures
        self.similarity_threshold = 0.8  # ignore similar text
        
        # State management
        self.is_capturing = False
        self.stop_event = Event()
        self.current_monitor = 0
        self.capture_area = None  # (x, y, width, height)
        
        # Components
        self.screenshot_queue = Queue()
        self.ocr_worker = None
        self.text_processor = TextProcessor()
        self.translation_window = None
        
        # Track previous text to avoid processing duplicates
        self.previous_text = ""
        self.previous_translation = ""
        
        logger.info("Screen Capture Manager initialized")

    def get_available_monitors(self):
        """Retrieve a list of available monitors."""
        try:
            with mss() as sct:
                monitors = sct.monitors  # List of monitors
                return monitors
        except Exception as e:
            logger.error(f"Failed to retrieve monitors: {str(e)}")
            return []

    def start_capture(self, monitor_index: int = 0, capture_area: Optional[Tuple[int, int, int, int]] = None):
        """Start the screen capture and translation pipeline."""
        if self.is_capturing:
            self.status_update.emit("Capture already running")
            return False

        try:
            monitors = self.get_available_monitors()
            if not monitors:
                self.error_occurred.emit("No monitors detected")
                return False

            if monitor_index >= len(monitors):
                self.error_occurred.emit("Invalid monitor index")
                return False

            self.current_monitor = monitor_index
            self.capture_area = capture_area
            self.is_capturing = True
            self.stop_event.clear()

            # Initialize OCR worker
            self.ocr_worker = OCRWorker(self.screenshot_queue, "eng")  # Default to English
            self.ocr_worker.ocr_result.connect(self._handle_ocr_result)
            self.ocr_worker.start()

            # Start capture thread
            self.capture_thread = Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()

            self.status_update.emit("Screen capture started")
            logger.info(f"Capture started on monitor {monitor_index}, area: {capture_area}")
            return True

        except Exception as e:
            self.error_occurred.emit(f"Failed to start capture: {str(e)}")
            logger.error(f"Failed to start capture: {str(e)}")
            return False

    def stop_capture(self):
        """Stop the screen capture pipeline."""
        if not self.is_capturing:
            return
            
        self.is_capturing = False
        self.stop_event.set()
        
        if self.ocr_worker and self.ocr_worker.isRunning():
            self.ocr_worker.quit()
            self.ocr_worker.wait()
        
        if self.translation_window:
            self.translation_window.close()
            self.translation_window = None
            
        self.status_update.emit("Screen capture stopped")
        logger.info("Capture stopped")

    def set_languages(self, source_lang: str, target_lang: str):
        """Update the source and target languages."""
        # Convert language names to codes if needed
        lang_map = {"English": "eng", "Malay": "msa"}  # Add more as needed
        self.source_lang_code = lang_map.get(source_lang, source_lang)
        self.target_lang_code = lang_map.get(target_lang, target_lang)
        
        # Update OCR worker language if it exists
        if self.ocr_worker:
            self.ocr_worker.language_combo = self.source_lang_code
            
        logger.info(f"Languages set: {source_lang} -> {target_lang}")

    def _capture_loop(self):
        """Main loop that captures screenshots at regular intervals."""
        with mss() as sct:
            while not self.stop_event.is_set() and self.is_capturing:
                try:
                    # Capture screenshot
                    screenshot = self._capture_screenshot(sct)
                    if screenshot:
                        # Put in queue for OCR processing
                        self.screenshot_queue.put((screenshot, self.source_lang_code))
                    
                    # Wait for next capture
                    time.sleep(self.capture_interval)
                    
                except Exception as e:
                    logger.error(f"Error in capture loop: {str(e)}")
                    self.error_occurred.emit(f"Capture error: {str(e)}")
                    time.sleep(1)  # Prevent rapid error looping

    def _capture_screenshot(self, sct) -> Optional:
        """Capture a screenshot of the specified area."""
        try:
            if self.capture_area:
                # Capture specific area
                x, y, width, height = self.capture_area
                monitor = {
                    "left": x,
                    "top": y,
                    "width": width,
                    "height": height
                }
            else:
                # Capture entire monitor
                monitor = sct.monitors[self.current_monitor + 1]  # +1 because monitor 0 is all monitors
            
            screenshot = sct.grab(monitor)
            return screenshot
            
        except Exception as e:
            logger.error(f"Screenshot capture failed: {str(e)}")
            return None

    def _handle_ocr_result(self, extracted_text: str):
        """Process OCR result and trigger translation if text is new."""
        try:
            # Clean and process the text
            cleaned_text = self.text_processor.process_text(extracted_text)
            
            if not cleaned_text.strip():
                return  # Skip empty text
                
            # Check if text is similar to previous text
            similarity = self.text_processor.calculate_similarity(
                cleaned_text, self.previous_text, self.source_lang_code
            )
            
            if similarity < self.similarity_threshold:
                # New text detected - translate it
                self.previous_text = cleaned_text
                self._translate_and_display(cleaned_text)
                
        except Exception as e:
            logger.error(f"Error processing OCR result: {str(e)}")
            self.error_occurred.emit(f"Processing error: {str(e)}")

    def _translate_and_display(self, text: str):
        """Translate text and display it in the overlay window."""
        try:
            # Translate the text
            translated_text = self.text_processor.translate_text(
                text, self.target_lang_code
            )
            
            self.previous_translation = translated_text
            
            # Emit signal for UI updates (if needed)
            self.translation_ready.emit(translated_text)
            
            # Create or update translation window
            if not self.translation_window:
                self._create_translation_window(translated_text)
            else:
                self.translation_window.update_text(translated_text)
                
            logger.debug(f"Translated: {text[:50]}... -> {translated_text[:50]}...")
            
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            self.error_occurred.emit(f"Translation error: {str(e)}")

    def _create_translation_window(self, initial_text: str):
        """Create the translation overlay window."""
        try:
            if self.capture_area:
                x, y, width, height = self.capture_area
            else:
                # Use entire monitor if no specific area selected
                with mss() as sct:
                    monitor = sct.monitors[self.current_monitor + 1]
                    x, y, width, height = monitor["left"], monitor["top"], monitor["width"], monitor["height"]
            
            self.translation_window = TranslatedTextWindow(
                self.parent, self.current_monitor, (x, y, width, height), initial_text
            )
            self.translation_window.show()
            
        except Exception as e:
            logger.error(f"Failed to create translation window: {str(e)}")
            self.error_occurred.emit(f"Window creation error: {str(e)}")

    def update_capture_area(self, start_point, end_point, geometry):
        """Update the capture area based on user selection."""
        try:
            # Convert points to absolute screen coordinates
            abs_start = (
                geometry.x() + start_point.x(),
                geometry.y() + start_point.y()
            )
            abs_end = (
                geometry.x() + end_point.x(),
                geometry.y() + end_point.y()
            )
            
            # Calculate area
            x = min(abs_start[0], abs_end[0])
            y = min(abs_start[1], abs_end[1])
            width = abs(abs_end[0] - abs_start[0])
            height = abs(abs_end[1] - abs_start[1])
            
            self.capture_area = (x, y, width, height)
            self.status_update.emit(f"Capture area set: {width}x{height}")
            logger.info(f"Capture area updated: {self.capture_area}")
            
        except Exception as e:
            logger.error(f"Failed to update capture area: {str(e)}")
