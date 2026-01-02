# templates.py
from .style import CSS
from gui.ui_js import get_file_translation_js

def get_html_template():
    js_code = get_file_translation_js()
    
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
                    <select id="source-lang">
                        <option value="eng">English</option>
                        <option value="msa">Malay</option>
                    </select>
                    <i class="fas fa-chevron-down"></i>
                </div>
            </div>
            
            <div class="language-selector">
                <label>Target:</label>
                <div class="language-dropdown">
                    <select id="target-lang">
                        <option value="msa">Malay</option>
                        <option value="eng">English</option>
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
                        <div class="translation-area" id="translation-result"></div>
                    </div>
                </div>
            </div>
            
            <!-- File Module -->
            <div id="file-module" class="module">
                <div class="file-container">
                    <div class="file-input">
                        <div class="upload-area" id="upload-area">
                            <i class="fas fa-file-word"></i>
                            <h3>Upload File to Translate</h3>
                            <p>Supported formats: DOCX, TXT (Max file size: 10MB)</p>
                        </div>
                    </div>
                </div>
                
                <div class="file-actions" id="file-module-actions">
                    <button class="action-btn" id="main-translate-btn">
                        <i class="fas fa-language"></i> Translate
                    </button>
                    <button class="action-btn save" id="main-save-btn" disabled>
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
                                <select id="monitor-select">
                                    <option value="loading">Loading monitors...</option>
                                </select>
                                <i class="fas fa-chevron-down"></i>
                            </div>
                        </div>
                        
                        <div class="capture-controls">
                            <button class="capture-btn secondary" id="select-area">
                                <i class="fas fa-expand"></i> Select Area
                            </button>
                            <button class="capture-btn" id="start-capture">
                                <i class="fas fa-play-circle"></i> Start
                            </button>
                            <button class="capture-btn stop" id="stop-capture">
                                <i class="fas fa-stop-circle"></i> Stop
                            </button>
                        </div>
                    </div>
                    
                    <div class="capture-preview" id="preview-container">
                        <div class="preview-placeholder" id="preview-placeholder" style="display: none;">
                            <i class="fas fa-desktop"></i>
                            <p>Select a monitor to see preview</p>
                        </div>
                        <canvas id="webgl-preview" style="display: none;"></canvas>
                        <canvas id="preview-canvas" style="display: none;"></canvas>
                    </div>
                    
                    <div class="capture-status" id="capture-status">
                        <div class="status-info">
                            <i class="fas fa-info-circle"></i> 
                            Ready to start screen capture
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
            <div class="modal-actions">
                <button id="check-api-btn" class="action-btn secondary">
                    <i class="fas fa-check-circle"></i> Check API
                </button>
                <button id="save-api-btn" class="action-btn">
                    <i class="fas fa-save"></i> Save Key
                </button>
            </div>
            <div id="api-check-result" class="status-message"></div>
        </div>
    </div>
    <script>
        {js_code}
        
        // Initialize all functionality
        document.addEventListener('DOMContentLoaded', function() {{
            setupModuleSwitching();
            setupApiModal();
            
            // Initialize the module that is active by default
            const activeBtn = document.querySelector('.nav-btn.active');
            if (activeBtn) {{
                const targetModule = activeBtn.getAttribute('data-target');
                initializeModule(targetModule);
            }}
        }});
    </script>
</body>
</html>
"""
