# api.py
import logging
import os
import tempfile
import base64
from text_translator import TextTranslator
from services.file_handler import FileTranslationHandler

logger = logging.getLogger("API")

class TranslationAPI:
    def __init__(self):
        self.translator = TextTranslator()
        self.file_handler = FileTranslationHandler()
        self.temp_files = {}
        logger.info("Translation API initialized")
        
        # Add cleanup on exit
        import atexit
        atexit.register(self.cleanup_temp_files)

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

    def translate_file(self, file_path: str, source_lang: str, target_lang: str) -> dict:
        """Handle file translation"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError("File not found")
            
            result = self.file_handler.process_uploaded_file(
                file_path=file_path,
                source_lang=source_lang,
                target_lang=target_lang
            )
            
            if result['status'] == 'success':
                file_id = str(len(self.temp_files))
                self.temp_files[file_id] = result['translated_file']
                result['file_id'] = file_id
            
            return result
        except Exception as e:
            logger.error(f"File translation failed: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def download_file(self, file_id: str) -> dict:
        """Handle file download requests"""
        try:
            file_path = self.temp_files.get(file_id)
            if not file_path or not os.path.exists(file_path):
                raise FileNotFoundError("File no longer available")
            
            return {
                'status': 'success',
                'file_path': file_path,
                'file_name': os.path.basename(file_path)
            }
        except Exception as e:
            logger.error(f"File download failed: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def cleanup_temp_files(self):
        """Clean up temporary files"""
        for file_path in self.temp_files.values():
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    dir_path = os.path.dirname(file_path)
                    if os.path.exists(dir_path):
                        os.rmdir(dir_path)
            except Exception as e:
                logger.warning(f"Could not delete temp file {file_path}: {str(e)}")
        self.temp_files.clear()

    def save_temp_file(self, file_data) -> str:
        """Save uploaded file to temp location and return path"""
        try:
            temp_dir = tempfile.mkdtemp()
            
            # Handle dictionary from JS
            if isinstance(file_data, dict):
                file_name = file_data.get('name', 'uploaded_file')
                file_content = file_data.get('content', '')
                
                if not file_content:
                    raise ValueError("No file content provided")
                    
                # Remove data URL prefix if present
                if isinstance(file_content, str) and ',' in file_content:
                    file_content = file_content.split(',')[1]
                    
                file_path = os.path.join(temp_dir, file_name)
                
                with open(file_path, 'wb') as f:
                    f.write(base64.b64decode(file_content))
                    
            else:
                raise ValueError(f"Unsupported file data format: {type(file_data)}")
                
            return file_path
        except Exception as e:
            logger.error(f"Failed to save temp file: {str(e)}")
            raise



    def open_file_dialog(self):
        """Open file dialog and return selected file path"""
        try:
            from tkinter import Tk
            from tkinter.filedialog import askopenfilename
            root = Tk()
            root.withdraw()  # Hide the main window
            file_path = askopenfilename()
            root.destroy()
            return file_path
        except Exception as e:
            logger.error(f"File dialog failed: {str(e)}")
            return None

    # Add these methods to the TranslationAPI class
    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"Failed to get file size: {str(e)}")
            raise

    def save_translated_file(self, file_path: str) -> dict:
        """Handle saving translated files"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError("Translated file not found")
            
            # Get the original file name to suggest a save name
            original_name = os.path.basename(file_path)
            save_name = f"translated_{original_name}"
            
            # Create save dialog
            import webview
            save_path = webview.windows[0].create_file_dialog(
                webview.SAVE_DIALOG,
                directory=os.path.expanduser("~"),
                save_filename=save_name
            )
            
            if save_path:
                import shutil
                shutil.copy2(file_path, save_path)
                return {'status': 'success', 'path': save_path}
            return {'status': 'cancelled'}
        except Exception as e:
            logger.error(f"File save failed: {str(e)}")
            return {'status': 'error', 'message': str(e)}
