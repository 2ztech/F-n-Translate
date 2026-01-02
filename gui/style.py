CSS = """
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
        
body {
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .app-container {
            width: 100%;
            max-width: 900px;
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }
        
        .app-header {
            background: #1ba1e2;
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .logo i {
            font-size: 24px;
        }
        
        .logo h1 {
            font-size: 22px;
            font-weight: 600;
        }
        
        .nav-buttons {
            display: flex;
            gap: 5px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 30px;
            padding: 5px;
        }
        
        .nav-btn {
            background: transparent;
            border: none;
            color: white;
            padding: 8px 20px;
            border-radius: 30px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        
        .nav-btn.active {
            background: white;
            color: #1ba1e2;
            box-shadow: 0 3px 8px rgba(0, 0, 0, 0.2);
        }
        
        .nav-btn:hover:not(.active) {
            background: rgba(255, 255, 255, 0.3);
        }
        
        .language-bar {
            background: #dae8fc;
            padding: 15px 20px;
            display: flex;
            justify-content: center;
            gap: 20px;
            border-bottom: 1px solid #b8d1f0;
        }
        
        .language-selector {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .language-selector label {
            font-weight: 500;
            color: #2a5298;
        }
        
        .language-dropdown {
            position: relative;
            width: 150px;
        }
        
        .language-dropdown select {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #b8d1f0;
            border-radius: 6px;
            background: white;
            color: #2a5298;
            font-weight: 500;
            appearance: none;
            cursor: pointer;
        }
        
        .language-dropdown i {
            position: absolute;
            right: 12px;
            top: 50%;
            transform: translateY(-50%);
            color: #2a5298;
            pointer-events: none;
        }
        
        .module-content {
            padding: 30px;
        }
        
        .module {
            display: none;
            animation: fadeIn 0.4s ease;
        }
        
        .module.active {
            display: block;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Text Module */
        .text-module {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        
        .translation-box {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        
        .translation-box h3 {
            color: #2a5298;
            font-weight: 600;
            font-size: 18px;
            margin-bottom: 5px;
        }
        
        .translation-area {
            border: 1px solid #d0d0d0;
            border-radius: 8px;
            min-height: 250px;
            padding: 15px;
            background: #f9fbfd;
            resize: vertical;
            font-size: 16px;
            color: #333;
        }
        
        .translation-area:focus {
            outline: none;
            border-color: #1ba1e2;
            box-shadow: 0 0 0 2px rgba(27, 161, 226, 0.2);
        }
        
        .translation-area::placeholder {
            color: #aaa;
        }
        
        /* File Module */
        .file-container {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 25px;
            width: 100%;
        }
    
        .file-input {
            width: 100%;
            max-width: 500px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .file-module {
            display: flex;
            flex-direction: column;
        }

        .processing-card, .success-card, .error-card {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 20px;
            width: 100%;
            height: 100%;
            flex-grow: 1;
        }

        .loading-spinner {
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #1ba1e2;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .btn-small {
            padding: 8px 15px;
            font-size: 14px;
        }
        
        .upload-area {
            border: 2px dashed #b8d1f0;
            border-radius: 12px;
            width: 100%;
            min-height: 250px;
            padding: 30px;
            text-align: center;
            background: #f9fbfd;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        
        .upload-area:hover {
            border-color: #1ba1e2;
            background: #f0f7ff;
        }
        
        .upload-area i {
            font-size: 48px;
            color: #1ba1e2;
            margin-bottom: 15px;
        }
        
        .upload-area h3 {
            color: #2a5298;
            margin-bottom: 10px;
        }
        
        .upload-area p {
            color: #666;
            font-size: 14px;
        }
        
        .file-actions {
            display: flex;
            gap: 15px;
            justify-content: center;
        }
        
        .action-btn {
            padding: 10px 25px;
            border: none;
            border-radius: 6px;
            background: #1ba1e2;
            color: white;
            font-weight: 500;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.3s ease;
        }
        
        .action-btn:hover {
            background: #0d8bc9;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
        }
        
        .action-btn.save {
            background: #4CAF50;
        }
        
        .action-btn.save:hover {
            background: #3d8b40;
        }
        
        /* Capture Module */
        .capture-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .capture-module {
            display: flex;
            flex-direction: column;
            gap: 25px;
        }
        
        .monitor-selector {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .monitor-selector label {
            font-weight: 500;
            color: #2a5298;
            min-width: 120px;
        }
        
        .monitor-dropdown {
            position: relative;
            width: 200px;
        }
        
        .monitor-dropdown select {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #b8d1f0;
            border-radius: 6px;
            background: white;
            color: #2a5298;
            font-weight: 500;
            appearance: none;
            cursor: pointer;
        }
        
        .monitor-dropdown i {
            position: absolute;
            right: 12px;
            top: 50%;
            transform: translateY(-50%);
            color: #2a5298;
            pointer-events: none;
        }
        
        .capture-preview {
            border: 1px solid #d0d0d0;
            border-radius: 8px;
            height: 400px;
            background: #f0f7ff;
            position: relative;
            overflow: hidden;
        }
        
        .preview-placeholder {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            height: 100%;
            color: #666;
            gap: 15px;
        }
        
        .preview-placeholder i {
            font-size: 48px;
            color: #b8d1f0;
        }
        
        .capture-controls {
            display: flex;
            gap: 10px;
        }
        
        .capture-btn {
            padding: 8px 15px;
            border: none;
            border-radius: 6px;
            background: #1ba1e2;
            color: white;
            font-weight: 500;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.3s ease;
        }
        
        .capture-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
        }
        
        .capture-btn.stop {
            background: #e51400;
        }

        .capture-btn.secondary {
            background: #6a89cc;
        }
        
        .capture-btn.secondary:hover {
            background: #4a69bd;
        }
        
        .app-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 30px;
            background: #f5f5f5;
            border-top: 1px solid #e0e0e0;
            margin-top: 20px;
        }
        
        .settings-btn {
            background: transparent;
            border: none;
            color: #666;
            font-size: 20px;
            cursor: pointer;
            padding: 8px;
            border-radius: 50%;
            transition: all 0.3s ease;
        }
        
        .settings-btn:hover {
            background: #eaeaea;
            color: #1ba1e2;
        }
        
        .api-key-info {
            font-size: 14px;
            color: #666;
        }
        
        .api-key-info span {
            font-weight: 500;
            color: #1ba1e2;
        }
        
        /* API Settings Modal */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }
        
        .modal-content {
            background-color: #fff;
            margin: 15% auto;
            padding: 25px;
            border-radius: 10px;
            width: 400px;
            max-width: 90%;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            position: relative;
        }
        
        .close {
            position: absolute;
            right: 15px;
            top: 10px;
            font-size: 24px;
            cursor: pointer;
            color: #666;
        }
        
        .api-input {
            margin: 20px 0;
        }
        
        .api-input input {
            width: 100%;
            padding: 10px;
            border: 1px solid #b8d1f0;
            border-radius: 6px;
            margin-top: 8px;
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
            .text-module, .file-grid {
                grid-template-columns: 1fr;
                gap: 20px;
            }
            
            .language-bar {
                flex-direction: column;
                align-items: center;
                gap: 10px;
            }
            
            .capture-header {
                flex-direction: column;
                align-items: flex-start;
                gap: 15px;
            }
            
            .capture-preview {
                height: 300px;
            }
            
            .file-actions {
                flex-direction: column;
                width: 100%;
            }
            
            .action-btn {
                width: 100%;
                justify-content: center;
            }
        }
"""