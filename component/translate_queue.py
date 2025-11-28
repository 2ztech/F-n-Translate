# component/translate_queue.py
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from cachetools import LRUCache
from core.dbmanager import get_db_manager
import time

class TranslateQueue:
    def __init__(self, translation_fn, max_workers=2, lru_size=512):
        """
        translation_fn: callable(text, source_lang, target_lang) -> translated_text
        """
        self.translation_fn = translation_fn
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.db = get_db_manager()
        self.cache = LRUCache(maxsize=lru_size)
        self.pending = {}  # map hash -> future
        self.lock = threading.Lock()
        # keep last seen time for items to allow timeout fallback
        self.last_update = {}

    def _hash_text(self, text: str) -> str:
        h = hashlib.sha1(text.encode('utf-8')).hexdigest()
        return h

    def get_cached_translation(self, text, source_lang, target_lang):
        key = (text, source_lang, target_lang)
        # fast LRU
        h = self._hash_text("|".join(key))
        if h in self.cache:
            return self.cache[h]
        # try DB
        cached = self.db.get_cached_translation(text, source_lang, target_lang)
        if cached:
            self.cache[h] = cached
            return cached
        return None

    def submit(self, text, source_lang, target_lang, callback):
        """
        Submit a translation job. callback(translated_text, metadata)
        - If cached: callback is called synchronously (but off main thread recommended)
        - If not: schedule translation and call callback on completion
        """
        key = (text, source_lang, target_lang)
        h = self._hash_text("|".join(key))

        # check LRU/DB cache
        cached = self.get_cached_translation(text, source_lang, target_lang)
        if cached:
            callback(cached, {"source": "cache"})
            return

        with self.lock:
            # if job already running, attach a waiter
            if h in self.pending:
                future = self.pending[h]
                # attach a done callback
                def _attach(fut):
                    try:
                        res = fut.result()
                        callback(res, {"source": "pending"})
                    except Exception as e:
                        callback(None, {"error": str(e)})
                future.add_done_callback(_attach)
                return

            # else schedule
            future = self.executor.submit(self._do_translate, text, source_lang, target_lang)
            self.pending[h] = future

            def _done(fut):
                try:
                    res = fut.result()
                    # store in db and LRU
                    self.db.cache_translation(text, source_lang, target_lang, res)
                    self.cache[h] = res
                    callback(res, {"source": "remote"})
                except Exception as e:
                    callback(None, {"error": str(e)})
                finally:
                    with self.lock:
                        if h in self.pending:
                            del self.pending[h]
            future.add_done_callback(_done)

    def _do_translate(self, text, source_lang, target_lang):
        # actual translation call (network). Let translation_fn raise on error.
        return self.translation_fn(text, source_lang, target_lang)

    def shutdown(self):
        self.executor.shutdown(wait=False)
