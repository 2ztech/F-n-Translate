def get_file_translation_js():
    return """
    function setupFileUpload() {{
        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.style.display = 'none';
        document.body.appendChild(fileInput);

        let currentFile = null;

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
                    
                    // Read file content
                    const fileContent = await readFileAsBase64(file);
                    
                    // Send to Python backend
                    const filePath = await pywebview.api.save_temp_file({{
                        name: file.name,
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
                    
                    // Read file content
                    const fileContent = await readFileAsBase64(file);
                    
                    // Send to Python backend
                    const filePath = await pywebview.api.save_temp_file({{
                        name: file.name,
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

        function readFileAsBase64(file) {{
            return new Promise((resolve, reject) => {{
                const reader = new FileReader();
                reader.onload = (event) => {{
                    // Remove the data:application/octet-stream;base64, prefix
                    const base64String = event.target.result.split(',')[1];
                    resolve(base64String);
                }};
                reader.onerror = (error) => reject(error);
                reader.readAsDataURL(file);
            }});
        }}

        function showFileInfo(file) {{
            const sizeInMB = (file.size / (1024 * 1024)).toFixed(2);
            uploadArea.innerHTML = `
                <i class="fas fa-file-alt"></i>
                <h3>${{file.name}}</h3>
                <p>${{sizeInMB}} MB</p>
            `;
        }}
    }}

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
    """
