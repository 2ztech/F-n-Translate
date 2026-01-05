from gui.file_upload_module_js import file_upload_module_js
from gui.screen_capture_module_js import screen_capture_module_js

def get_file_translation_js():
    file_upload_js = file_upload_module_js()
    screen_capture_js = screen_capture_module_js()
    
    return f"""
    // Core UI JavaScript Functions

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
        const buttons = document.querySelectorAll('.nav-btn');
        if (!buttons.length) return;

        buttons.forEach(button => {{
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
                const moduleEl = document.getElementById(targetModule);
                if (moduleEl) {{
                    moduleEl.classList.add('active');
                    // Initialize the module when shown
                    initializeModule(targetModule);
                }}
            }});
        }});
    }}

    // Initialize specific modules when they become active
    function initializeModule(moduleId) {{
        console.log('Initializing module:', moduleId);
        
        switch(moduleId) {{
            case 'capture-module':
                try {{ initializeCaptureModule(); }} catch(e) {{ console.error(e); }}
                break;
            case 'text-module':
                try {{ initializeTextModule(); }} catch(e) {{ console.error(e); }}
                break;
            case 'file-module':
                try {{ initializeFileModule(); }} catch(e) {{ console.error(e); }}
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
        
        if (!sourceTextarea || !translationOutput) return;

        const sourceLangSelect = document.querySelector('.language-selector:first-child select');
        const targetLangSelect = document.querySelector('.language-selector:last-child select');
        
        let typingTimer;
        const typingDelay = 3000;
        let isTranslating = false;
        
        sourceTextarea.addEventListener('input', function() {{
            clearTimeout(typingTimer);
            
            if (isTranslating) return;
            
            if (this.value.trim()) {{
                translationOutput.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Translating...';
                
                typingTimer = setTimeout(() => {{
                    isTranslating = true;
                    const text = this.value;
                    const sourceLang = sourceLangSelect ? sourceLangSelect.value : 'eng';
                    const targetLang = targetLangSelect ? targetLangSelect.value : 'msa';
                    
                    if (window.pywebview && window.pywebview.api) {{
                        pywebview.api.translate_text(text, sourceLang, targetLang)
                            .then(translated => {{
                                translationOutput.textContent = translated;
                                isTranslating = false;
                            }})
                            .catch(error => {{
                                translationOutput.textContent = 'Error: ' + error;
                                isTranslating = false;
                            }});
                    }}
                }}, typingDelay);
            }} else {{
                translationOutput.textContent = '';
            }}
        }});
    }}

    // API Modal Setup (Fixed & Robust)
    function setupApiModal() {{
        const settingsBtn = document.querySelector('.settings-btn');
        const modal = document.getElementById('api-modal');
        const closeBtn = document.querySelector('.close');
        const saveApiBtn = document.getElementById('save-api-btn');
        const checkApiBtn = document.getElementById('check-api-btn');
        const resultDiv = document.getElementById('api-check-result');

        if (!settingsBtn || !modal) {{
            console.warn('API Modal elements missing');
            return;
        }}

        // Open Modal
        settingsBtn.addEventListener('click', () => {{
            modal.style.display = 'block';
            if(resultDiv) resultDiv.innerHTML = '';
        }});

        // Close Modal via X button
        if (closeBtn) {{
            closeBtn.addEventListener('click', () => {{
                modal.style.display = 'none';
            }});
        }}

        // Close Modal via clicking outside
        window.addEventListener('click', (e) => {{
            if(e.target === modal) {{
                modal.style.display = 'none';
            }}
        }});

        // CHECK/TEST API Key Button Logic
        if (checkApiBtn) {{
            checkApiBtn.addEventListener('click', () => {{
                const apiKeyInput = document.getElementById('api-key-input');
                const apiKey = apiKeyInput ? apiKeyInput.value : '';
                
                if (!apiKey) {{
                    if(resultDiv) resultDiv.innerHTML = '<span style="color: red;">Please enter an API key first</span>';
                    return;
                }}
                
                if(resultDiv) resultDiv.innerHTML = '<span style="color: blue;"><i class="fas fa-spinner fa-spin"></i> Checking...</span>';
                
                if (window.pywebview && window.pywebview.api) {{
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
                }} else {{
                    if(resultDiv) resultDiv.innerHTML = '<span style="color: orange;">Backend not ready</span>';
                }}
            }});
        }}

        // SAVE API Key Button Logic
        if (saveApiBtn) {{
            saveApiBtn.addEventListener('click', () => {{
                const apiKeyInput = document.getElementById('api-key-input');
                const apiKey = apiKeyInput ? apiKeyInput.value : '';
                
                if(apiKey) {{
                    // Update footer display
                    const maskedKey = 'ds-' + '*'.repeat(Math.max(0, apiKey.length - 3)) + apiKey.slice(-3);
                    const footerInfo = document.querySelector('.api-key-info span:last-child');
                    if(footerInfo) footerInfo.textContent = maskedKey;
                    
                    if (window.pywebview && window.pywebview.api) {{
                        pywebview.api.save_api_key(apiKey)
                            .then(() => {{
                                // CLOSE MODAL ON SUCCESS (No Alert)
                                modal.style.display = 'none';
                            }});
                    }}
                }} else {{
                    alert('Please enter an API key');
                }}
            }});
        }}
    }}
    
    function showTranslation(text) {{
        const translationArea = document.getElementById('translation-result');
        if (translationArea) {{
            translationArea.innerHTML = `<div class="translation-notification">
                <i class="fas fa-language"></i> 
                <strong>Live Translation:</strong> ${{text}}
            </div>`;
            setTimeout(() => {{
                translationArea.innerHTML = '';
            }}, 5000);
        }}
        console.log('Live translation received:', text);
    }}
    
    window.showTranslation = showTranslation;
    window.updateStatus = updateStatus;
    window.showError = showError;

    {file_upload_js}
    {screen_capture_js}
"""