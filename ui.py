# ui.py
import webview
import logging
from style import CSS
from api import TranslationAPI

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log',
    filemode='w'
)
logger = logging.getLogger("UI")

class FnTranslateUI:
    def __init__(self):
        self.window = None
        self.api = TranslationAPI()
        self.html = self._create_html()
        logger.info("UI initialized")
        
        self.__name__ = 'FnTranslateUI'
        self.__qualname__ = 'FnTranslateUI'
        
    def _create_html(self):
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>F(n)Translate</title>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
            <style>{CSS}</style>
        </head>
        <body>
            <div class="app-container">
                <div class="app-header">
                    <div class="logo">
                        <i class="fas fa-language"></i>
                        <h1>F(n)Translate</h1>
                    </div>
                    <div class="nav-buttons">
                        <button class="nav-btn active" data-target="text-module">Translate Text</button>
                        <button class="nav-btn" data-target="file-module">Translate File</button>
                        <button class="nav-btn" data-target="capture-module">Screen Capture</button>
                    </div>
                </div>
                
                <div class="language-bar">
                    <div class="language-selector">
                        <label>Source:</label>
                        <div class="language-dropdown">
                            <select>
                                <option>English</option>
                                <option>Malay</option>
                            </select>
                            <i class="fas fa-chevron-down"></i>
                        </div>
                    </div>
                    
                    <div class="language-selector">
                        <label>Target:</label>
                        <div class="language-dropdown">
                            <select>
                                <option>Malay</option>
                                <option>English</option>
                            </select>
                            <i class="fas fa-chevron-down"></i>
                        </div>
                    </div>
                </div>
                
                <div class="module-content">
                    <!-- Text Module (default) -->
                    <div id="text-module" class="module active">
                        <div class="text-module">
                            <div class="translation-box">
                                <h3>Source Text</h3>
                                <textarea class="translation-area" placeholder="Type to translate...">Hello! Welcome to F(n)Translate. This tool helps you translate text between multiple languages quickly and accurately.</textarea>
                            </div>
                            
                            <div class="translation-box">
                                <h3>Translation</h3>
                                <div class="translation-area">Hai! Selamat datang ke F(n)Translate. Alat ini membantu anda menterjemahkan teks antara pelbagai bahasa dengan pantas dan tepat.</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- File Module -->
                    <div id="file-module" class="module">
                        <div class="file-grid">
                            <div class="file-input">
                                <div class="upload-area" id="upload-area">
                                    <i class="fas fa-cloud-upload-alt"></i>
                                    <h3>Upload File to Translate</h3>
                                    <p>Supported formats: PDF, DOCX, TXT (Max file size: 10MB)</p>
                                </div>
                            </div>
                            
                            <div class="translation-output">
                                <div class="translation-area">
                                    Translated content will appear here...
                                </div>
                            </div>
                        </div>
                        
                        <div class="file-actions">
                            <button class="action-btn">
                                <i class="fas fa-language"></i> Translate
                            </button>
                            <button class="action-btn save">
                                <i class="fas fa-save"></i> Save Text
                            </button>
                        </div>
                    </div>
                    
                    <!-- Screen Capture Module -->
                    <div id="capture-module" class="module">
                        <div class="capture-module">
                            <div class="capture-header">
                                <div class="monitor-selector">
                                    <label>Select Monitor:</label>
                                    <div class="monitor-dropdown">
                                        <select>
                                            <option>Monitor 1</option>
                                            <option>Monitor 2</option>
                                            <option>Full Screen</option>
                                            <option>Custom Region</option>
                                        </select>
                                        <i class="fas fa-chevron-down"></i>
                                    </div>
                                </div>
                                
                                <div class="capture-controls">
                                    <button class="capture-btn">
                                        <i class="fas fa-play-circle"></i> Start
                                    </button>
                                    <button class="capture-btn stop">
                                        <i class="fas fa-stop-circle"></i> Stop
                                    </button>
                                </div>
                            </div>
                            
                            <div class="capture-preview">
                                <div class="preview-placeholder">
                                    <i class="fas fa-desktop"></i>
                                    <p>Screen preview will appear here</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="app-footer">
                    <button class="settings-btn" title="API Settings">
                        <i class="fas fa-cog"></i>
                    </button>
                    <div class="api-key-info">
                        API Status: <span>Connected</span> | Key: <span>ds-********************</span>
                    </div>
                </div>
            </div>

            <!-- API Key Modal -->
            <div id="api-modal" class="modal">
                <div class="modal-content">
                    <span class="close">&times;</span>
                    <h3>API Key Settings</h3>
                    <div class="api-input">
                        <label>DeepSeek API Key:</label>
                        <input type="password" id="api-key-input" placeholder="Enter your API key">
                    </div>
                    <button id="save-api-btn" class="action-btn">
                        <i class="fas fa-save"></i> Save Key
                    </button>
                </div>
            </div>
            <script>
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
                        }});
                    }});
                }}
                
                // File upload area interaction
                function setupFileUpload() {{
                    const uploadArea = document.getElementById('upload-area');
                    uploadArea.addEventListener('click', function() {{
                        // Show loading state
                        this.innerHTML = `
                            <i class="fas fa-spinner fa-spin"></i>
                            <h3>Processing File...</h3>
                            <p>Your document is being prepared for translation</p>
                        `;
                        
                        // Simulate file processing
                        setTimeout(() => {{
                            this.innerHTML = `
                                <i class="fas fa-check-circle" style="color: #4CAF50;"></i>
                                <h3>document.pdf Ready</h3>
                                <p>2.4MB</p>
                            `;
                        }}, 1500);
                    }});
                }}
                
                // API Settings Modal functionality
                function setupApiModal() {{
                    const settingsBtn = document.querySelector('.settings-btn');
                    const modal = document.getElementById('api-modal');
                    const closeBtn = document.querySelector('.close');
                    const saveApiBtn = document.getElementById('save-api-btn');

                    settingsBtn.addEventListener('click', () => {{
                        modal.style.display = 'block';
                    }});

                    closeBtn.addEventListener('click', () => {{
                        modal.style.display = 'none';
                    }});

                    saveApiBtn.addEventListener('click', () => {{
                        const apiKey = document.getElementById('api-key-input').value;
                        if(apiKey) {{
                            // Update API info in footer
                            const maskedKey = 'ds-' + '*'.repeat(apiKey.length - 3) + apiKey.slice(-3);
                            document.querySelector('.api-key-info span:last-child').textContent = maskedKey;
                            modal.style.display = 'none';
                            alert('API key saved successfully!');
                        }} else {{
                            alert('Please enter an API key');
                        }}
                    }});

                    window.addEventListener('click', (e) => {{
                        if(e.target === modal) {{
                            modal.style.display = 'none';
                        }}
                    }});
                }}
                
                // Real-time translation functionality
                function setupRealTimeTranslation() {{
                    const sourceTextarea = document.querySelector('#text-module .translation-area');
                    const translationOutput = document.querySelector('#text-module .translation-box:last-child .translation-area');
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
                
                // Initialize all functionality
                document.addEventListener('DOMContentLoaded', function() {{
                    setupModuleSwitching();
                    setupFileUpload();
                    setupApiModal();
                    setupRealTimeTranslation();
                }});
            </script>
        </body>
        </html>
        """
    
    def translate_text(self, text: str, source_lang: str, target_lang: str):
        """Called from JavaScript to perform translation"""
        logger.info(f"Starting translation: {source_lang} -> {target_lang}")
        try:
            translated = self.translator.translation_service.translate(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang
            )
            logger.debug(f"Translation successful: {translated[:100]}...")
            return translated
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            return str(e)
        
    def show(self):
        """Create and show the webview window"""
        try:
            self.window = webview.create_window(
                'F(n)Translate',
                html=self.html,
                js_api=self.api,  # Pass the API instance instead of self
                width=1000,
                height=700,
                min_size=(800, 600),
                text_select=True
            )
            webview.start()
        except Exception as e:
            logger.error(f"Failed to start webview: {str(e)}")
            raise