# translate_core.py
# Core translation service using DeepSeek API with environment variables

import os
import time
import logging  # Missing import added
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TranslationService")

# Load environment variables from .env file
load_dotenv()

class TranslationService:
    """
    A streamlined translation service using DeepSeek API.
    Handles text translation between languages using environment variables for configuration.
    """
    
    def __init__(self):
        """
        Initialize the translation service using API key from environment variables.
        """
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in environment variables")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com")
        )
        self.default_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        
    def translate(
        self,
        text: str,
        target_lang: str = "English",
        source_lang: str = "auto",
        model: Optional[str] = None,
        formal: bool = True
    ) -> str:
        """
        Translate text to the target language using DeepSeek API.
        
        Args:
            text: Text to translate
            target_lang: Target language (e.g., "Spanish", "French")
            source_lang: Source language or "auto" for auto-detection
            model: Optional model override
            formal: Whether to use formal language (default True)
            
        Returns:
            Translated text as a string
            
        Raises:
            TranslationError: If translation fails
        """
        if not text.strip():
            raise ValueError("Text to translate cannot be empty")
            
        tone = "formal" if formal else "informal"
        prompt = (
            f"Translate the following text from {source_lang} to {target_lang} "
            f"in a {tone} tone. Maintain the original meaning and context. "
            f"Only return the translated text without additional commentary:\n\n"
            f"{text}"
        )
        
        logger.debug("Initiating translation request")
        logger.debug(f"Source: {source_lang}, Target: {target_lang}")
        logger.debug(f"Text length: {len(text)} characters")
        
        start_time = time.perf_counter()
        
        try:
            response = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            elapsed = time.perf_counter() - start_time
            logger.info(f"Translation completed in {elapsed:.3f} seconds")
            
            translated_text = response.choices[0].message.content.strip()
            if not translated_text:
                raise TranslationError("Received empty translation response")
                
            return translated_text
            
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.error(f"Translation failed after {elapsed:.3f} seconds: {str(e)}")
            raise TranslationError(f"Translation failed: {str(e)}") from e


class TranslationError(Exception):
    """Custom exception for translation failures"""
    pass


# Example usage
if __name__ == "__main__":
    try:
        translator = TranslationService()
        result = translator.translate(
            text="The sun rose slowly over the horizon, casting a golden glow across the dew-kissed grass, while birds chirped melodiously in the distance, their songs blending with the gentle rustle of leaves swaying in the morning breeze, and as the world awoke from its slumber, a lone jogger padded softly along the winding path, breathing in the crisp, fresh air, while nearby, a small café began to stir, the rich aroma of freshly brewed coffee mingling with the scent of warm pastries, enticing early risers to pause and savor the quiet beauty of the new day, where every moment seemed to hold the promise of endless possibilities, and the ordinary felt just a little bit magical.",
            target_lang="Malay"
        )
        print(f"Translation: {result}")
    except TranslationError as e:
        print(f"Translation Error: {e}")
    except Exception as e:
        print(f"Unexpected Error: {e}")
