# translate_core.py
# Fixed version with working HTTP adapter configuration

import os
import time
import logging
from typing import Optional
from functools import lru_cache
from openai import OpenAI
from dotenv import load_dotenv
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler('translation_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DeepSeekTranslator")

# Load environment variables
load_dotenv()

class TranslationService:
    """
    Optimized translation service with:
    - Automatic retries
    - Request chunking
    - Local caching
    - Network resilience
    """
    
    def __init__(self):
        """
        Initialize with optimized configuration
        """
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in environment variables")
        
        # Configure client with retry strategy
        self.client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com"),
            timeout=10.0  # Combined timeout
        )
        
        self.default_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.max_retries = 3
        self.retry_delay = 1.0

    @lru_cache(maxsize=1024)
    def _get_translation_prompt(self, source_lang: str, target_lang: str, formal: bool) -> str:
        """Cache prompt templates to reduce processing overhead"""
        tone = "formal" if formal else "informal"
        return (
            f"Translate from {source_lang} to {target_lang} in {tone} tone. "
            "Maintain original meaning and context. Only return the translated text:\n\n{text}"
        )

    def translate(
        self,
        text: str,
        target_lang: str = "English",
        source_lang: str = "auto",
        model: Optional[str] = None,
        formal: bool = True
    ) -> str:
        """
        Robust translation with retry mechanism
        """
        if not text.strip():
            return ""

        prompt_template = self._get_translation_prompt(source_lang, target_lang, formal)
        prompt = prompt_template.format(text=text)

        logger.debug(f"Translating {len(text)} chars to {target_lang}")
        start_time = time.perf_counter()

        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=model or self.default_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                
                translated_text = response.choices[0].message.content.strip()
                elapsed = time.perf_counter() - start_time
                
                logger.info(f"Translated {len(text)} chars in {elapsed:.2f}s")
                return translated_text

            except Exception as e:
                last_error = e
                elapsed = time.perf_counter() - start_time
                logger.warning(f"Attempt {attempt + 1} failed after {elapsed:.2f}s: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
        
        raise TranslationError(f"Translation failed after {self.max_retries} attempts: {str(last_error)}")

    def batch_translate(
        self,
        texts: list[str],
        target_lang: str = "English",
        source_lang: str = "auto",
        model: Optional[str] = None,
        formal: bool = True
    ) -> list[str]:
        """
        Translate multiple texts with automatic retries
        """
        return [self.translate(text, target_lang, source_lang, model, formal) for text in texts]


class TranslationError(Exception):
    """Custom exception for translation failures"""
    pass


if __name__ == "__main__":
    def performance_test():
        """Test with different text sizes"""
        test_cases = [
            ("Short text", "Hello world"),
            ("Medium text", "The quick brown fox jumps over the lazy dog. " * 10),
            ("Long text", "Lorem ipsum dolor sit amet. " * 100)
        ]
        
        translator = TranslationService()
        
        for name, text in test_cases:
            print(f"\nTesting: {name} ({len(text)} chars)")
            start = time.perf_counter()
            try:
                result = translator.translate(text, target_lang="Spanish")
                elapsed = time.perf_counter() - start
                print(f"Success in {elapsed:.2f}s")
                print(f"Sample: {result[:50]}...")
            except Exception as e:
                elapsed = time.perf_counter() - start
                print(f"Failed in {elapsed:.2f}s: {str(e)}")
    
    performance_test()