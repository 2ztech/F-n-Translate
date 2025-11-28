# component/text_dedupe.py
from rapidfuzz import fuzz
import time
import hashlib

class DedupeEngine:
    def __init__(self, similarity_threshold=85, hold_seconds=3.0):
        """
        similarity_threshold: percent similarity above which we skip re-translation
        hold_seconds: minimum seconds to keep same translation visible before replacing
        """
        self.similarity_threshold = similarity_threshold
        self.hold_seconds = hold_seconds
        self.last_text = ""
        self.last_time = 0.0
        self.last_hash = None

    def should_translate(self, new_text: str) -> bool:
        """
        Return True if this new_text should be considered new enough to translate.
        """
        if not new_text.strip():
            return False

        now = time.time()
        if self.last_text == "":
            return True

        # quick hash exact test
        h = hashlib.sha1(new_text.encode('utf-8')).hexdigest()
        if h == self.last_hash:
            # exact same text; reset last_time to extend display
            self.last_time = now
            return False

        # approximate similarity
        score = fuzz.ratio(new_text, self.last_text)
        if score >= self.similarity_threshold and (now - self.last_time) < self.hold_seconds:
            # too similar and within hold window => skip
            return False

        # else update baseline
        self.last_text = new_text
        self.last_hash = h
        self.last_time = now
        return True
