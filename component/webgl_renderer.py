# component/webgl_renderer.py
import io
import base64
import logging
from PIL import Image
import mss

logger = logging.getLogger("WebGLRenderer")

class WebGLRenderer:
    """GPU-accelerated preview renderer for smooth screen capture preview"""
    
    def __init__(self):
        self.performance_stats = {
            'fps': 0,
            'frame_time': 0,
            'memory_usage': 0
        }
        logger.info("WebGL Renderer initialized")
    
    def get_gpu_optimized_preview(self, monitor_index):
        """Get optimized screenshot for WebGL rendering"""
        try:
            with mss() as sct:
                # Convert UI index (0-based) to MSS index (1-based for physical monitors)
                mss_index = monitor_index + 1
                
                if mss_index >= len(sct.monitors):
                    logger.error(f"Invalid monitor index: {monitor_index}")
                    return None
                
                monitor = sct.monitors[mss_index]
                
                # OPTIMIZATION: Capture smaller region for preview performance
                capture_width = min(1920, monitor['width'])
                capture_height = min(1080, monitor['height'])
                
                # Center the capture region
                left = monitor['left'] + (monitor['width'] - capture_width) // 2
                top = monitor['top'] + (monitor['height'] - capture_height) // 2
                
                capture_region = {
                    'left': left,
                    'top': top,
                    'width': capture_width,
                    'height': capture_height
                }
                
                screenshot = sct.grab(capture_region)
                
                # Fast JPEG conversion optimized for WebGL
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                buffered = io.BytesIO()
                
                # Optimized for speed over quality
                img.save(buffered, format="JPEG", quality=75, optimize=True, subsampling=0)
                img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                logger.debug(f"GPU preview: {screenshot.size} -> JPEG {len(img_base64)} bytes")
                return img_base64
                
        except Exception as e:
            logger.error(f"GPU preview capture failed: {str(e)}")
            return None
    
    def get_performance_stats(self):
        """Get current performance statistics"""
        return self.performance_stats
    
    def is_webgl_supported(self):
        """Check if WebGL is likely supported (basic check)"""
        # This is a basic check - actual detection happens in JavaScript
        return True
