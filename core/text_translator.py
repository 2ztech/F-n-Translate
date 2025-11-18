# text_translator.py
import threading
import time
import logging
from typing import Callable
from core.translate_core import TranslationService

logger = logging.getLogger("TextTranslator")

class TextTranslator:
    def __init__(self):
        self.translation_service = TranslationService()
        self.timer = None
        self.last_text = ""
        self.delay = 3  # seconds
        self.active = False
        logger.info("TextTranslator initialized")

    def translate_with_delay(self, text: str, source_lang: str, target_lang: str, callback: Callable[[str], None]):
        """Start or reset the translation timer"""
        logger.debug(f"Translation requested - Text: {text[:50]}..., Source: {source_lang}, Target: {target_lang}")
        
        if self.timer:
            logger.debug("Cancelling previous timer")
            self.timer.cancel()
        
        if not text or text == self.last_text:
            logger.debug("No translation needed - empty text or unchanged")
            return

        self.last_text = text
        self.active = True
        
        def do_translation():
            if not self.active:
                return
                
            try:
                logger.info(f"Starting translation after {self.delay} second delay")
                translated = self.translation_service.translate(
                    text=text,
                    source_lang=source_lang,
                    target_lang=target_lang
                )
                logger.debug(f"Translation completed: {translated[:50]}...")
                callback(translated)
            except Exception as e:
                logger.error(f"Translation failed: {str(e)}")
                callback(f"Translation error: {str(e)}")
            finally:
                self.active = False

        logger.debug(f"Starting new timer with {self.delay} second delay")
        self.timer = threading.Timer(self.delay, do_translation)
        self.timer.start()

    def cancel(self):
        """Cancel any pending translation"""
        if self.timer:
            logger.debug("Cancelling translation timer")
            self.timer.cancel()
        self.active = False
