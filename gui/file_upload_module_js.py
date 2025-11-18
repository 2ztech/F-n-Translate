# file_upload_module_js.py

def file_upload_module_js():
    return """
    // File Upload Module JS

    function setupFileUpload() {
        const uploadArea = document.getElementById('upload-area');
        if (!uploadArea) {
            console.error('Upload area not found');
            return;
        }

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

    function initializeFileModule() {
        console.log('Initializing file module...');
        setupFileUpload();
    }
"""
