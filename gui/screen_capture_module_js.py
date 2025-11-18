# screen_capture_module_js.py
from gui.webgl_preview_js import webgl_preview_js

def screen_capture_module_js():
    webgl_js = webgl_preview_js()
    
    return f"""
    // Screen Capture Module JS
    {webgl_js}

    let stopPreviewFunction = null;
    let isCapturing = false;
    let previewFrameCount = 0;
    let lastPreviewTime = 0;

    function setupScreenCapture() {{
        console.log('Setting up screen capture...');
        
        const startButton = document.getElementById('start-capture');
        const stopButton = document.getElementById('stop-capture');
        const monitorDropdown = document.getElementById('monitor-select');
        const statusArea = document.getElementById('capture-status');

        if (!startButton || !stopButton || !monitorDropdown || !statusArea) {{
            console.error('Screen capture elements not found');
            return;
        }}

        // Load available monitors
        function loadAvailableMonitors() {{
            console.log('Loading available monitors...');
            monitorDropdown.innerHTML = '<option value="loading">Loading monitors...</option>';
            statusArea.innerHTML = '<div class="status-info"><i class="fas fa-spinner fa-spin"></i> Detecting monitors...</div>';
            
            pywebview.api.get_available_monitors()
                .then(monitors => {{
                    console.log('Monitors received:', monitors);
                    monitorDropdown.innerHTML = '';
                    
                    if (monitors.length === 0) {{
                        monitorDropdown.innerHTML = '<option value="none">No monitors detected</option>';
                        statusArea.innerHTML = '<div class="status-warning"><i class="fas fa-exclamation-triangle"></i> No monitors detected</div>';
                        return;
                    }}
                    
                    monitors.forEach(monitor => {{
                        const option = document.createElement('option');
                        option.value = monitor.index;
                        option.textContent = `${{monitor.name}} (${{monitor.width}}x${{monitor.height}})`;
                        monitorDropdown.appendChild(option);
                    }});
                    
                    // Add custom region option
                    const customOption = document.createElement('option');
                    customOption.value = 'custom';
                    customOption.textContent = 'Custom Region';
                    monitorDropdown.appendChild(customOption);
                    
                    statusArea.innerHTML = '<div class="status-success"><i class="fas fa-check-circle"></i> ' + monitors.length + ' monitor(s) detected</div>';
                    
                    // Auto-select first monitor and show preview
                    if (monitors.length > 0) {{
                        monitorDropdown.value = monitors[0].index;
                        updateMonitorPreview(monitors[0].index);
                    }}
                    
                }})
                .catch(err => {{
                    console.error('Failed to fetch monitors:', err);
                    monitorDropdown.innerHTML = '<option value="error">Error loading monitors</option>';
                    statusArea.innerHTML = '<div class="status-error"><i class="fas fa-times-circle"></i> Error detecting monitors: ' + err + '</div>';
                }});
        }}

        // Monitor selection change handler
        monitorDropdown.addEventListener('change', function() {{
            const selectedValue = this.value;
            console.log('Monitor selected:', selectedValue);
            if (selectedValue !== 'custom' && selectedValue !== 'loading' && selectedValue !== 'error' && selectedValue !== 'none') {{
                updateMonitorPreview(parseInt(selectedValue));
            }} else {{
                showPreviewPlaceholder();
            }}
        }});

        // Start screen capture
        startButton.addEventListener('click', async () => {{
            if (isCapturing) {{
                alert('Capture is already running');
                return;
            }}

            const selectedValue = monitorDropdown.value;
            let monitorIndex = 0;

            if (selectedValue === 'custom') {{
                alert('Custom region selection will be implemented in the next version');
                return;
            }} else if (selectedValue === 'loading' || selectedValue === 'error' || selectedValue === 'none') {{
                alert('Please select a valid monitor first');
                return;
            }} else {{
                monitorIndex = parseInt(selectedValue);
            }}

            try {{
                // Get current languages
                const sourceLang = document.getElementById('source-lang').value;
                const targetLang = document.getElementById('target-lang').value;
                
                // Set languages first
                await pywebview.api.set_capture_languages(sourceLang, targetLang);
                
                // Start capture
                statusArea.innerHTML = '<div class="status-info"><i class="fas fa-spinner fa-spin"></i> Starting screen capture...</div>';
                const success = await pywebview.api.start_screen_capture(monitorIndex);
                
                if (success) {{
                    isCapturing = true;
                    startButton.disabled = true;
                    stopButton.disabled = false;
                    startButton.innerHTML = '<i class="fas fa-sync fa-spin"></i> Capturing...';
                    statusArea.innerHTML = '<div class="status-success"><i class="fas fa-circle" style="color: #4caf50;"></i> Screen capture started - translations will appear as overlay on screen</div>';
                }} else {{
                    statusArea.innerHTML = '<div class="status-error"><i class="fas fa-times-circle"></i> Failed to start screen capture</div>';
                    alert('Failed to start screen capture');
                }}
            }} catch (error) {{
                console.error('Failed to start capture:', error);
                statusArea.innerHTML = '<div class="status-error"><i class="fas fa-times-circle"></i> Error: ' + error + '</div>';
                alert('Failed to start screen capture: ' + error);
            }}
        }});

        // Stop screen capture
        stopButton.addEventListener('click', async () => {{
            if (!isCapturing) {{
                return;
            }}

            try {{
                statusArea.innerHTML = '<div class="status-info"><i class="fas fa-spinner fa-spin"></i> Stopping screen capture...</div>';
                const success = await pywebview.api.stop_screen_capture();
                
                if (success) {{
                    isCapturing = false;
                    startButton.disabled = false;
                    stopButton.disabled = true;
                    startButton.innerHTML = '<i class="fas fa-play-circle"></i> Start Capture';
                    statusArea.innerHTML = '<div class="status-info"><i class="fas fa-circle" style="color: #ff6b6b;"></i> Screen capture stopped</div>';
                }} else {{
                    statusArea.innerHTML = '<div class="status-error"><i class="fas fa-times-circle"></i> Failed to stop screen capture</div>';
                    alert('Failed to stop screen capture');
                }}
            }} catch (error) {{
                console.error('Failed to stop capture:', error);
                statusArea.innerHTML = '<div class="status-error"><i class="fas fa-times-circle"></i> Error: ' + error + '</div>';
                alert('Failed to stop screen capture: ' + error);
            }}
        }});

        // Initialize the capture module
        loadAvailableMonitors();
        stopButton.disabled = true;
        showPreviewPlaceholder();
    }}

    function initializeCaptureModule() {{
        console.log('Initializing capture module...');
        setupScreenCapture();
    }}

    // Updated live preview function with WebGL support
    function startLivePreview(monitorIndex) {{
        console.log('Starting live preview for monitor:', monitorIndex);
        
        // Try WebGL preview first, fallback to Canvas2D
        try {{
            console.log('Attempting WebGL preview...');
            return startWebGLPreview(monitorIndex);
        }} catch (error) {{
            console.warn('WebGL preview failed, falling back to Canvas2D:', error);
            console.log('Starting Canvas2D preview...');
            return startCanvas2DPreview(monitorIndex);
        }}
    }}

    function updateMonitorPreview(monitorIndex) {{
        console.log('Updating monitor preview for index:', monitorIndex);
        
        // Stop any existing preview
        if (stopPreviewFunction) {{
            stopPreviewFunction();
            stopPreviewFunction = null;
        }}
        
        const placeholder = document.getElementById('preview-placeholder');
        const webglCanvas = document.getElementById('webgl-preview');
        const canvas2d = document.getElementById('preview-canvas');
        
        if (!placeholder || !webglCanvas || !canvas2d) {{
            console.error('Preview elements not found');
            return;
        }}
        
        // Show placeholder initially, hide all canvases
        placeholder.style.display = 'block';
        webglCanvas.style.display = 'none';
        canvas2d.style.display = 'none';
        
        // Get monitor details and start live preview
        pywebview.api.get_available_monitors()
            .then(monitors => {{
                const monitor = monitors.find(m => m.index === monitorIndex);
                if (monitor) {{
                    // Update placeholder with monitor info
                    placeholder.innerHTML = `
                        <i class="fas fa-desktop" style="font-size: 48px; color: #1ba1e2;"></i>
                        <h3>${{monitor.name}}</h3>
                        <p>Resolution: ${{monitor.width}}x${{monitor.height}}</p>
                        <p>Starting live preview...</p>
                    `;
                    
                    // Start live preview after a short delay
                    setTimeout(() => {{
                        stopPreviewFunction = startLivePreview(monitorIndex);
                    }}, 500);
                }} else {{
                    console.error('Monitor not found for preview:', monitorIndex);
                    showPreviewPlaceholder();
                }}
            }})
            .catch(err => {{
                console.error('Failed to get monitor details for preview:', err);
                showPreviewPlaceholder();
            }});
    }}

    function showPreviewPlaceholder() {{
        const placeholder = document.getElementById('preview-placeholder');
        const webglCanvas = document.getElementById('webgl-preview');
        const canvas2d = document.getElementById('preview-canvas');
        
        if (!placeholder || !webglCanvas || !canvas2d) {{
            console.error('Preview elements not found');
            return;
        }}
        
        // Stop any running preview
        if (stopPreviewFunction) {{
            stopPreviewFunction();
            stopPreviewFunction = null;
        }}
        
        placeholder.style.display = 'block';
        webglCanvas.style.display = 'none';
        canvas2d.style.display = 'none';
        
        if (monitorDropdown && monitorDropdown.value === 'custom') {{
            placeholder.innerHTML = `
                <i class="fas fa-crop-alt" style="font-size: 48px; color: #ff6b6b;"></i>
                <h3>Custom Region</h3>
                <p>Click "Start Capture" to select a region</p>
            `;
        }} else {{
            placeholder.innerHTML = `
                <i class="fas fa-desktop"></i>
                <p>Select a monitor to see preview</p>
            `;
        }}
    }}
"""
