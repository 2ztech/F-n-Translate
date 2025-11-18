# ui.py
import webview
import logging
import sys
import os
from .style import CSS
from api import TranslationAPI
from .ui_js import get_file_translation_js
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from component.screen_capture_manager import ScreenCaptureManager
from component.transparent_window import TransparentWindow

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
        self.capture_manager = ScreenCaptureManager()
        self.capture_manager.translation_ready.connect(self._on_translation_ready)
        self.capture_manager.status_update.connect(self._on_status_update)
        self.capture_manager.error_occurred.connect(self._on_error)
        logger.info("UI initialized")
        
        self.__name__ = 'FnTranslateUI'
        self.__qualname__ = 'FnTranslateUI'
    
    
    def _on_translation_ready(self, translated_text):
        """Handle new translation from screen capture"""
        # You can update UI or log the translation
        print(f"New translation: {translated_text}")
        
    def _on_status_update(self, message):
        """Handle status updates"""
        print(f"Status: {message}")
        
    def _on_error(self, error_message):
        """Handle errors"""
        print(f"Error: {error_message}")
        
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
                                <textarea class="translation-area" placeholder="Type to translate..."></textarea>
                            </div>
                            
                            <div class="translation-box">
                                <h3>Translation</h3>
                                <div class="translation-area"></div>
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
                
                function setupFileUpload() {{
                            const uploadArea = document.getElementById('upload-area');
                            const fileInput = document.createElement('input');
                            fileInput.type = 'file';
                            fileInput.style.display = 'none';
                            document.body.appendChild(fileInput);

                            const translateBtn = document.querySelector('#file-module .action-btn');
                            const saveBtn = document.querySelector('#file-module .action-btn.save');
                            const outputArea = document.querySelector('#file-module .translation-area');
                            let currentFile = null;
                            let translatedFilePath = null;

                            // Enhanced drag-and-drop
                            uploadArea.addEventListener('dragover', (e) => {{
                                e.preventDefault();
                                uploadArea.style.borderColor = '#1ba1e2';
                                uploadArea.style.backgroundColor = '#f0f7ff';
                            }});

                            uploadArea.addEventListener('dragleave', () => {{
                                uploadArea.style.borderColor = '#b8d1f0';
                                uploadArea.style.backgroundColor = '#f9fbfd';
                            }});

                            uploadArea.addEventListener('drop', async (e) => {{
                                e.preventDefault();
                                uploadArea.style.borderColor = '#b8d1f0';
                                uploadArea.style.backgroundColor = '#f9fbfd';
                                
                                if (e.dataTransfer.files.length) {{
                                    try {{
                                        const file = e.dataTransfer.files[0];
                                        uploadArea.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing file...';
                                        
                                        // Read file as base64
                                        const fileContent = await readFileAsBase64(file);
                                        
                                        // Save file to temp location
                                        const filePath = await pywebview.api.save_temp_file({{
                                            name: file.name,
                                            size: file.size,
                                            type: file.type,
                                            content: fileContent
                                            }});
                                        
                                        currentFile = {{
                                            name: file.name,
                                            path: filePath,
                                            size: file.size
                                        }};
                                        showFileInfo(currentFile);
                                    }} catch (error) {{
                                        console.error('File upload failed:', error);
                                        uploadArea.innerHTML = `
                                            <i class="fas fa-exclamation-triangle"></i>
                                            <h3>Upload Failed</h3>
                                            <p>${{error.message || error}}</p>
                                            <p>Click to try again</p>
                                        `;
                                    }}
                                }}
                            }});

                            // Click handler for manual selection
                            uploadArea.addEventListener('click', () => {{
                                fileInput.click();
                            }});

                            fileInput.addEventListener('change', async () => {{
                                if (fileInput.files.length) {{
                                    try {{
                                        const file = fileInput.files[0];
                                        uploadArea.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing file...';
                                        
                                        // Read file as base64
                                        const fileContent = await readFileAsBase64(file);
                                        
                                        // Save file to temp location
                                        const filePath = await pywebview.api.save_temp_file({{
                                            name: file.name,
                                            size: file.size,
                                            type: file.type,
                                            content: fileContent
                                        }});
                                        
                                        currentFile = {{
                                            name: file.name,
                                            path: filePath,
                                            size: file.size
                                        }};
                                        showFileInfo(currentFile);
                                    }} catch (error) {{
                                        console.error('File selection failed:', error);
                                        uploadArea.innerHTML = `
                                            <i class="fas fa-exclamation-triangle"></i>
                                            <h3>Upload Failed</h3>
                                            <p>${{error.message || error}}</p>
                                            <p>Click to try again</p>
                                        `;
                                    }}
                                }}
                            }});

                            // Translate button handler
                            translateBtn.addEventListener('click', async () => {{
                                if (!currentFile) {{
                                    alert('Please select a file first');
                                    return;
                                }}

                                const sourceLang = document.querySelector('.language-selector:first-child select').value;
                                const targetLang = document.querySelector('.language-selector:last-child select').value;
                                
                                outputArea.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Translating...';
                                
                                try {{
                                    const result = await pywebview.api.translate_file(
                                        currentFile.path, 
                                        sourceLang, 
                                        targetLang
                                    );
                                    
                                    if (result.status === 'success') {{
                                        translatedFilePath = result.translated_file;
                                        outputArea.innerHTML = `
                                            <div class="translation-success">
                                                <i class="fas fa-check-circle"></i>
                                                <h3>Translation Complete!</h3>
                                                <p>Click "Save Text" to download the translated file.</p>
                                            </div>
                                        `;
                                    }} else {{
                                        outputArea.innerHTML = `
                                            <div class="translation-error">
                                                <i class="fas fa-exclamation-triangle"></i>
                                                <h3>Translation Failed</h3>
                                                <p>${{result.message}}</p>
                                            </div>
                                        `;
                                    }}
                                }} catch (error) {{
                                    outputArea.innerHTML = `
                                        <div class="translation-error">
                                            <i class="fas fa-exclamation-triangle"></i>
                                            <h3>Translation Error</h3>
                                            <p>${{error.message || error}}</p>
                                        </div>
                                    `;
                                }}
                            }});

                            // Save button handler
                            saveBtn.addEventListener('click', async () => {{
                                if (!translatedFilePath) {{
                                    alert('Please translate a file first');
                                    return;
                                }}

                                try {{
                                    const result = await pywebview.api.save_translated_file(translatedFilePath);
                                    if (result.status === 'success') {{
                                        alert('File saved successfully!');
                                    }} else if (result.status === 'cancelled') {{
                                        // User cancelled the save dialog
                                    }} else {{
                                        alert('Save failed: ' + result.message);
                                    }}
                                }} catch (error) {{
                                    alert('Save failed: ' + error.message);
                                }}
                            }});

                            function showFileInfo(file) {{
                                const sizeInMB = (file.size / (1024 * 1024)).toFixed(2);
                                uploadArea.innerHTML = `
                                    <i class="fas fa-file-alt"></i>
                                    <h3>${{file.name}}</h3>
                                    <p>${{sizeInMB}} MB</p>
                                `;
                            }}
                            
                            function readFileAsBase64(file) {{
                                return new Promise((resolve, reject) => {{
                                    const reader = new FileReader();
                                    reader.onload = (event) => resolve(event.target.result);
                                    reader.onerror = (error) => reject(error);
                                    reader.readAsDataURL(file);
                                }});
                            }}
                        }}
                
                // Initialize all functionality
                document.addEventListener('DOMContentLoaded', function() {{
                    setupModuleSwitching();
                    setupFileUpload();
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
        
    # In FnTranslateUI.show() method:
    def show(self):
        """Create and show the webview window"""
        try:
            self.window = webview.create_window(
                'F(n)Translate',
                html=self.html,
                js_api=self.api,
                width=1000,
                height=700,
                min_size=(800, 600),
                text_select=True
            )
            
            # Add file download handler
            def handle_download(file_info):
                if file_info['status'] == 'success':
                    try:
                        self.window.create_file_dialog(
                            webview.SAVE_DIALOG,
                            directory='/',
                            save_filename=file_info['file_name']
                        )
                        # Webview will handle the actual file save
                    except Exception as e:
                        logger.error(f"Download failed: {str(e)}")
            
            self.api.download_file = lambda file_id: handle_download(
                self.api.download_file(file_id)
            )
            
            webview.start()
        except Exception as e:
            logger.error(f"Failed to start webview: {str(e)}")
            raise
