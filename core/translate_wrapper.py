# core/translate_wrapper.py
from core.translate_core import TranslationService

service = TranslationService()

def translate_fn(text, source_lang, target_lang):
    # map codes if needed, e.g., 'eng'->'English' or 'auto' -> 'auto'
    # call service.translate synchronously
    return service.translate(text, target_lang=target_lang, source_lang=source_lang)
