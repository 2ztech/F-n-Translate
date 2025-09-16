import os
import tempfile
import logging
from typing import Dict, Tuple, Optional
from pathlib import Path
from langchain.schema import Document
from .parser import FileParser
from translate_core import TranslationService
from unstructured.partition.auto import partition
from unstructured.partition.pdf import partition_pdf
import fitz  # PyMuPDF
from docx import Document as DocxDocument

logger = logging.getLogger("FileHandler")

class FileTranslationHandler:
    """Handles the complete file translation workflow from upload to output"""
    
    def __init__(self):
        self.parser = FileParser()
        self.translator = TranslationService()
        self.supported_formats = ['.pdf', '.docx', '.txt']
        logger.info("File translation handler initialized")

    def process_uploaded_file(self, file_path: str, source_lang: str, target_lang: str) -> Dict:
        """
        Complete processing pipeline:
        1. Parse file with metadata
        2. Translate content
        3. Reconstruct original format
        """
        try:
            # Validate input
            if not os.path.exists(file_path):
                raise ValueError("File not found")
            
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in self.supported_formats:
                raise ValueError(f"Unsupported file type: {ext}")

            # Step 1: Parse with layout preservation
            parsed = self.parser.extract_text(file_path)
            logger.info(f"Extracted {len(parsed['text'])} chars from {file_path}")
            
            # Step 2: Translate content
            translated_text = self.translator.translate(
                text=parsed['text'],
                source_lang=source_lang,
                target_lang=target_lang
            )
            
            # Step 3: Reconstruct original format
            output_file = self._reconstruct_file(
                original_path=file_path,
                translated_text=translated_text,
                metadata=parsed
            )
            
            return {
                'status': 'success',
                'translated_file': output_file,
                'metadata': {
                    'original_format': ext,
                    'used_ocr': parsed.get('is_ocr', False),
                    'format_preserved': parsed.get('format_preserved', False),
                    'source_lang': source_lang,
                    'target_lang': target_lang
                }
            }
            
        except Exception as e:
            logger.error(f"File processing failed: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'file': os.path.basename(file_path)
            }

    def _reconstruct_file(self, original_path: str, translated_text: str, metadata: Dict) -> str:
        """Recreates the translated file in original format"""
        ext = os.path.splitext(original_path)[1].lower()
        output_path = self._get_output_path(original_path)
        
        if ext == '.pdf':
            return self._reconstruct_pdf(original_path, translated_text, output_path)
        elif ext == '.docx':
            return self._reconstruct_docx(translated_text, output_path)
        else:  # .txt
            return self._save_text_file(translated_text, output_path)

    def _reconstruct_pdf(self, original_pdf: str, translated_text: str, output_path: str) -> str:
        """Special handling for PDFs to maintain page structure"""
        try:
            # For OCR'd PDFs, just create a new text-based PDF
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text(
                point=fitz.Point(50, 50),
                text=translated_text,
                fontsize=11,
                fontname="helv"
            )
            doc.save(output_path)
            return output_path
        except Exception as e:
            logger.warning(f"PDF reconstruction failed, falling back to text: {str(e)}")
            return self._save_text_file(translated_text, output_path.replace('.pdf', '.txt'))

    def _reconstruct_docx(self, translated_text: str, output_path: str) -> str:
        """Recreates a DOCX with basic formatting"""
        doc = DocxDocument()
        for paragraph in translated_text.split('\n\n'):
            doc.add_paragraph(paragraph)
        doc.save(output_path)
        return output_path

    def _save_text_file(self, text: str, output_path: str) -> str:
        """Simple text file output"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        return output_path

    def _get_output_path(self, original_path: str) -> str:
        """Generates output path in system temp directory"""
        original_name = os.path.basename(original_path)
        name, ext = os.path.splitext(original_name)
        return os.path.join(
            tempfile.gettempdir(),
            f"{name}_translated{ext}"
        )

    def cleanup(self, file_path: str):
        """Removes temporary files"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.warning(f"Cleanup failed for {file_path}: {str(e)}")
