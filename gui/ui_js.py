def get_file_translation_js():
    return """
    // Add these helper functions at the beginning of the JavaScript
    function updateStatus(message) {
        const statusArea = document.getElementById('capture-status');
        if (statusArea) {
            statusArea.innerHTML = '<div class="status-info"><i class="fas fa-info-circle"></i> ' + message + '</div>';
        }
    }

    function showError(error) {
        const statusArea = document.getElementById('capture-status');
        if (statusArea) {
            statusArea.innerHTML = '<div class="status-error"><i class="fas fa-times-circle"></i> ' + error + '</div>';
        }
        alert('Error: ' + error);
    }

    // Module switching functionality
    function setupModuleSwitching() {
        document.querySelectorAll('.nav-btn').forEach(button => {
            button.addEventListener('click', function() {
                // Remove active class from all buttons
                document.querySelectorAll('.nav-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
                            
                // Add active class to clicked button
                this.classList.add('active');
                            
                // Hide all modules
                document.querySelectorAll('.module').forEach(module => {
                    module.classList.remove('active');
                });
                            
                // Show target module
                const targetModule = this.getAttribute('data-target');
                document.getElementById(targetModule).classList.add('active');
                
                // Load monitors when capture module is shown
                if (targetModule === 'capture-module') {
                    loadAvailableMonitors();
                }
            });
        });
    }

    function setupFileUpload() {
        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.style.display = 'none';
        document.body.appendChild(fileInput);

        let currentFile = null;

        // Enhanced drag-and-drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#1ba1e2';
            uploadArea.style.backgroundColor = '#f0f7ff';
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.style.borderColor = '#b8d1f0';
            uploadArea.style.backgroundColor = '#f9fbfd';
        });

        uploadArea.addEventListener('drop', async (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#b8d1f0';
            uploadArea.style.backgroundColor = '#f9fbfd';
            
            if (e.dataTransfer.files.length) {
                try {
                    const file = e.dataTransfer.files[0];
                    uploadArea.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing file...';
                    
                    // Read file content
                    const fileContent = await readFileAsBase64(file);
                    
                    // Send to Python backend
                    const filePath = await pywebview.api.save_temp_file({
                        name: file.name,
                        content: fileContent
                    });
                    
                    currentFile = {
                        name: file.name,
                        path: filePath,
                        size: file.size
                    };
                    showFileInfo(currentFile);
                } catch (error) {
                    console.error('File upload failed:', error);
                    uploadArea.innerHTML = `
                        <i class="fas fa-exclamation-triangle"></i>
                        <h3>Upload Failed</h3>
                        <p>${error.message || error}</p>
                        <p>Click to try again</p>
                    `;
                }
            }
        });

        // Click handler for manual selection
        uploadArea.addEventListener('click', () => {
            fileInput.click();
        });

        fileInput.addEventListener('change', async () => {
            if (fileInput.files.length) {
                try {
                    const file = fileInput.files[0];
                    uploadArea.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing file...';
                    
                    // Read file content
                    const fileContent = await readFileAsBase64(file);
                    
                    // Send to Python backend
                    const filePath = await pywebview.api.save_temp_file({
                        name: file.name,
                        content: fileContent
                    });
                    
                    currentFile = {
                        name: file.name,
                        path: filePath,
                        size: file.size
                    };
                    showFileInfo(currentFile);
                } catch (error) {
                    console.error('File selection failed:', error);
                    uploadArea.innerHTML = `
                        <i class="fas fa-exclamation-triangle"></i>
                        <h3>Upload Failed</h3>
                        <p>${error.message || error}</p>
                        <p>Click to try again</p>
                    `;
                }
            }
        });

        function readFileAsBase64(file) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = (event) => {
                    // Remove the data:application/octet-stream;base64, prefix
                    const base64String = event.target.result.split(',')[1];
                    resolve(base64String);
                };
                reader.onerror = (error) => reject(error);
                reader.readAsDataURL(file);
            });
        }

        function showFileInfo(file) {
            const sizeInMB = (file.size / (1024 * 1024)).toFixed(2);
            uploadArea.innerHTML = `
                <i class="fas fa-file-alt"></i>
                <h3>${file.name}</h3>
                <p>${sizeInMB} MB</p>
            `;
        }
    }

    function setupRealTimeTranslation() {
        const sourceTextarea = document.querySelector('#text-module .translation-area');
        const translationOutput = document.querySelector('#text-module .translation-box:last-child .translation-area');
        const sourceLangSelect = document.querySelector('.language-selector:first-child select');
        const targetLangSelect = document.querySelector('.language-selector:last-child select');
        
        let typingTimer;
        const typingDelay = 3000; // 3 seconds
        let isTranslating = false;
        
        sourceTextarea.addEventListener('input', function() {
            clearTimeout(typingTimer);
            
            if (isTranslating) {
                return;
            }
            
            if (this.value.trim()) {
                // Show loading indicator
                translationOutput.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Translating...';
                
                typingTimer = setTimeout(() => {
                    isTranslating = true;
                    const text = this.value;
                    const sourceLang = sourceLangSelect.value;
                    const targetLang = targetLangSelect.value;
                    
                    pywebview.api.translate_text(text, sourceLang, targetLang)
                        .then(translated => {
                            translationOutput.textContent = translated;
                            isTranslating = false;
                        })
                        .catch(error => {
                            translationOutput.textContent = 'Error: ' + error;
                            isTranslating = false;
                        });
                }, typingDelay);
            } else {
                translationOutput.textContent = '';
            }
        });
    }

    function setupScreenCapture() {
        const startButton = document.getElementById('start-capture');
        const stopButton = document.getElementById('stop-capture');
        const monitorDropdown = document.getElementById('monitor-select');
        const statusArea = document.getElementById('capture-status');
        let isCapturing = false;

        // Load available monitors
        function loadAvailableMonitors() {
            monitorDropdown.innerHTML = '<option value="loading">Loading monitors...</option>';
            statusArea.innerHTML = '<div class="status-info"><i class="fas fa-spinner fa-spin"></i> Detecting monitors...</div>';
            
            pywebview.api.get_available_monitors()
                .then(monitors => {
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
            if (selectedValue !== 'custom' && selectedValue !== 'loading' && selectedValue !== 'error' && selectedValue !== 'none') {
                updateMonitorPreview(parseInt(selectedValue));
            } else {
                showPreviewPlaceholder();
            }
        });

        function updateMonitorPreview(monitorIndex) {
            const placeholder = document.getElementById('preview-placeholder');
            const canvas = document.getElementById('preview-canvas');
            
            // Show monitor info in preview
            pywebview.api.get_available_monitors()
                .then(monitors => {
                    const monitor = monitors.find(m => m.index === monitorIndex);
                    if (monitor) {
                        placeholder.innerHTML = `
                            <i class="fas fa-desktop" style="font-size: 48px; color: #1ba1e2;"></i>
                            <h3>${monitor.name}</h3>
                            <p>Resolution: ${monitor.width}x${monitor.height}</p>
                            <p>Position: (${monitor.left}, ${monitor.top})</p>
                            <p style="color: #666; font-size: 12px; margin-top: 10px;">
                                <i class="fas fa-info-circle"></i> 
                                Translations will appear as overlay on the selected screen
                            </p>
                        `;
                    }
                });
        }

        function showPreviewPlaceholder() {
            const placeholder = document.getElementById('preview-placeholder');
            const canvas = document.getElementById('preview-canvas');
            
            placeholder.style.display = 'block';
            canvas.style.display = 'none';
            
            if (monitorDropdown.value === 'custom') {
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

        // Start screen capture
        startButton.addEventListener('click', async () => {
            if (isCapturing) {
                alert('Capture is already running');
                return;
            }

            const selectedValue = monitorDropdown.value;
            let monitorIndex = 0;
            let captureArea = null;

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
                const success = await pywebview.api.start_screen_capture(monitorIndex, captureArea);
                
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

        // Initialize
        loadAvailableMonitors();
        stopButton.disabled = true;
    }

    function setupApiModal() {
        const settingsBtn = document.querySelector('.settings-btn');
        const modal = document.getElementById('api-modal');
        const closeBtn = document.querySelector('.close');
        const saveApiBtn = document.getElementById('save-api-btn');

        settingsBtn.addEventListener('click', () => {
            modal.style.display = 'block';
        });

        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });

        saveApiBtn.addEventListener('click', () => {
            const apiKey = document.getElementById('api-key-input').value;
            if(apiKey) {
                // Update API info in footer
                const maskedKey = 'ds-' + '*'.repeat(apiKey.length - 3) + apiKey.slice(-3);
                document.querySelector('.api-key-info span:last-child').textContent = maskedKey;
                modal.style.display = 'none';
                alert('API key saved successfully!');
            } else {
                alert('Please enter an API key');
            }
        });

        window.addEventListener('click', (e) => {
            if(e.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
    """
