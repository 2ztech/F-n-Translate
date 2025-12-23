from unstructured.partition.auto import partition
from unstructured.partition.pdf import partition_pdf
from typing import Optional, List, Dict, Union
import pytesseract
from PIL import Image
import io
import fitz  # PyMuPDF
import os

class FileParser:
    def __init__(self):
        self.supported_formats = [".pdf", ".docx", ".txt"]

    def extract_text(self, file_path: str) -> Dict[str, Union[str, bool]]:
        """Extract text from a file with layout preservation.
        Returns:
            {
                "text": "Extracted text",
                "is_ocr": False,  # Was OCR used?
                "format_preserved": True  # Did we keep paragraphs/indents?
            }
        """
        if not os.path.exists(file_path):
            raise ValueError("File not found.")
        
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {ext}")

        try:
            # Try Unstructured partition_pdf for better layout/element separation
            # If we're strictly doing text-to-text translation, partition() is fine.
            elements = partition(file_path)
            
            # Combine elements with doubled newlines to preserve paragraph-like separation
            text_parts = []
            for e in elements:
                t = str(e).strip()
                if t:
                    text_parts.append(t)
            
            text = "\n\n".join(text_parts)
            
            if not text.strip():
                logger.warning("Extracted text is empty, falling back to OCR")
                raise ValueError("Empty text")

            return {
                "text": text,
                "is_ocr": False,
                "format_preserved": True
            }
        
        except Exception as e:
            logger.info(f"Standard parsing failed or returned empty: {e}. Attempting OCR fallback for {ext}.")
            # Fallback to OCR for PDFs
            if ext == ".pdf":
                text = self._extract_with_ocr(file_path)
                return {
                    "text": text,
                    "is_ocr": True,
                    "format_preserved": False
                }
            raise RuntimeError(f"Parsing failed for {ext}: {e}")

    def _extract_with_ocr(self, pdf_path: str) -> str:
        """OCR fallback for scanned PDFs using PyMuPDF + Tesseract."""
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes()))
            text += pytesseract.image_to_string(img) + "\n\n"
        return text.strip()
