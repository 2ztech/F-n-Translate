# api.py
import logging
from text_translator import TextTranslator

logger = logging.getLogger("API")

class TranslationAPI:
    def __init__(self):
        self.translator = TextTranslator()
        logger.info("Translation API initialized")

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
