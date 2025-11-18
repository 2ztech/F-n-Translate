# screen_capture_module_js.py

def screen_capture_module_js():
    return """
    // Screen Capture Module JS

    let stopPreviewFunction = null;
    let isCapturing = false;
    let previewFrameCount = 0;
    let lastPreviewTime = 0;

    function setupScreenCapture() {
        console.log('Setting up screen capture...');
        
        const startButton = document.getElementById('start-capture');
        const stopButton = document.getElementById('stop-capture');
        const monitorDropdown = document.getElementById('monitor-select');
        const statusArea = document.getElementById('capture-status');

        if (!startButton || !stopButton || !monitorDropdown || !statusArea) {
            console.error('Screen capture elements not found');
            return;
        }

        // Load available monitors
        function loadAvailableMonitors() {
            console.log('Loading available monitors...');
            monitorDropdown.innerHTML = '<option value="loading">Loading monitors...</option>';
            statusArea.innerHTML = '<div class="status-info"><i class="fas fa-spinner fa-spin"></i> Detecting monitors...</div>';
            
            pywebview.api.get_available_monitors()
                .then(monitors => {
                    console.log('Monitors received:', monitors);
                    monitorDropdown.innerHTML = '';
                    
                    if (monitors.length === 0) {
                        monitorDropdown.innerHTML = '<option value="none">No monitors detected</option>';
                        statusArea.innerHTML = '<div class="status-warning"><i class="fas fa-exclamation-triangle"></i> No monitors detected</div>';
                        return;
                    }
                    
                    monitors.forEach(monitor => {
                        const option = document.createElement('option');
                        option.value = monitor.index;
                        option.textContent = `${monitor.name} (${monitor.width}x${monitor.height})`;
                        monitorDropdown.appendChild(option);
                    });
                    
                    // Add custom region option
                    const customOption = document.createElement('option');
                    customOption.value = 'custom';
                    customOption.textContent = 'Custom Region';
                    monitorDropdown.appendChild(customOption);
                    
                    statusArea.innerHTML = '<div class="status-success"><i class="fas fa-check-circle"></i> ' + monitors.length + ' monitor(s) detected</div>';
                    
                    // Auto-select first monitor and show preview
                    if (monitors.length > 0) {
                        monitorDropdown.value = monitors[0].index;
                        updateMonitorPreview(monitors[0].index);
                    }
                    
                })
                .catch(err => {
                    console.error('Failed to fetch monitors:', err);
                    monitorDropdown.innerHTML = '<option value="error">Error loading monitors</option>';
                    statusArea.innerHTML = '<div class="status-error"><i class="fas fa-times-circle"></i> Error detecting monitors: ' + err + '</div>';
                });
        }

        // Monitor selection change handler
        monitorDropdown.addEventListener('change', function() {
            const selectedValue = this.value;
            console.log('Monitor selected:', selectedValue);
            if (selectedValue !== 'custom' && selectedValue !== 'loading' && selectedValue !== 'error' && selectedValue !== 'none') {
                updateMonitorPreview(parseInt(selectedValue));
            } else {
                showPreviewPlaceholder();
            }
        });

        // Start screen capture
        startButton.addEventListener('click', async () => {
            if (isCapturing) {
                alert('Capture is already running');
                return;
            }

            const selectedValue = monitorDropdown.value;
            let monitorIndex = 0;

            if (selectedValue === 'custom') {
                alert('Custom region selection will be implemented in the next version');
                return;
            } else if (selectedValue === 'loading' || selectedValue === 'error' || selectedValue === 'none') {
                alert('Please select a valid monitor first');
                return;
            } else {
                monitorIndex = parseInt(selectedValue);
            }

            try {
                // Get current languages
                const sourceLang = document.getElementById('source-lang').value;
                const targetLang = document.getElementById('target-lang').value;
                
                // Set languages first
                await pywebview.api.set_capture_languages(sourceLang, targetLang);
                
                // Start capture
                statusArea.innerHTML = '<div class="status-info"><i class="fas fa-spinner fa-spin"></i> Starting screen capture...</div>';
                const success = await pywebview.api.start_screen_capture(monitorIndex);
                
                if (success) {
                    isCapturing = true;
                    startButton.disabled = true;
                    stopButton.disabled = false;
                    startButton.innerHTML = '<i class="fas fa-sync fa-spin"></i> Capturing...';
                    statusArea.innerHTML = '<div class="status-success"><i class="fas fa-circle" style="color: #4caf50;"></i> Screen capture started - translations will appear as overlay on screen</div>';
                } else {
                    statusArea.innerHTML = '<div class="status-error"><i class="fas fa-times-circle"></i> Failed to start screen capture</div>';
                    alert('Failed to start screen capture');
                }
            } catch (error) {
                console.error('Failed to start capture:', error);
                statusArea.innerHTML = '<div class="status-error"><i class="fas fa-times-circle"></i> Error: ' + error + '</div>';
                alert('Failed to start screen capture: ' + error);
            }
        });

        // Stop screen capture
        stopButton.addEventListener('click', async () => {
            if (!isCapturing) {
                return;
            }

            try {
                statusArea.innerHTML = '<div class="status-info"><i class="fas fa-spinner fa-spin"></i> Stopping screen capture...</div>';
                const success = await pywebview.api.stop_screen_capture();
                
                if (success) {
                    isCapturing = false;
                    startButton.disabled = false;
                    stopButton.disabled = true;
                    startButton.innerHTML = '<i class="fas fa-play-circle"></i> Start Capture';
                    statusArea.innerHTML = '<div class="status-info"><i class="fas fa-circle" style="color: #ff6b6b;"></i> Screen capture stopped</div>';
                } else {
                    statusArea.innerHTML = '<div class="status-error"><i class="fas fa-times-circle"></i> Failed to stop screen capture</div>';
                    alert('Failed to stop screen capture');
                }
            } catch (error) {
                console.error('Failed to stop capture:', error);
                statusArea.innerHTML = '<div class="status-error"><i class="fas fa-times-circle"></i> Error: ' + error + '</div>';
                alert('Failed to stop screen capture: ' + error);
            }
        });

        // Initialize the capture module
        loadAvailableMonitors();
        stopButton.disabled = true;
        showPreviewPlaceholder();
    }

    function initializeCaptureModule() {
        console.log('Initializing capture module...');
        setupScreenCapture();
    }

    // Add these new functions for live preview
    function startLivePreview(monitorIndex) {
        console.log('Starting live preview for monitor:', monitorIndex);
        
        const canvas = document.getElementById('preview-canvas');
        const placeholder = document.getElementById('preview-placeholder');
        const ctx = canvas.getContext('2d');
        
        if (!canvas || !placeholder) {
            console.error('Preview elements not found');
            return;
        }
        
        // Show canvas, hide placeholder
        canvas.style.display = 'block';
        placeholder.style.display = 'none';
        
        // Set canvas size to match preview container
        const container = canvas.parentElement;
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
        
        console.log(`Canvas size: ${canvas.width}x${canvas.height}`);
        
        // Start preview loop
        let previewActive = true;
        let frameCount = 0;
        let lastFpsUpdate = Date.now();
        let lastFrameTime = Date.now();
        
        async function previewLoop() {
            if (!previewActive) return;
            
            const frameStart = Date.now();
            frameCount++;
            
            try {
                // Get screenshot from Python backend
                const screenshotData = await pywebview.api.get_monitor_preview(monitorIndex);
                
                if (screenshotData && screenshotData.image) {
                    // Create image from base64 data
                    const img = new Image();
                    img.onload = function() {
                        // Clear canvas
                        ctx.clearRect(0, 0, canvas.width, canvas.height);
                        
                        // Calculate aspect ratios for proper autofit
                        const imgAspect = img.width / img.height;
                        const canvasAspect = canvas.width / canvas.height;
                        
                        let renderWidth, renderHeight, offsetX, offsetY;
                        
                        // Maintain aspect ratio while fitting to canvas (contain strategy)
                        if (imgAspect > canvasAspect) {
                            // Image is wider than canvas - fit to width
                            renderWidth = canvas.width;
                            renderHeight = canvas.width / imgAspect;
                            offsetX = 0;
                            offsetY = (canvas.height - renderHeight) / 2;
                        } else {
                            // Image is taller than canvas - fit to height
                            renderHeight = canvas.height;
                            renderWidth = canvas.height * imgAspect;
                            offsetX = (canvas.width - renderWidth) / 2;
                            offsetY = 0;
                        }
                        
                        // Draw scaled image to canvas with proper aspect ratio
                        ctx.drawImage(img, offsetX, offsetY, renderWidth, renderHeight);
                        
                        // Draw monitor border
                        ctx.strokeStyle = '#1ba1e2';
                        ctx.lineWidth = 2;
                        ctx.strokeRect(offsetX, offsetY, renderWidth, renderHeight);
                        
                        // Add monitor info overlay
                        ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                        ctx.fillRect(10, 10, 220, 90);
                        ctx.fillStyle = 'white';
                        ctx.font = '12px Arial';
                        ctx.fillText(`Monitor ${monitorIndex}`, 20, 30);
                        ctx.fillText(`Original: ${img.width}x${img.height}`, 20, 50);
                        ctx.fillText(`Preview: ${Math.round(renderWidth)}x${Math.round(renderHeight)}`, 20, 70);
                        
                        // Calculate and display FPS
                        const now = Date.now();
                        if (now - lastFpsUpdate >= 1000) {
                            const fps = Math.round((frameCount * 1000) / (now - lastFpsUpdate));
                            ctx.fillText(`FPS: ${fps}`, 20, 90);
                            frameCount = 0;
                            lastFpsUpdate = now;
                        }
                    };
                    img.src = `data:image/png;base64,${screenshotData.image}`;
                }
            } catch (error) {
                console.error('Preview error:', error);
            }
            
            // Calculate frame processing time and adjust delay dynamically
            const frameTime = Date.now() - frameStart;
            const targetFPS = 8; // Reduced from 10 to 8 FPS for better performance
            const targetFrameTime = 1000 / targetFPS;
            
            // Dynamic delay based on processing time - minimum 80ms delay
            const delay = Math.max(80, targetFrameTime - frameTime);
            
            // Continue preview loop
            if (previewActive) {
                setTimeout(previewLoop, delay);
            }
        }
        
        // Start the preview loop
        previewLoop();
        
        // Return function to stop preview
        return function stopPreview() {
            previewActive = false;
            canvas.style.display = 'none';
            placeholder.style.display = 'block';
            console.log('Live preview stopped');
        };
    }

    function updateMonitorPreview(monitorIndex) {
        console.log('Updating monitor preview for index:', monitorIndex);
        
        // Stop any existing preview
        if (stopPreviewFunction) {
            stopPreviewFunction();
            stopPreviewFunction = null;
        }
        
        const placeholder = document.getElementById('preview-placeholder');
        const canvas = document.getElementById('preview-canvas');
        
        if (!placeholder || !canvas) {
            console.error('Preview elements not found');
            return;
        }
        
        // Show placeholder initially
        placeholder.style.display = 'block';
        canvas.style.display = 'none';
        
        // Get monitor details and start live preview
        pywebview.api.get_available_monitors()
            .then(monitors => {
                const monitor = monitors.find(m => m.index === monitorIndex);
                if (monitor) {
                    // Update placeholder with monitor info
                    placeholder.innerHTML = `
                        <i class="fas fa-desktop" style="font-size: 48px; color: #1ba1e2;"></i>
                        <h3>${monitor.name}</h3>
                        <p>Resolution: ${monitor.width}x${monitor.height}</p>
                        <p>Starting live preview...</p>
                    `;
                    
                    // Start live preview after a short delay
                    setTimeout(() => {
                        stopPreviewFunction = startLivePreview(monitorIndex);
                    }, 500);
                } else {
                    console.error('Monitor not found for preview:', monitorIndex);
                    showPreviewPlaceholder();
                }
            })
            .catch(err => {
                console.error('Failed to get monitor details for preview:', err);
                showPreviewPlaceholder();
            });
    }

    function showPreviewPlaceholder() {
        const placeholder = document.getElementById('preview-placeholder');
        const canvas = document.getElementById('preview-canvas');
        
        if (!placeholder || !canvas) {
            console.error('Preview elements not found');
            return;
        }
        
        // Stop any running preview
        if (stopPreviewFunction) {
            stopPreviewFunction();
            stopPreviewFunction = null;
        }
        
        placeholder.style.display = 'block';
        canvas.style.display = 'none';
        
        if (monitorDropdown && monitorDropdown.value === 'custom') {
            placeholder.innerHTML = `
                <i class="fas fa-crop-alt" style="font-size: 48px; color: #ff6b6b;"></i>
                <h3>Custom Region</h3>
                <p>Click "Start Capture" to select a region</p>
            `;
        } else {
            placeholder.innerHTML = `
                <i class="fas fa-desktop"></i>
                <p>Select a monitor to see preview</p>
            `;
        }
    }
"""
