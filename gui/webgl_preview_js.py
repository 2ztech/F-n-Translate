def webgl_preview_js():
    return """
// WebGL Preview JavaScript

class WebGLPreviewRenderer {
    constructor() {
        this.gl = null;
        this.program = null;
        this.texture = null;
        this.isActive = false;
        this.frameCount = 0;
        this.lastFpsUpdate = 0;
    }

    initialize(canvasElement) {
        try {
            // Get WebGL context
            this.gl = canvasElement.getContext('webgl2') || 
                     canvasElement.getContext('webgl') || 
                     canvasElement.getContext('experimental-webgl');
            
            if (!this.gl) {
                console.error('❌ WebGL not supported');
                return false;
            }

            console.log('✅ WebGL renderer initialized:', this.gl.getParameter(this.gl.VERSION));
            
            // Create shader program
            this.program = this.createShaderProgram();
            this.texture = this.gl.createTexture();
            
            // Setup geometry
            this.setupGeometry();
            
            // Configure texture
            this.configureTexture();
            
            return true;
            
        } catch (error) {
            console.error('❌ WebGL initialization failed:', error);
            return false;
        }
    }

    createShaderProgram() {
        const vsSource = `
            attribute vec2 a_position;
            attribute vec2 a_texcoord;
            varying vec2 v_texcoord;
            
            void main() {
                gl_Position = vec4(a_position, 0, 1);
                v_texcoord = a_texcoord;
            }
        `;
        
        const fsSource = `
            precision mediump float;
            varying vec2 v_texcoord;
            uniform sampler2D u_texture;
            
            void main() {
                gl_FragColor = texture2D(u_texture, v_texcoord);
            }
        `;
        
        const vertexShader = this.compileShader(this.gl.VERTEX_SHADER, vsSource);
        const fragmentShader = this.compileShader(this.gl.FRAGMENT_SHADER, fsSource);
        
        const program = this.gl.createProgram();
        this.gl.attachShader(program, vertexShader);
        this.gl.attachShader(program, fragmentShader);
        this.gl.linkProgram(program);
        
        if (!this.gl.getProgramParameter(program, this.gl.LINK_STATUS)) {
            throw new Error('Shader program link error: ' + this.gl.getProgramInfoLog(program));
        }
        
        return program;
    }

    compileShader(type, source) {
        const shader = this.gl.createShader(type);
        this.gl.shaderSource(shader, source);
        this.gl.compileShader(shader);
        
        if (!this.gl.getShaderParameter(shader, this.gl.COMPILE_STATUS)) {
            const error = this.gl.getShaderInfoLog(shader);
            this.gl.deleteShader(shader);
            throw new Error('Shader compile error: ' + error);
        }
        
        return shader;
    }

    setupGeometry() {
        // Vertex data for full-screen quad (positions + texture coordinates)
        const vertices = new Float32Array([
            -1, -1,  0, 1,  // bottom left
             1, -1,  1, 1,  // bottom right
            -1,  1,  0, 0,  // top left
             1,  1,  1, 0   // top right
        ]);
        
        const vertexBuffer = this.gl.createBuffer();
        this.gl.bindBuffer(this.gl.ARRAY_BUFFER, vertexBuffer);
        this.gl.bufferData(this.gl.ARRAY_BUFFER, vertices, this.gl.STATIC_DRAW);
        
        // Set up attributes
        const positionLocation = this.gl.getAttribLocation(this.program, 'a_position');
        const texcoordLocation = this.gl.getAttribLocation(this.program, 'a_texcoord');
        
        this.gl.enableVertexAttribArray(positionLocation);
        this.gl.vertexAttribPointer(positionLocation, 2, this.gl.FLOAT, false, 16, 0);
        
        this.gl.enableVertexAttribArray(texcoordLocation);
        this.gl.vertexAttribPointer(texcoordLocation, 2, this.gl.FLOAT, false, 16, 8);
    }

    configureTexture() {
        this.gl.bindTexture(this.gl.TEXTURE_2D, this.texture);
        this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_WRAP_S, this.gl.CLAMP_TO_EDGE);
        this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_WRAP_T, this.gl.CLAMP_TO_EDGE);
        this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_MIN_FILTER, this.gl.LINEAR);
        this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_MAG_FILTER, this.gl.LINEAR);
        
        // Reserve texture memory (will be updated each frame)
        this.gl.texImage2D(this.gl.TEXTURE_2D, 0, this.gl.RGBA, 1024, 1024, 0, this.gl.RGBA, this.gl.UNSIGNED_BYTE, null);
    }

    updateTexture(image) {
        this.gl.bindTexture(this.gl.TEXTURE_2D, this.texture);
        this.gl.texImage2D(this.gl.TEXTURE_2D, 0, this.gl.RGBA, this.gl.RGBA, this.gl.UNSIGNED_BYTE, image);
    }

    render() {
        if (!this.isActive) return;
        
        // Clear and render
        this.gl.clearColor(0, 0, 0, 1);
        this.gl.clear(this.gl.COLOR_BUFFER_BIT);
        
        this.gl.useProgram(this.program);
        this.gl.drawArrays(this.gl.TRIANGLE_STRIP, 0, 4);
        
        this.frameCount++;
        
        // FPS counter
        const now = Date.now();
        if (now - this.lastFpsUpdate >= 1000) {
            const fps = Math.round((this.frameCount * 1000) / (now - this.lastFpsUpdate));
            console.log(`📊 WebGL Render FPS: ${fps}`);
            this.frameCount = 0;
            this.lastFpsUpdate = now;
        }
    }

    cleanup() {
        if (this.texture) {
            this.gl.deleteTexture(this.texture);
            this.texture = null;
        }
        if (this.program) {
            this.gl.deleteProgram(this.program);
            this.program = null;
        }
        this.isActive = false;
    }
}

// Global WebGL renderer instance
let webglRenderer = null;

function startWebGLPreview(monitorIndex) {
    console.log('🎮 Starting WebGL-accelerated preview for monitor:', monitorIndex);
    
    const canvas = document.getElementById('webgl-preview');
    const placeholder = document.getElementById('preview-placeholder');
    
    if (!canvas || !placeholder) {
        console.error('❌ WebGL preview elements not found');
        return startCanvas2DPreview(monitorIndex); // Fallback
    }
    
    // Show canvas, hide placeholder
    canvas.style.display = 'block';
    placeholder.style.display = 'none';
    
    // Set canvas size
    const container = canvas.parentElement;
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
    console.log(`📐 Canvas size: ${canvas.width}x${canvas.height}`);
    
    // Initialize WebGL
    webglRenderer = new WebGLPreviewRenderer();
    const webglSupported = webglRenderer.initialize(canvas);
    
    if (!webglSupported) {
        console.warn('❌ WebGL initialization failed, falling back to Canvas2D');
        return startCanvas2DPreview(monitorIndex);
    }
    
    let previewActive = true;
    const previewImage = new Image();
    
    // FPS control variables
    let lastFrameTime = 0;
    const targetFPS = 60;
    const frameInterval = 1000 / targetFPS; // 16.67ms per frame
    
    // FPS counter
    let frameCount = 0;
    let lastFPSUpdate = 0;
    let currentFPS = 0;
    
    console.log(`🎯 Target FPS: ${targetFPS} (${frameInterval.toFixed(2)}ms per frame)`);
    
    // Separate rendering loop (GPU) - FIXED: Added currentTime parameter
    function renderLoop(currentTime) {
        if (!previewActive || !webglRenderer) return;
        
        // FPS limiting logic
        const deltaTime = currentTime - lastFrameTime;
        
        if (deltaTime >= frameInterval) {
            webglRenderer.render();
            
            // Update FPS counter
            frameCount++;
            if (currentTime - lastFPSUpdate >= 1000) {
                currentFPS = frameCount;
                frameCount = 0;
                lastFPSUpdate = currentTime;
                console.log(`📊 Current FPS: ${currentFPS}`);
            }
            
            lastFrameTime = currentTime - (deltaTime % frameInterval);
        }
        
        requestAnimationFrame(renderLoop);
    }
    
    // Start rendering loop
    webglRenderer.isActive = true;
    requestAnimationFrame(renderLoop);
    
    // Frame loading loop (separate from rendering) - limited to 60 FPS
    function loadNextFrame() {
        if (!previewActive) return;
        
        pywebview.api.get_monitor_preview_optimized(monitorIndex)
            .then(screenshotData => {
                if (screenshotData && screenshotData.image && previewActive && webglRenderer) {
                    previewImage.onload = function() {
                        webglRenderer.updateTexture(previewImage);
                        // Schedule next frame with FPS limit
                        setTimeout(loadNextFrame, frameInterval);
                    };
                    previewImage.src = `data:image/jpeg;base64,${screenshotData.image}`;
                } else {
                    console.log('⚠️ No screenshot data received, retrying...');
                    setTimeout(loadNextFrame, 100);
                }
            })
            .catch(error => {
                console.error('❌ WebGL preview error:', error);
                setTimeout(loadNextFrame, 100);
            });
    }
    
    // Start frame loading
    loadNextFrame();
    
    return function stopPreview() {
        console.log('🛑 Stopping WebGL preview...');
        previewActive = false;
        canvas.style.display = 'none';
        placeholder.style.display = 'block';
        
        if (webglRenderer) {
            webglRenderer.cleanup();
            webglRenderer = null;
        }
        
        console.log(`📊 Final FPS average: ${currentFPS}`);
    };
}

// Export functions for use in other modules
window.startWebGLPreview = startWebGLPreview;
"""
