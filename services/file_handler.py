import os
import tempfile
import logging
from typing import Dict, Optional, List
from pathlib import Path

# Import our own modules cleanly
from services.parser import FileParser

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
        self.translator = translation_service
        self.supported_formats = ['.docx', '.txt']
        self.CHUNK_SIZE = 3000  # Conservative char limit per chunk (adjust based on API limits)
        logger.info("File translation handler initialized")

    def process_uploaded_file(self, file_path: str, source_lang: str, target_lang: str, output_format: Optional[str] = None) -> Dict:
        """
        Complete processing pipeline with chunking support.
        """
        try:
            # Validate input
            file_path = Path(file_path)
            if not file_path.exists():
                raise ValueError("File not found")

            ext = file_path.suffix.lower()
            if ext not in self.supported_formats:
                raise ValueError(f"Unsupported file type: {ext}. Only DOCX and TXT are supported.")

            # Determine output format if not specified
            if output_format is None:
                output_format = ext.lstrip('.')

            # Step 1: Parse/Extract text
            parsed_data = self.parser.extract_text(str(file_path))
            full_text = parsed_data['text']
            
            if not full_text.strip():
                raise ValueError("No text could be extracted from the file.")

            logger.info(f"Extracted {len(full_text)} chars from {file_path}")

            # Step 2: Translate content (using Chunking)
            translated_text = self._chunk_and_translate(
                text=full_text,
                source_lang=source_lang,
                target_lang=target_lang
            )

            # Step 3: Convert to Output
            output_file = self._create_output(
                original_path=file_path,
                translated_text=translated_text,
                target_format=output_format
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

    def _chunk_and_translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Splits text into chunks, translates them, and rejoins them."""
        
        # 1. Split by paragraphs to preserve structure
        # We also look for \r\n vs \n
        text = text.replace('\r\n', '\n')
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = []
        current_length = 0

        # 2. Group paragraphs into chunks
        for para in paragraphs:
            if len(para) > self.CHUNK_SIZE:
                # If current chunk has data, save it first
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Split large paragraph into smaller sentences or parts if possible
                # For now, just add it (API might handle it or we should refine this)
                chunks.append(para)
                continue

            if current_length + len(para) + 2 > self.CHUNK_SIZE:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [para]
                current_length = len(para)
            else:
                current_chunk.append(para)
                current_length += len(para) + 2 # +2 for the \n\n
        
        # Add the final chunk
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        logger.info(f"Split document into {len(chunks)} chunks for translation.")

        # 3. Translate each chunk
        translated_chunks = []
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            
            logger.debug(f"Translating chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
            try:
                # IMPORTANT: ensure translate accepts source/target in this order
                translated_part = self.translator.translate(
                    text=chunk,
                    source_lang=source_lang,
                    target_lang=target_lang
                )
                if translated_part:
                    translated_chunks.append(translated_part)
                else:
                    logger.warning(f"Empty translation for chunk {i+1}, using original")
                    translated_chunks.append(chunk)
            except Exception as e:
                logger.error(f"Failed to translate chunk {i+1}: {e}")
                translated_chunks.append(chunk) # Fallback: keep original text

        final_text = "\n\n".join(translated_chunks)
        if not final_text.strip():
            logger.error("Final translated text is empty!")
            return text # Fallback to original text if everything failed
            
        return final_text

    def _create_output(self, original_path: Path, translated_text: str, target_format: str) -> str:
        """Creates the output file in the requested format (DOCX or TXT)."""
        output_path = str(original_path.with_name(f"{original_path.stem}_translated.{target_format}"))
        
        if target_format == 'docx':
            return self._create_simple_docx(translated_text, output_path)
        else:
            return self._save_text_file(translated_text, output_path)

    def _create_simple_docx(self, text: str, output_path: str) -> str:
        """Creates a DOCX file."""
        logger.info(f"Starting DOCX creation at {output_path} with {len(text)} characters.")
        try:
            from docx import Document
            doc = Document()
            
            # Simple paragraph split and add
            for paragraph in text.split('\n\n'):
                if paragraph.strip():
                    doc.add_paragraph(paragraph.strip())
            
            doc.save(output_path)
            logger.info(f"DOCX creation successful: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"DOCX creation failed: {e}", exc_info=True)
            return self._save_text_file(text, output_path.replace('.docx', '.txt'))

    def _save_text_file(self, text: str, output_path: str) -> str:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        return output_path

    def _get_output_path(self, original_path: Path, ext: str) -> str:
        """Generates output path in system temp directory with correct extension."""
        if not ext.startswith('.'):
            ext = f".{ext}"
        return str(
            Path(tempfile.gettempdir()) /
            f"{original_path.stem}_translated{ext}"
        )

    def cleanup(self, file_path: str):
        try:
            Path(file_path).unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Cleanup failed for {file_path}: {str(e)}")