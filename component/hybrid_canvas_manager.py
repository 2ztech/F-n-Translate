# component/hybrid_canvas_manager.py
import logging

logger = logging.getLogger("HybridCanvasManager")

class HybridCanvasManager:
    """Manages hybrid WebGL + Canvas2D rendering system for preview and text overlay"""
    
    def __init__(self):
        self.current_mode = "webgl"  # or "canvas2d"
        self.is_initialized = False
        logger.info("Hybrid Canvas Manager initialized")
    
    def get_hybrid_setup_js(self):
        """Return JavaScript code to setup hybrid canvas system"""
        return """
        function setupHybridCanvases() {
            const container = document.getElementById('preview-container');
            if (!container) {
                console.error('Preview container not found');
                return false;
            }
            
            // Clear existing content
            container.innerHTML = '';
            
            // Create WebGL background canvas for smooth preview
            const webglCanvas = document.createElement('canvas');
            webglCanvas.id = 'webgl-preview';
            webglCanvas.className = 'preview-canvas';
            webglCanvas.style.position = 'absolute';
            webglCanvas.style.zIndex = '1';
            
            // Create text overlay canvas for translations
            const textCanvas = document.createElement('canvas');
            textCanvas.id = 'text-overlay';
            textCanvas.className = 'preview-canvas';
            textCanvas.style.position = 'absolute';
            textCanvas.style.zIndex = '2';
            textCanvas.style.pointerEvents = 'none'; // Allow clicks through to background
            
            // Add both to container
            container.appendChild(webglCanvas);
            container.appendChild(textCanvas);
            
            // Initial resize
            resizeHybridCanvases();
            
            console.log('Hybrid canvas system initialized - ready for GPU acceleration');
            return true;
        }
        
        function resizeHybridCanvases() {
            const container = document.getElementById('preview-container');
            const webglCanvas = document.getElementById('webgl-preview');
            const textCanvas = document.getElementById('text-overlay');
            
            if (!container || !webglCanvas || !textCanvas) return;
            
            const width = container.clientWidth;
            const height = container.clientHeight;
            
            [webglCanvas, textCanvas].forEach(canvas => {
                canvas.width = width;
                canvas.height = height;
                canvas.style.width = width + 'px';
                canvas.style.height = height + 'px';
            });
            
            console.log(`Hybrid canvases resized to: ${width}x${height}`);
        }
        
        function isWebGLSupported() {
            try {
                const canvas = document.createElement('canvas');
                const gl = canvas.getContext('webgl2') || 
                          canvas.getContext('webgl') || 
                          canvas.getContext('experimental-webgl');
                return !!gl;
            } catch (e) {
                console.warn('WebGL not supported:', e);
                return false;
            }
        }
        
        // Initialize hybrid system
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() {
                if (isWebGLSupported()) {
                    setupHybridCanvases();
                } else {
                    console.warn('WebGL not available, using fallback rendering');
                }
            });
        } else {
            if (isWebGLSupported()) {
                setupHybridCanvases();
            }
        }
        
        // Handle window resize
        window.addEventListener('resize', resizeHybridCanvases);
        """
    
    def get_text_overlay_js(self):
        """Return JavaScript for rendering text overlay"""
        return """
        function renderTextOverlay(translations) {
            const textCanvas = document.getElementById('text-overlay');
            if (!textCanvas) {
                console.error('Text overlay canvas not found');
                return;
            }
            
            const ctx = textCanvas.getContext('2d');
            
            // Clear previous frame
            ctx.clearRect(0, 0, textCanvas.width, textCanvas.height);
            
            translations.forEach(translation => {
                const { text, x, y, fontSize = 16, color = 'white', backgroundColor = 'rgba(0,0,0,0.7)' } = translation;
                
                // Measure text
                ctx.font = `${fontSize}px Arial`;
                const metrics = ctx.measureText(text);
                const textWidth = metrics.width;
                const textHeight = fontSize;
                
                // Draw background
                ctx.fillStyle = backgroundColor;
                ctx.fillRect(x - 5, y - textHeight, textWidth + 10, textHeight + 5);
                
                // Draw text
                ctx.fillStyle = color;
                ctx.fillText(text, x, y);
                
                // Optional: Add border
                ctx.strokeStyle = '#1ba1e2';
                ctx.lineWidth = 1;
                ctx.strokeRect(x - 5, y - textHeight, textWidth + 10, textHeight + 5);
            });
        }
        """
