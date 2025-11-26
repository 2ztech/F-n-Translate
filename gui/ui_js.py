# ui_js.py
from gui.file_upload_module_js import file_upload_module_js
from gui.screen_capture_module_js import screen_capture_module_js

def get_file_translation_js():
    file_upload_js = file_upload_module_js()
    screen_capture_js = screen_capture_module_js()
    
    return f"""
    // Core UI JavaScript Functions

    // Add these helper functions at the beginning of the JavaScript
    function updateStatus(message) {{
        const statusArea = document.getElementById('capture-status');
        if (statusArea) {{
            statusArea.innerHTML = '<div class="status-info"><i class="fas fa-info-circle"></i> ' + message + '</div>';
        }}
    }}

    function showError(error) {{
        const statusArea = document.getElementById('capture-status');
        if (statusArea) {{
            statusArea.innerHTML = '<div class="status-error"><i class="fas fa-times-circle"></i> ' + error + '</div>';
        }}
        alert('Error: ' + error);
    }}

    // Module switching functionality
    function setupModuleSwitching() {{
        document.querySelectorAll('.nav-btn').forEach(button => {{
            button.addEventListener('click', function() {{
                // Remove active class from all buttons
                document.querySelectorAll('.nav-btn').forEach(btn => {{
                    btn.classList.remove('active');
                }});
                            
                // Add active class to clicked button
                this.classList.add('active');
                            
                // Hide all modules
                document.querySelectorAll('.module').forEach(module => {{
                    module.classList.remove('active');
                }});
                            
                // Show target module
                const targetModule = this.getAttribute('data-target');
                document.getElementById(targetModule).classList.add('active');
                
                // Initialize the module when shown
                initializeModule(targetModule);
            }});
        }});
    }}

    // Initialize specific modules when they become active
    function initializeModule(moduleId) {{
        console.log('Initializing module:', moduleId);
        
        switch(moduleId) {{
            case 'capture-module':
                initializeCaptureModule();
                break;
            case 'text-module':
                initializeTextModule();
                break;
            case 'file-module':
                initializeFileModule();
                break;
        }}
    }}

    function initializeTextModule() {{
        console.log('Initializing text module...');
        setupRealTimeTranslation();
    }}

    // Real-time Translation Module (Text Module)
    function setupRealTimeTranslation() {{
        const sourceTextarea = document.querySelector('#text-module .translation-area');
        const translationOutput = document.querySelector('#text-module .translation-box:last-child .translation-area');
        
        if (!sourceTextarea || !translationOutput) {{
            console.error('Text translation elements not found');
            return;
        }}

        const sourceLangSelect = document.querySelector('.language-selector:first-child select');
        const targetLangSelect = document.querySelector('.language-selector:last-child select');
        
        let typingTimer;
        const typingDelay = 3000; // 3 seconds
        let isTranslating = false;
        
        sourceTextarea.addEventListener('input', function() {{
            clearTimeout(typingTimer);
            
            if (isTranslating) {{
                return;
            }}
            
            if (this.value.trim()) {{
                // Show loading indicator
                translationOutput.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Translating...';
                
                typingTimer = setTimeout(() => {{
                    isTranslating = true;
                    const text = this.value;
                    const sourceLang = sourceLangSelect.value;
                    const targetLang = targetLangSelect.value;
                    
                    pywebview.api.translate_text(text, sourceLang, targetLang)
                        .then(translated => {{
                            translationOutput.textContent = translated;
                            isTranslating = false;
                        }})
                        .catch(error => {{
                            translationOutput.textContent = 'Error: ' + error;
                            isTranslating = false;
                        }});
                }}, typingDelay);
            }} else {{
                translationOutput.textContent = '';
            }}
        }});
    }}

    function setupApiModal() {{
        const settingsBtn = document.querySelector('.settings-btn');
        const modal = document.getElementById('api-modal');
        const closeBtn = document.querySelector('.close');
        const saveApiBtn = document.getElementById('save-api-btn');
        const checkApiBtn = document.getElementById('check-api-btn');
        const resultDiv = document.getElementById('api-check-result');

        if (!settingsBtn || !modal || !closeBtn || !saveApiBtn) {{
            console.error('API modal elements not found');
            return;
        }}

        settingsBtn.addEventListener('click', () => {{
            modal.style.display = 'block';
        }});

        closeBtn.addEventListener('click', () => {{
            modal.style.display = 'none';
            if(resultDiv) resultDiv.innerHTML = '';
        }});

        if (checkApiBtn) {{
            checkApiBtn.addEventListener('click', () => {{
                const apiKey = document.getElementById('api-key-input').value;
                if (!apiKey) {{
                    if(resultDiv) resultDiv.innerHTML = '<span style="color: red;">Please enter an API key first</span>';
                    return;
                }}
                
                if(resultDiv) resultDiv.innerHTML = '<span style="color: blue;"><i class="fas fa-spinner fa-spin"></i> Checking...</span>';
                
                pywebview.api.check_api_key(apiKey)
                    .then(isValid => {{
                        if (isValid) {{
                            if(resultDiv) resultDiv.innerHTML = '<span style="color: green;"><i class="fas fa-check"></i> API Key is valid!</span>';
                        }} else {{
                            if(resultDiv) resultDiv.innerHTML = '<span style="color: red;"><i class="fas fa-times"></i> Invalid API Key</span>';
                        }}
                    }})
                    .catch(err => {{
                        if(resultDiv) resultDiv.innerHTML = '<span style="color: red;">Error: ' + err + '</span>';
                    }});
            }});
        }}

        saveApiBtn.addEventListener('click', () => {{
            const apiKey = document.getElementById('api-key-input').value;
            if(apiKey) {{
                // Update API info in footer
                const maskedKey = 'ds-' + '*'.repeat(Math.max(0, apiKey.length - 3)) + apiKey.slice(-3);
                document.querySelector('.api-key-info span:last-child').textContent = maskedKey;
                
                // Save via backend
                pywebview.api.save_api_key(apiKey)
                    .then(() => {{
                        modal.style.display = 'none';
                        alert('API key saved successfully!');
                    }});
            }} else {{
                alert('Please enter an API key');
            }}
        }});
        
        window.addEventListener('click', (e) => {{
            if(e.target === modal) {{
                modal.style.display = 'none';
                if(resultDiv) resultDiv.innerHTML = '';
            }}
        }});
    }}
    
    function showTranslation(text) {{
        // Create a notification or update a translation display area
        const translationArea = document.getElementById('translation-result');
        if (translationArea) {{
            translationArea.innerHTML = `<div class="translation-notification">
                <i class="fas fa-language"></i> 
                <strong>Live Translation:</strong> ${{text}}
            </div>`;
            
            // Auto-clear after 5 seconds
            setTimeout(() => {{
                translationArea.innerHTML = '';
            }}, 5000);
        }}
        
        console.log('Live translation received:', text);
    }}
    
    // Expose functions to Python backend
    window.showTranslation = showTranslation;
    window.updateStatus = updateStatus;
    window.showError = showError;

    // Import module-specific JavaScript
    {file_upload_js}
    {screen_capture_js}
"""
