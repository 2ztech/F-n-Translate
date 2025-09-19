# src/core/database/dbmanager.py
"""
Centralized database management module.
Handles all CRUD operations and database connections for the application.
"""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import logging
from contextlib import contextmanager
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class DBManager:
    """Centralized database manager for handling all database operations."""
    
    def __init__(self, db_path: Union[str, Path] = "app_database.db"):
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self._ensure_db_directory()
        self._init_tables()
    
    def _ensure_db_directory(self) -> None:
        """Ensure the database directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _init_tables(self) -> None:
        """Initialize database tables if they don't exist."""
        tables = [
            """
            CREATE TABLE IF NOT EXISTS translation_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_text TEXT NOT NULL,
                source_lang TEXT NOT NULL,
                target_lang TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_text, source_lang, target_lang)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS document_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_hash TEXT NOT NULL UNIQUE,
                document_path TEXT NOT NULL,
                embeddings_json TEXT NOT NULL,
                chunk_count INTEGER NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT NOT NULL UNIQUE,
                setting_value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS translation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_text TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                source_lang TEXT NOT NULL,
                target_lang TEXT NOT NULL,
                character_count INTEGER NOT NULL,
                translated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for table_sql in tables:
                cursor.execute(table_sql)
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with automatic cleanup."""
        conn = sqlite3.connect(
            str(self.db_path),
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        try:
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    # CRUD Operations for Translation Cache
    def get_cached_translation(self, source_text: str, source_lang: str, 
                              target_lang: str) -> Optional[str]:
        """
        Retrieve a cached translation.
        
        Returns:
            The cached translation text or None if not found
        """
        query = """
            SELECT translated_text FROM translation_cache 
            WHERE source_text = ? AND source_lang = ? AND target_lang = ?
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (source_text, source_lang, target_lang))
            result = cursor.fetchone()
            return result['translated_text'] if result else None
    
    def cache_translation(self, source_text: str, source_lang: str, 
                         target_lang: str, translated_text: str) -> bool:
        """
        Cache a translation result.
        
        Returns:
            True if successful, False otherwise
        """
        query = """
            INSERT OR REPLACE INTO translation_cache 
            (source_text, source_lang, target_lang, translated_text)
            VALUES (?, ?, ?, ?)
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (source_text, source_lang, target_lang, translated_text))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Failed to cache translation: {e}")
            return False
    
    def clear_translation_cache(self, older_than_days: Optional[int] = None) -> int:
        """
        Clear translation cache.
        
        Args:
            older_than_days: If provided, only clear entries older than X days
            
        Returns:
            Number of rows deleted
        """
        if older_than_days:
            query = "DELETE FROM translation_cache WHERE created_at < datetime('now', ?)"
            params = (f'-{older_than_days} days',)
        else:
            query = "DELETE FROM translation_cache"
            params = ()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
    
    # CRUD Operations for Document Embeddings
    def save_document_embeddings(self, document_hash: str, document_path: str,
                               embeddings: List[List[float]], chunk_count: int) -> bool:
        """
        Save document embeddings to the database.
        
        Returns:
            True if successful, False otherwise
        """
        query = """
            INSERT OR REPLACE INTO document_embeddings 
            (document_hash, document_path, embeddings_json, chunk_count)
            VALUES (?, ?, ?, ?)
        """
        
        try:
            embeddings_json = json.dumps(embeddings)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (document_hash, document_path, embeddings_json, chunk_count))
                conn.commit()
                return True
        except (sqlite3.Error, TypeError) as e:
            logger.error(f"Failed to save document embeddings: {e}")
            return False
    
    def get_document_embeddings(self, document_hash: str) -> Optional[Tuple[str, List[List[float]]]]:
        """
        Retrieve document embeddings from the database.
        
        Returns:
            Tuple of (document_path, embeddings_list) or None if not found
        """
        query = "SELECT document_path, embeddings_json FROM document_embeddings WHERE document_hash = ?"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (document_hash,))
            result = cursor.fetchone()
            
            if result:
                try:
                    embeddings = json.loads(result['embeddings_json'])
                    return result['document_path'], embeddings
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse embeddings JSON: {e}")
                    return None
            return None
    
    # CRUD Operations for App Settings
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Retrieve an application setting."""
        query = "SELECT setting_value FROM app_settings WHERE setting_key = ?"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (key,))
            result = cursor.fetchone()
            return result['setting_value'] if result else default
    
    def set_setting(self, key: str, value: Any, description: str = None) -> bool:
        """Set an application setting."""
        query = """
            INSERT OR REPLACE INTO app_settings 
            (setting_key, setting_value, description)
            VALUES (?, ?, ?)
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (key, str(value), description))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Failed to set setting {key}: {e}")
            return False
    
    # History Operations
    def add_translation_history(self, source_text: str, translated_text: str,
                              source_lang: str, target_lang: str) -> bool:
        """Add an entry to the translation history."""
        query = """
            INSERT INTO translation_history 
            (source_text, translated_text, source_lang, target_lang, character_count)
            VALUES (?, ?, ?, ?, ?)
        """
        
        try:
            char_count = len(source_text) + len(translated_text)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (source_text, translated_text, source_lang, target_lang, char_count))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Failed to add translation history: {e}")
            return False
    
    def get_recent_translations(self, limit: int = 50) -> List[Dict]:
        """Get recent translation history."""
        query = """
            SELECT * FROM translation_history 
            ORDER BY translated_at DESC 
            LIMIT ?
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    # Generic Query Methods
    def execute_query(self, query: str, params: Tuple = ()) -> List[Dict]:
        """Execute a custom query and return results as dictionaries."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def execute_update(self, query: str, params: Tuple = ()) -> int:
        """Execute an update/insert/delete query and return affected rows."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount

# Singleton instance for easy access across the application
_db_instance = None

def get_db_manager(db_path: str = "app_database.db") -> DBManager:
    """Get the singleton database manager instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DBManager(db_path)
    return _db_instance
