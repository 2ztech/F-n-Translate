# webview_capture_manager.py
import logging
import time
import threading
import platform
from mss import mss
from PIL import Image
import pytesseract
import io
import base64

logger = logging.getLogger("WebViewCaptureManager")

class WebViewCaptureManager:
    """Screen capture manager without PyQt5 dependencies for PyWebView"""
    
    def __init__(self):
        self.is_capturing = False
        self.capture_thread = None
        self.stop_event = threading.Event()
        self.current_monitor = 1  # Default to monitor 1 (physical monitor)
        self.source_lang = "eng"
        self.target_lang = "msa"
        
        # Simple callback system instead of PyQt5 signals
        self.translation_callback = None
        self.status_callback = None
        self.error_callback = None
        
        logger.info(f"WebView Capture Manager initialized on {platform.system()}")
    
    def set_callbacks(self, translation_cb, status_cb, error_cb):
        """Set callbacks for communication"""
        self.translation_callback = translation_cb
        self.status_callback = status_cb
        self.error_callback = error_cb
    
    def get_available_monitors(self):
        """Get available monitors - returns simple dicts"""
        try:
            logger.info("Attempting to detect monitors...")
            
            with mss() as sct:
                monitors = []
                logger.info(f"Total monitors detected by MSS: {len(sct.monitors)}")
                
                # Log all monitors for debugging
                for i, monitor in enumerate(sct.monitors):
                    logger.info(f"Monitor {i}: {monitor}")
                
                # On Windows:
                # - Monitor 0: Virtual screen (all monitors combined)
                # - Monitor 1+: Physical monitors
                # We only want to show physical monitors to the user
                for i, monitor in enumerate(sct.monitors):
                    if i == 0:
                        # Skip the virtual screen (monitor 0)
                        continue
                    
                    # This is a physical monitor
                    monitor_name = f"Display {i}"
                    if i == 1 and len(sct.monitors) == 2:
                        monitor_name = "Primary Display"
                    
                    monitors.append({
                        'index': i - 1,  # FIX: Convert to 0-based index for UI
                        'name': monitor_name,
                        'width': monitor['width'],
                        'height': monitor['height'],
                        'left': monitor['left'],
                        'top': monitor['top']
                    })
                
                logger.info(f"Returning {len(monitors)} physical monitors to UI")
                return monitors
                
        except Exception as e:
            logger.error(f"Failed to get monitors: {str(e)}")
            if self.error_callback:
                self.error_callback(f"Monitor detection failed: {str(e)}")
            return []
    
    def set_languages(self, source_lang, target_lang):
        """Set languages for OCR and translation"""
        # Convert language names to codes
        lang_map = {
            "English": "eng", 
            "Malay": "msa",
            "eng": "eng",
            "msa": "msa"
        }
        self.source_lang = lang_map.get(source_lang, "eng")
        self.target_lang = lang_map.get(target_lang, "msa")
        logger.info(f"Languages set: {source_lang}->{self.source_lang}, {target_lang}->{self.target_lang}")
    
    def start_capture(self, monitor_index):
        """Start screen capture"""
        if self.is_capturing:
            if self.status_callback:
                self.status_callback("Capture already running")
            return False
        
        try:
            # FIX: Convert UI index (0-based) to MSS index (1-based for physical monitors)
            self.current_monitor = monitor_index + 1
            self.is_capturing = True
            self.stop_event.clear()
            
            if self.status_callback:
                self.status_callback(f"Starting screen capture on monitor {monitor_index}...")
            
            # Start capture in a thread
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            logger.info(f"Capture started on monitor {monitor_index} (MSS index: {self.current_monitor})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start capture: {str(e)}")
            if self.error_callback:
                self.error_callback(f"Failed to start capture: {str(e)}")
            return False
    
    def stop_capture(self):
        """Stop screen capture"""
        if not self.is_capturing:
            return
        
        self.is_capturing = False
        self.stop_event.set()
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        
        if self.status_callback:
            self.status_callback("Screen capture stopped")
        logger.info("Capture stopped")
    
    def _capture_loop(self):
        """Main capture loop"""
        try:
            with mss() as sct:
                # Validate monitor index
                if self.current_monitor >= len(sct.monitors):
                    logger.error(f"Invalid monitor index: {self.current_monitor}")
                    if self.error_callback:
                        self.error_callback(f"Invalid monitor index: {self.current_monitor}")
                    return
                
                monitor = sct.monitors[self.current_monitor]
                logger.info(f"Capturing from monitor {self.current_monitor}: {monitor}")
                
                if self.status_callback:
                    self.status_callback(f"Capturing from {monitor['width']}x{monitor['height']} display")
                
                capture_count = 0
                while self.is_capturing and not self.stop_event.is_set():
                    try:
                        # Capture screenshot
                        screenshot = sct.grab(monitor)
                        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                        
                        # Process OCR
                        text = self._perform_ocr(img)
                        
                        if text and text.strip():
                            # Translate text
                            translated = self._translate_text(text)
                            
                            if translated and self.translation_callback:
                                self.translation_callback(translated)
                        
                        capture_count += 1
                        if capture_count % 10 == 0:  # Log every 10 captures
                            logger.info(f"Still capturing... ({capture_count} captures)")
                        
                        # Wait before next capture
                        time.sleep(2.0)  # 2 second interval
                        
                    except Exception as e:
                        logger.error(f"Error in capture loop: {str(e)}")
                        if self.error_callback:
                            self.error_callback(f"Capture error: {str(e)}")
                        time.sleep(1.0)
                        
        except Exception as e:
            logger.error(f"Capture loop failed: {str(e)}")
            if self.error_callback:
                self.error_callback(f"Capture failed: {str(e)}")
    
    def _perform_ocr(self, image):
        """Perform OCR on image"""
        try:
            # Simple OCR processing
            image = image.convert('L')  # Convert to grayscale
            
            # Use pytesseract
            pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            config = f"-l {self.source_lang} --psm 6 --oem 1"
            text = pytesseract.image_to_string(image, config=config)
            
            if text.strip():
                logger.info(f"OCR detected text: {text.strip()[:100]}...")
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"OCR failed: {str(e)}")
            return ""
    
    def _translate_text(self, text):
        """Translate text - you can integrate your translation service here"""
        try:
            # For now, just return the text as-is
            # Replace this with your actual translation service
            return f"[Translated] {text}"
            
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            return text

    def test_capture(self):
        """Test method to verify screen capture works"""
        try:
            with mss() as sct:
                logger.info("Testing screen capture...")
                monitor = sct.monitors[1]  # Try primary monitor
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                logger.info(f"Test capture successful: {screenshot.size}")
                return True
        except Exception as e:
            logger.error(f"Test capture failed: {str(e)}")
            return False
    
    def get_monitor_screenshot(self, monitor_index):
        """Take a screenshot of the specified monitor and return as base64"""
        try:
            with mss() as sct:
                # FIX: Convert UI index (0-based) to MSS index (1-based for physical monitors)
                mss_index = monitor_index + 1
                
                # Validate index
                if mss_index >= len(sct.monitors):
                    logger.error(f"Invalid monitor index for preview: {monitor_index} (MSS index: {mss_index})")
                    return None
                
                monitor = sct.monitors[mss_index]
                screenshot = sct.grab(monitor)
                
                # FIX: Convert to base64 properly
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                logger.info(f"Preview screenshot taken: {screenshot.size}")
                return img_base64
                
        except Exception as e:
            logger.error(f"Screenshot failed: {str(e)}")
            return None

    # Add this method to your WebViewCaptureManager class for optimized previews
    def get_monitor_preview_optimized(self, monitor_index):
        """Take an optimized screenshot for preview (lower quality, faster)"""
        try:
            with mss() as sct:
                # Convert UI index (0-based) to MSS index (1-based for physical monitors)
                mss_index = monitor_index + 1
                
                # Validate index
                if mss_index >= len(sct.monitors):
                    logger.error(f"Invalid monitor index for preview: {monitor_index}")
                    return None
                
                monitor = sct.monitors[mss_index]
                screenshot = sct.grab(monitor)
                
                # Convert to PIL Image
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                
                # OPTIMIZATION: Resize image for preview to reduce data transfer
                # Calculate target size while maintaining aspect ratio
                max_preview_size = 800  # Maximum dimension for preview
                width, height = img.size
                
                if width > height:
                    new_width = max_preview_size
                    new_height = int((max_preview_size / width) * height)
                else:
                    new_height = max_preview_size
                    new_width = int((max_preview_size / height) * width)
                
                # Resize image for faster transfer and rendering
                img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Convert to base64
                buffered = io.BytesIO()
                img_resized.save(buffered, format="JPEG", quality=85)  # Use JPEG for smaller size
                img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                logger.debug(f"Preview generated: {screenshot.size} -> {img_resized.size}")
                return img_base64
                
        except Exception as e:
            logger.error(f"Screenshot failed: {str(e)}")
            return None
