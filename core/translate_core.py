# core/translate_core.py
import os
import time
import logging
from typing import Optional
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO, # Changed to INFO as requested
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TranslationService")

class TranslationService:
    def __init__(self):
        """
        Initialize the translation service.
        Safe Mode: Does NOT raise error if key is missing during init.
        """
        self.default_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Try to initialize the OpenAI client if key exists."""
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key:
            self.client = OpenAI(
                api_key=api_key,
                base_url=os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com")
            )
            logger.info("DeepSeek Client initialized successfully.")
        else:
            logger.warning("DeepSeek API Key not found. Service in PASSIVE mode.")

    def translate(
        self,
        text: str,
        target_lang: str = "English",
        source_lang: str = "auto",
        model: Optional[str] = None,
        formal: bool = True
    ) -> str:
        """
        Translate text. Raises error ONLY if key is missing at this specific moment.
        """
        # Lazy load: Check if key was added since init
        if not self.client:
            self._initialize_client()
            if not self.client:
                raise TranslationError("API Key is missing. Please set it in Settings.")

        if not text.strip():
            raise ValueError("Text to translate cannot be empty")
            
        tone = "formal" if formal else "informal"
        prompt = (
            f"Translate the following text from {source_lang} to {target_lang} "
            f"in a {tone} tone. Maintain the original meaning and context. "
            f"Only return the translated text without additional commentary:\n\n"
            f"{text}"
        )
        
        start_time = time.perf_counter()
        
        try:
            response = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=1.3
            )
            
            elapsed = time.perf_counter() - start_time
            logger.info(f"Translation completed in {elapsed:.3f} seconds")
            
            translated_text = response.choices[0].message.content.strip()
            if not translated_text:
                raise TranslationError("Received empty translation response")
                
            return translated_text
            
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            raise TranslationError(f"Translation failed: {str(e)}") from e

class TranslationError(Exception):
    pass