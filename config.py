# config.py
import json
import os
from cryptography.fernet import Fernet
from typing import Optional

class ConfigManager:
    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file
        self.key_file = 'secret.key'
        self._ensure_key_exists()
        try:
            self.cipher = Fernet(self._load_key())
        except Exception as e:
            print(f"Encryption key error: {e}. Generating new key.")
            # If key is corrupted, reset it
            self._generate_new_key()
            self.cipher = Fernet(self._load_key())

    def _ensure_key_exists(self):
        """Ensure the encryption key exists."""
        if not os.path.exists(self.key_file):
            self._generate_new_key()

    def _generate_new_key(self):
        """Generate and save a new encryption key."""
        key = Fernet.generate_key()
        with open(self.key_file, 'wb') as f:
            f.write(key)

    def _load_key(self) -> bytes:
        """Load the encryption key from file."""
        with open(self.key_file, 'rb') as f:
            return f.read()

    def save_api_key(self, api_key: str) -> bool:
        """Encrypt and save the API key to config file."""
        try:
            encrypted_key = self.cipher.encrypt(api_key.encode())
            config = {'api_key': encrypted_key.decode()}
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
            return True
        except Exception as e:
            print(f"Failed to save config: {e}")
            return False

    def get_api_key(self) -> Optional[str]:
        """Retrieve and decrypt the API key."""
        if not os.path.exists(self.config_file):
            return None
            
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            if 'api_key' not in config:
                return None
                
            encrypted_key = config['api_key'].encode()
            return self.cipher.decrypt(encrypted_key).decode()
        except (json.JSONDecodeError, KeyError, Exception) as e:
            print(f"Failed to load config: {e}")
            return None

    def validate_api_key(self, api_key: str) -> bool:
        """Basic validation of API key format."""
        if not api_key: 
            return False
        # Allow 'ds-' (Your custom) OR 'sk-' (Standard DeepSeek/OpenAI)
        return (api_key.startswith('ds-') or api_key.startswith('sk-')) and len(api_key) > 20

    def delete_api_key(self):
        """Remove the config file."""
        if os.path.exists(self.config_file):
            try:
                os.remove(self.config_file)
            except Exception:
                pass