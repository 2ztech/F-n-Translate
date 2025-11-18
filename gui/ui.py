# ui.py
import webview
import logging
import sys
import os
import json
import time
from .templates import get_html_template

# Add parent directory to path to import webview_capture_manager
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from component.webview_capture_manager import WebViewCaptureManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log',
    filemode='w'
)
logger = logging.getLogger("UI")

# Global instances for PyWebView compatibility
api = None
capture_manager = None

def initialize_components():
    """Initialize components on demand"""
    global api, capture_manager
    if api is None:
        from api.api import TranslationAPI
        api = TranslationAPI()
        logger.debug("TranslationAPI initialized")
    if capture_manager is None:
        from component.webview_capture_manager import WebViewCaptureManager
        capture_manager = WebViewCaptureManager()
        logger.debug("WebViewCaptureManager initialized")
    return api, capture_manager

# Simple functions that PyWebView can serialize
def get_available_monitors():
    """Get available monitors - returns simple dicts"""
    logger.debug("get_available_monitors called")
    _, capture_manager = initialize_components()
    monitors = capture_manager.get_available_monitors()
    logger.debug(f"Returning {len(monitors)} monitors")
    return monitors

def get_monitor_preview(monitor_index):
    """Get a preview screenshot of the monitor"""
    logger.debug(f"get_monitor_preview called for monitor {monitor_index}")
    start_time = time.time()
    
    try:
        _, capture_manager = initialize_components()
        # Take a screenshot of the monitor
        screenshot_data = capture_manager.get_monitor_screenshot(monitor_index)
        
        if screenshot_data:
            processing_time = time.time() - start_time
            logger.debug(f"Preview generated in {processing_time:.2f}s, size: {len(screenshot_data)} bytes")
            return {
                'image': screenshot_data,
                'width': 1920,  # These should come from actual monitor dimensions
                'height': 1080
            }
        else:
            logger.warning(f"No screenshot data returned for monitor {monitor_index}")
            return None
    except Exception as e:
        logger.error(f"Failed to get monitor preview: {str(e)}")
        return None

def get_monitor_preview_optimized(monitor_index):
    """Get optimized preview for GPU rendering"""
    logger.debug(f"get_monitor_preview_optimized called for monitor {monitor_index}")
    _, capture_manager = initialize_components()
    return capture_manager.get_monitor_preview_optimized(monitor_index)

def translate_text(text: str, source_lang: str, target_lang: str):
    """Called from JavaScript to perform translation"""
    logger.debug(f"translate_text called: '{text[:50]}...' ({source_lang}->{target_lang})")
    api, _ = initialize_components()
    
    start_time = time.time()
    try:
        translated = api.translate_text(text, source_lang, target_lang)
        processing_time = time.time() - start_time
        logger.debug(f"Translation completed in {processing_time:.2f}s: '{translated[:50]}...'")
        return translated
    except Exception as e:
        logger.error(f"Translation failed: {str(e)}")
        return f"Translation error: {str(e)}"

def start_screen_capture(monitor_index):
    """Start screen capture"""
    logger.debug(f"start_screen_capture called for monitor {monitor_index}")
    _, capture_manager = initialize_components()
    result = capture_manager.start_capture(monitor_index)
    logger.debug(f"start_screen_capture result: {result}")
    return result

def stop_screen_capture():
    """Stop screen capture"""
    logger.debug("stop_screen_capture called")
    _, capture_manager = initialize_components()
    capture_manager.stop_capture()
    return True

def set_capture_languages(source_lang, target_lang):
    """Set languages for screen capture"""
    logger.debug(f"set_capture_languages called: {source_lang}->{target_lang}")
    _, capture_manager = initialize_components()
    capture_manager.set_languages(source_lang, target_lang)
    return True

class FnTranslateUI:
    def __init__(self):
        self.window = None
        self.html = get_html_template()
        
        # Initialize components
        initialize_components()
        
        # Set up callbacks for the capture manager
        if capture_manager:
            capture_manager.set_callbacks(
                translation_cb=self._on_translation_ready,
                status_cb=self._on_status_update,
                error_cb=self._on_error
            )
        
        logger.info("UI initialized")
        
        self.__name__ = 'FnTranslateUI'
        self.__qualname__ = 'FnTranslateUI'
    
    def _on_translation_ready(self, translated_text):
        """Handle new translation from screen capture"""
        logger.debug(f"Translation ready callback: '{translated_text[:100]}...'")
        if self.window:
            try:
                # Use json.dumps for proper escaping
                js_code = f"showTranslation({json.dumps(translated_text)});"
                self.window.evaluate_js(js_code)
                logger.info(f"Translation sent to UI: {translated_text[:100]}...")
            except Exception as e:
                logger.error(f"Failed to send translation to JS: {str(e)}")
    
    def _on_status_update(self, message):
        """Handle status updates"""
        logger.debug(f"Status update callback: {message}")
        if self.window:
            try:
                js_code = f"updateStatus({json.dumps(message)});"
                self.window.evaluate_js(js_code)
            except Exception as e:
                logger.error(f"Failed to update status in JS: {str(e)}")
    
    def _on_error(self, error_message):
        """Handle errors"""
        logger.error(f"Error callback: {error_message}")
        if self.window:
            try:
                js_code = f"showError({json.dumps(error_message)});"
                self.window.evaluate_js(js_code)
            except Exception as e:
                logger.error(f"Failed to show error in JS: {str(e)}")
    
    def show(self):
        """Create and show the webview window"""
        try:
            logger.debug("Creating webview window...")
            self.window = webview.create_window(
                'F(n)Translate',
                html=self.html,
                width=1000,
                height=700,
                min_size=(800, 600),
                text_select=True
            )
            
            # Expose only simple functions (not complex objects)
            self.window.expose(
                get_available_monitors,
                translate_text,
                start_screen_capture,
                stop_screen_capture,
                set_capture_languages,
                get_monitor_preview,
                get_monitor_preview_optimized
            )
            
            logger.debug("Starting webview...")
            webview.start()
            logger.info("WebView started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start webview: {str(e)}")
            raise
