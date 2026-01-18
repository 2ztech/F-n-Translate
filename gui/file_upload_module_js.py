# file_upload_module_js.py

def file_upload_module_js():
    return """
    // File Upload Module JS
    let fileModuleInitialized = false;

    function setupFileUpload() {
        const uploadArea = document.getElementById('upload-area');
        if (!uploadArea || uploadArea.dataset.initialized) return;
        uploadArea.dataset.initialized = 'true';

        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = '.docx,.txt'; // Remove PDF
        fileInput.style.display = 'none';
        document.body.appendChild(fileInput);

        const translateBtn = document.getElementById('main-translate-btn');
        const saveBtn = document.getElementById('main-save-btn');

        let currentFile = null;
        let translatedFileResult = null;

        // --- Event Listeners ---
        
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
            if (e.dataTransfer.files.length) handleFileSelection(e.dataTransfer.files[0]);
        });

        uploadArea.addEventListener('click', (e) => {
            // Only trigger if clicking the area itself, not children buttons
            if (e.target.closest('.action-btn')) return;
            fileInput.click();
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) handleFileSelection(fileInput.files[0]);
        });

        if (translateBtn) {
            translateBtn.onclick = async () => {
                if (currentFile) {
                    try {
                        const hasKey = await pywebview.api.is_api_key_set();
                        if (!hasKey) {
                            alert("Warning: API Key is missing. Please set it in Settings to translate.");
                            return;
                        }
                        performFileTranslation();
                    } catch (e) {
                         console.error("API check failed:", e);
                         // Fallback - try anyway, the backend might handle it or error out
                         performFileTranslation();
                    }
                }
                else alert('Please upload a file first');
            };
        }

        if (saveBtn) {
            saveBtn.onclick = async () => {
                if (translatedFileResult && translatedFileResult.translated_file) {
                    await pywebview.api.save_translated_file(translatedFileResult.translated_file);
                }
            };
        }

        // --- Helper Functions ---

        async function handleFileSelection(file) {
            // Check extension
            const ext = file.name.split('.').pop().toLowerCase();
            if (ext !== 'docx' && ext !== 'txt') {
                alert('Only DOCX and TXT files are supported.');
                return;
            }

            try {
                uploadArea.innerHTML = '<div class="loading-spinner"></div><p>Uploading & Processing...</p>';
                
                const fileContent = await readFileAsBase64(file);
                
                // Upload to temp storage
                const filePath = await pywebview.api.save_temp_file({
                    name: file.name,
                    content: fileContent
                });
                
                currentFile = {
                    name: file.name,
                    path: filePath,
                    size: file.size
                };
                
                translatedFileResult = null;
                if (saveBtn) saveBtn.disabled = true;
                
                renderFileInfo(currentFile);
                
            } catch (error) {
                console.error('Upload error:', error);
                renderError('Upload Failed', error.message);
            }
        }

        function readFileAsBase64(file) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = (e) => resolve(e.target.result.split(',')[1]);
                reader.onerror = reject;
                reader.readAsDataURL(file);
            });
        }

        function renderFileInfo(file) {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
            uploadArea.innerHTML = `
                <div class="file-info-card">
                    <i class="fas fa-file-word fa-3x" style="color: #1ba1e2; margin-bottom: 15px;"></i>
                    <h3>${file.name}</h3>
                    <p>${sizeMB} MB</p>
                    <p style="margin-top: 10px; color: #1ba1e2; font-weight: 500;">Ready to translate</p>
                </div>
            `;
        }
        
        async function performFileTranslation() {
            if (!currentFile) return;
            
            translateBtn.disabled = true;
            renderTranslating();
            
            try {
                const sourceLang = document.getElementById('source-lang')?.value || 'auto';
                const targetLang = document.getElementById('target-lang')?.value || 'msa';
                
                const result = await pywebview.api.translate_file(currentFile.path, sourceLang, targetLang);
                
                if (result.status === 'success') {
                    translatedFileResult = result;
                    if (saveBtn) saveBtn.disabled = false;
                    renderSuccess(result);
                } else {
                    throw new Error(result.message || 'Unknown error during translation');
                }
            } catch (error) {
                console.error('Translation error:', error);
                renderError('Translation Failed', error.message);
            } finally {
                translateBtn.disabled = false;
            }
        }
        
        function renderTranslating() {
            uploadArea.innerHTML = `
                <div class="processing-card">
                    <div class="loading-spinner"></div>
                    <h3 style="margin-top: 15px;">Translating...</h3>
                    <p>Please wait while we process your file.</p>
                </div>
            `;
        }
        
        function renderSuccess(result) {
            uploadArea.innerHTML = `
                <div class="success-card">
                    <i class="fas fa-check-circle fa-3x" style="color: #28a745; margin-bottom: 15px;"></i>
                    <h3>Translation Complete!</h3>
                    <p>File is ready to be saved.</p>
                    <div class="upload-actions" style="margin-top: 20px; display: flex; justify-content: center;">
                        <button id="btn-new-file" class="action-btn secondary">
                            <i class="fas fa-plus"></i> Upload Another
                        </button>
                    </div>
                </div>
            `;
            
            document.getElementById('btn-new-file').addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation(); // CRITICAL: Stop propagation to prevent uploadArea.onclick
                currentFile = null;
                translatedFileResult = null;
                if (saveBtn) saveBtn.disabled = true;
                resetUploadArea();
            });
        }

        function renderError(title, msg) {
            uploadArea.innerHTML = `
                <div class="error-card">
                    <i class="fas fa-exclamation-circle fa-3x" style="color: #dc3545; margin-bottom: 10px;"></i>
                    <h3>${title}</h3>
                    <p>${msg}</p>
                    <div class="upload-actions" style="margin-top: 20px; display: flex; justify-content: center;">
                        <button id="btn-retry" class="action-btn secondary">Try Again</button>
                    </div>
                </div>
            `;
            document.getElementById('btn-retry').addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                resetUploadArea();
            });
        }

        function resetUploadArea() {
            uploadArea.innerHTML = `
                <div class="upload-placeholder">
                    <i class="fas fa-file-word fa-3x"></i>
                    <p>Drag & Drop files here or click to upload</p>
                    <span class="file-types">Supports DOCX, TXT</span>
                </div>
            `;
        }
    }

    function initializeFileModule() {
        if (fileModuleInitialized) return; // STRICT GUARD
        console.log('Initializing file module...');
        setupFileUpload();
        fileModuleInitialized = true;
    }
"""