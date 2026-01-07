# src/core/dbmanager.py
import sqlite3
import hashlib
import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Union
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DBManager:
    """
    Centralized database manager for caching translations and settings.
    Implements Hash-based caching for Files and Text-based caching for Live OCR.
    """
    
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DBManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, db_path: str = "FnTranslate_database.db"):
        if not hasattr(self, 'initialized'):
            self.db_path = Path(db_path)
            self._ensure_db_directory()
            self._init_tables()
            self.initialized = True

    def _ensure_db_directory(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _get_connection(self):
        """Yields a database connection with thread safety."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_tables(self) -> None:
        """Initialize the optimized schema."""
        queries = [
            # 1. TEXT CACHE (For Live Screen Translation)
            # Uses a hash of the text for faster indexing than raw text blocks
            """
            CREATE TABLE IF NOT EXISTS text_cache (
                text_hash TEXT PRIMARY KEY,
                source_text TEXT,
                source_lang TEXT,
                target_lang TEXT,
                translated_text TEXT,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # 2. FILE CACHE (For Document Translation)
            # Stores file hash so re-uploading the same file skips processing
            """
            CREATE TABLE IF NOT EXISTS file_cache (
                file_hash TEXT,
                source_lang TEXT,
                target_lang TEXT,
                original_filename TEXT,
                translated_file_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (file_hash, target_lang)
            )
            """,
            # 3. SETTINGS (For API Keys, etc)
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                description TEXT
            )
            """
        ]
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for query in queries:
                cursor.execute(query)
            conn.commit()

    # =========================================================
    #  FILE TRANSLATION LOGIC (Hash Based)
    # =========================================================

    def compute_file_hash(self, file_path: str) -> str:
        """Helper: Generates SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                # Read in chunks to handle large files
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Failed to hash file {file_path}: {e}")
            return ""

    def get_cached_file(self, file_path: str, target_lang: str) -> Optional[str]:
        """
        Check if this file has already been translated.
        Returns the path to the PREVIOUSLY translated file if it exists.
        """
        if not os.path.exists(file_path):
            return None

        file_hash = self.compute_file_hash(file_path)
        
        query = """
            SELECT translated_file_path FROM file_cache 
            WHERE file_hash = ? AND target_lang = ?
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (file_hash, target_lang))
            row = cursor.fetchone()
            
            if row:
                cached_path = row['translated_file_path']
                # CRITICAL: Check if the cached file actually still exists on disk
                if os.path.exists(cached_path):
                    logger.info(f"Cache HIT for file: {os.path.basename(file_path)}")
                    return cached_path
                else:
                    # If file is missing from disk, remove db record
                    logger.warning("Cached file missing from disk. Removing record.")
                    self.remove_file_cache(file_hash, target_lang)
            
            return None

    def cache_file_translation(self, original_path: str, translated_path: str, src_lang: str, target_lang: str):
        """Save a completed file translation to the cache."""
        file_hash = self.compute_file_hash(original_path)
        filename = os.path.basename(original_path)
        
        query = """
            INSERT OR REPLACE INTO file_cache 
            (file_hash, source_lang, target_lang, original_filename, translated_file_path)
            VALUES (?, ?, ?, ?, ?)
        """
        
        try:
            with self._get_connection() as conn:
                conn.execute(query, (file_hash, src_lang, target_lang, filename, translated_path))
                conn.commit()
            logger.info(f"File cached successfully: {filename}")
        except Exception as e:
            logger.error(f"Failed to cache file: {e}")

    def remove_file_cache(self, file_hash: str, target_lang: str):
        """Remove a stale cache record."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM file_cache WHERE file_hash = ? AND target_lang = ?", (file_hash, target_lang))
            conn.commit()

    # =========================================================
    #  SCREEN/TEXT TRANSLATION LOGIC (Text Hash Based)
    # =========================================================

    def _normalize_text(self, text: str) -> str:
        """Strip whitespace and lowercase to increase cache hit rate."""
        return text.strip().lower()

    def get_cached_text(self, text: str, src_lang: str, tgt_lang: str) -> Optional[str]:
        """Retrieve translated text if it exists."""
        if not text: return None
        
        # We hash the normalized text + languages to create a unique ID
        norm_text = self._normalize_text(text)
        unique_string = f"{norm_text}|{src_lang}|{tgt_lang}"
        text_hash = hashlib.md5(unique_string.encode()).hexdigest()

        query = "SELECT translated_text FROM text_cache WHERE text_hash = ?"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (text_hash,))
            row = cursor.fetchone()
            
            if row:
                # Update timestamp to keep this cache "fresh"
                conn.execute("UPDATE text_cache SET last_used = CURRENT_TIMESTAMP WHERE text_hash = ?", (text_hash,))
                conn.commit()
                return row['translated_text']
        
        return None

    def cache_text_translation(self, text: str, src_lang: str, tgt_lang: str, translated_text: str):
        """Store a text translation."""
        if not text or not translated_text: return

        norm_text = self._normalize_text(text)
        unique_string = f"{norm_text}|{src_lang}|{tgt_lang}"
        text_hash = hashlib.md5(unique_string.encode()).hexdigest()

        query = """
            INSERT OR REPLACE INTO text_cache 
            (text_hash, source_text, source_lang, target_lang, translated_text)
            VALUES (?, ?, ?, ?, ?)
        """
        
        try:
            with self._get_connection() as conn:
                conn.execute(query, (text_hash, text.strip(), src_lang, tgt_lang, translated_text))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to cache text: {e}")

    # =========================================================
    #  SETTINGS (API Keys)
    # =========================================================

    def get_setting(self, key: str) -> Optional[str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else None

    def set_setting(self, key: str, value: str, description: str = ""):
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value, description) VALUES (?, ?, ?)",
                (key, value, description)
            )
            conn.commit()

# Helper function to get singleton
def get_db_manager(db_path: str = "FnTranslate_database.db") -> DBManager:
    return DBManager(db_path)