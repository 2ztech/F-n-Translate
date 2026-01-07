# config.py
import keyring
import os
from typing import Optional

SERVICE_NAME = "FnTranslateApp"
USER_KEY = "deepseek_api_key"

class ConfigManager:
    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file

    def save_api_key(self, api_key: str) -> bool:
        """Securely save API key to OS Credential Manager"""
        try:
            keyring.set_password(SERVICE_NAME, USER_KEY, api_key)
            return True
        except Exception as e:
            print(f"Keyring error: {e}")
            return False

    def get_api_key(self) -> Optional[str]:
        """Retrieve API key from OS Credential Manager"""
        try:
            return keyring.get_password(SERVICE_NAME, USER_KEY)
        except Exception:
            return None

    def validate_api_key(self, api_key: str) -> bool:
        """Basic validation of API key format"""
        if not api_key: 
            return False
        # FIX: Allow 'sk-' (Standard) OR 'ds-' (Custom)
        # Also lowered length check slightly just in case
        return (api_key.startswith('ds-') or api_key.startswith('sk-')) and len(api_key) > 20

    def delete_api_key(self):
        """Remove the key from the vault"""
        try:
            keyring.delete_password(SERVICE_NAME, USER_KEY)
        except keyring.errors.PasswordDeleteError:
            pass