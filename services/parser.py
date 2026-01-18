from typing import Dict, Union
import os
import logging
from docx import Document

logger = logging.getLogger("FileParser")

class FileParser:
    def __init__(self):
        self.supported_formats = [".docx", ".txt"]

    def extract_text(self, file_path: str) -> Dict[str, Union[str, bool]]:
        """Extract text from a file.
        Returns:
            {
                "text": "Extracted text",
                "is_ocr": False,
                "format_preserved": True 
            }
        """
        if not os.path.exists(file_path):
            raise ValueError("File not found.")
        
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {ext}")

        try:
            if ext == ".docx":
                text = self._extract_docx(file_path)
            elif ext == ".txt":
                text = self._extract_txt(file_path)
            else:
                 raise ValueError("Unsupported format")

            if not text.strip():
                raise ValueError("Extracted text is empty")
            
            return {
                "text": text,
                "is_ocr": False,
                "format_preserved": True
            }

        except Exception as e:
            logger.error(f"Parsing failed for {ext}: {e}")
            raise RuntimeError(f"Parsing failed: {e}")

    def _extract_docx(self, path: str) -> str:
        """Extract text from DOCX file using python-docx."""
        doc = Document(path)
        # Use paragraphs to preserve basic structure with double newlines
        return "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])

    def _extract_txt(self, path: str) -> str:
        """Extract text from TXT file."""
        # Try UTF-8 first, fallback to latin-1
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            with open(path, 'r', encoding='latin-1') as f:
                return f.read()
