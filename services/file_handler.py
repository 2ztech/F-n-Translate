import os
import tempfile
import logging
from typing import Dict, Optional
from pathlib import Path

# Import our own modules cleanly
from .parser import FileParser

logger = logging.getLogger(__name__)

class FileTranslationHandler:
    """Handles the complete file translation workflow from upload to output."""

    def __init__(self, translation_service, parser: Optional[FileParser] = None):
        """
        Args:
            translation_service: An object with a .translate(text, src_lang, tgt_lang) method.
            parser: Optional, for dependency injection and testing.
        """
        self.parser = parser or FileParser()
        self.translator = translation_service  # Injected dependency
        self.supported_formats = ['.pdf', '.docx', '.txt']
        logger.info("File translation handler initialized")

    def process_uploaded_file(self, file_path: str, source_lang: str, target_lang: str) -> Dict:
        """Complete processing pipeline."""
        try:
            # Validate input
            file_path = Path(file_path)
            if not file_path.exists():
                raise ValueError("File not found")

            ext = file_path.suffix.lower()
            if ext not in self.supported_formats:
                raise ValueError(f"Unsupported file type: {ext}")

            # Step 1: Parse with layout preservation
            parsed_data = self.parser.extract_text(str(file_path))
            logger.info(f"Extracted {len(parsed_data['text'])} chars from {file_path}")

            # Step 2: Translate content
            translated_text = self.translator.translate(
                text=parsed_data['text'],
                source_lang=source_lang,
                target_lang=target_lang
            )

            # Step 3: Create output in a simple format
            output_file = self._create_simple_output(
                original_path=file_path,
                translated_text=translated_text,
                metadata=parsed_data
            )

            return {
                'status': 'success',
                'original_file': str(file_path),
                'translated_file': output_file,
                'metadata': {
                    'original_format': ext,
                    'output_format': Path(output_file).suffix,
                    'used_ocr': parsed_data.get('is_ocr', False),
                    'source_lang': source_lang,
                    'target_lang': target_lang
                }
            }

        except Exception as e:
            logger.error(f"File processing failed for {file_path}: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e),
                'file': os.path.basename(file_path)
            }

    def _create_simple_output(self, original_path: Path, translated_text: str, metadata: Dict) -> str:
        """Creates a simple output file. Does NOT fully reconstruct original format."""
        ext = original_path.suffix.lower()
        output_path = self._get_output_path(original_path)

        if ext == '.pdf':
            # Creates a new simple text-based PDF
            return self._create_simple_pdf(translated_text, output_path)
        elif ext == '.docx':
            # Creates a new simple DOCX with basic paragraphs
            return self._create_simple_docx(translated_text, output_path)
        else:  # .txt
            return self._save_text_file(translated_text, output_path)

    def _create_simple_pdf(self, text: str, output_path: str) -> str:
        """Creates a new simple PDF with the translated text."""
        try:
            import fitz  # Import here to make it optional
            doc = fitz.open()
            page = doc.new_page()
            # Simple text insertion
            page.insert_text(
                point=fitz.Point(50, 50),
                text=text,
                fontsize=11,
                fontname="helv"
            )
            doc.save(output_path)
            return output_path
        except ImportError:
            logger.warning("PyMuPDF not available, falling back to text file.")
        except Exception as e:
            logger.warning(f"Simple PDF creation failed: {e}, falling back to text file.")
        # Fallback to text
        return self._save_text_file(text, output_path.replace('.pdf', '.txt'))

    def _create_simple_docx(self, text: str, output_path: str) -> str:
        """Creates a new simple DOCX with the translated text."""
        try:
            from docx import Document
            doc = Document()
            for paragraph in text.split('\n\n'):
                doc.add_paragraph(paragraph)
            doc.save(output_path)
            return output_path
        except ImportError:
            logger.warning("python-docx not available, falling back to text file.")
        except Exception as e:
            logger.warning(f"Simple DOCX creation failed: {e}, falling back to text file.")
        # Fallback to text
        return self._save_text_file(text, output_path.replace('.docx', '.txt'))

    def _save_text_file(self, text: str, output_path: str) -> str:
        """Simple text file output. The most reliable method."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        return output_path

    def _get_output_path(self, original_path: Path) -> str:
        """Generates output path in system temp directory."""
        return str(
            Path(tempfile.gettempdir()) /
            f"{original_path.stem}_translated{original_path.suffix}"
        )

    def cleanup(self, file_path: str):
        """Removes temporary files."""
        try:
            Path(file_path).unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Cleanup failed for {file_path}: {str(e)}")
