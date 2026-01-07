# api.py
import logging
import os
import tempfile
import base64
import shutil  # Added missing import
from config import ConfigManager
from core.text_translator import TextTranslator
from services.file_handler import FileTranslationHandler

logger = logging.getLogger("API")

class TranslationAPI:
    def __init__(self):
        self.translator = TextTranslator()
        self.config_manager = ConfigManager()
        # FIX 1: Pass the actual service object, not the wrapper method
        # self.translator.translation_service has the .translate() method needed
        self.file_handler = FileTranslationHandler(self.translator.translation_service)
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
            
            # Using the improved handler with chunking
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
        """Clean up temporary files and their parent directories if they are empty"""
        temp_root = tempfile.gettempdir().lower()
        for file_path in self.temp_files.values():
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    dir_path = os.path.normpath(os.path.dirname(file_path))
                    # Only try to remove if it's a subdirectory of temp_root, not the temp_root itself
                    if os.path.exists(dir_path) and dir_path.lower() != temp_root:
                        try:
                            # Use listdir to check if empty just to be safe before trying to rmdir
                            if not os.listdir(dir_path):
                                os.rmdir(dir_path)
                        except (OSError, PermissionError):
                            pass # Skip if not empty or no permission
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
            
            # Create save dialog
            import webview
            save_path = webview.windows[0].create_file_dialog(
                webview.SAVE_DIALOG,
                directory=os.path.expanduser("~"),
                save_filename=original_name
            )
            
            # FIX 2: Handle tuple return type from create_file_dialog
            if save_path:
                if isinstance(save_path, (tuple, list)):
                    save_path = save_path[0]
                
                shutil.copy2(file_path, save_path)
                return {'status': 'success', 'path': save_path}
            
            return {'status': 'cancelled'}
        except Exception as e:
            logger.error(f"File save failed: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def check_api_key(self, api_key: str) -> bool:
        """Check if the provided API key is valid"""
        try:
            from core.translate_core import TranslationService
            # Validate format first
            if not self.config_manager.validate_api_key(api_key):
                return False

            old_key = os.environ.get("DEEPSEEK_API_KEY")
            os.environ["DEEPSEEK_API_KEY"] = api_key
            
            service = TranslationService()
            result = service.translate("test", "eng", "msa")
            
            if old_key:
                os.environ["DEEPSEEK_API_KEY"] = old_key
            else:
                del os.environ["DEEPSEEK_API_KEY"]
                
            return True if result else False
        except Exception as e:
            logger.error(f"API Key check failed: {e}")
            return False

    def save_api_key(self, api_key: str) -> bool:
        """Save the API key to persistent storage (Keyring)"""
        try:
            # Save to Keyring via ConfigManager
            if self.config_manager.save_api_key(api_key):
                # Also update current session env var so it works immediately
                os.environ["DEEPSEEK_API_KEY"] = api_key
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to save API key: {e}")
            return False