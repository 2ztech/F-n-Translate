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
capture_process = None
capture_command_queue = None
capture_stop_event = None

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
    global capture_process, capture_command_queue, capture_stop_event
    
    if capture_process and capture_process.is_alive():
        logger.warning("Capture process already running")
        return False

    try:
        from services.live_translation_orchestrator import LiveTranslationProcess
        import multiprocessing
        
        status_queue = multiprocessing.Queue()
        capture_command_queue = multiprocessing.Queue()
        capture_stop_event = multiprocessing.Event()
        
        # TODO: Get actual languages from UI or config
        source_lang = "eng" 
        target_lang = "msa"
        
        capture_process = LiveTranslationProcess(
            monitor_index, 
            source_lang, 
            target_lang, 
            status_queue, 
            capture_command_queue,
            capture_stop_event
        )
        capture_process.start()
        logger.info(f"Started capture process with PID: {capture_process.pid}")
        return True
    except Exception as e:
        logger.error(f"Failed to start capture process: {str(e)}")
        return False

def stop_screen_capture():
    """Stop screen capture"""
    logger.debug("stop_screen_capture called")
    global capture_process, capture_command_queue, capture_stop_event
    
    if capture_process and capture_process.is_alive():
        if capture_stop_event:
            capture_stop_event.set()
            
        if capture_command_queue:
            capture_command_queue.put("STOP")
            
        capture_process.join(timeout=3)
        
        if capture_process.is_alive():
            logger.warning("Process did not stop gracefully, terminating...")
            capture_process.terminate()
            
        logger.info("Capture process stopped")
        return True
    return False

def set_capture_languages(source_lang, target_lang):
    """Set languages for screen capture"""
    logger.debug(f"set_capture_languages called: {source_lang}->{target_lang}")
    # Note: For the separate process, we might need to send a command to update languages
    # For now, this just logs it as the process is initialized with these values
    return True

import atexit
atexit.register(stop_screen_capture)

def check_api_key(api_key):
    """Check if API key is valid"""
    logger.debug("check_api_key called")
    api, _ = initialize_components()
    return api.check_api_key(api_key)

def save_api_key(api_key):
    """Save API key"""
    logger.debug("save_api_key called")
    api, _ = initialize_components()
    return api.save_api_key(api_key)

class FnTranslateUI:
    def __init__(self):
        self.window = None
        self.html = get_html_template()
        
        # Initialize components
        initialize_components()
        
        logger.info("UI initialized")
        
        self.__name__ = 'FnTranslateUI'
        self.__qualname__ = 'FnTranslateUI'
    
    def _on_translation_ready(self, translated_text):
        """Handle new translation from screen capture"""
        # This might need adjustment if we want to show logs in the UI from the separate process
        pass
    
    def _on_status_update(self, message):
        """Handle status updates"""
        pass
    
    def _on_error(self, error_message):
        """Handle errors"""
        pass
    
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
                get_monitor_preview_optimized,
                check_api_key,
                save_api_key
            )
            
            logger.debug("Starting webview...")
            webview.start()
            logger.info("WebView started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start webview: {str(e)}")
            raise
