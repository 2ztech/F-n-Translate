import os
import json
from cryptography.fernet import Fernet
from typing import Optional

class ConfigManager:
    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file
        self.key_file = 'secret.key'
        self._ensure_key_exists()
        self.cipher = Fernet(self._load_key())

    def _ensure_key_exists(self):
        if not os.path.exists(self.key_file):
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)

    def _load_key(self) -> bytes:
        with open(self.key_file, 'rb') as f:
            return f.read()

    def save_api_key(self, api_key: str):
        """Encrypt and save the API key to config file"""
        encrypted_key = self.cipher.encrypt(api_key.encode())
        config = {'api_key': encrypted_key.decode()}
        with open(self.config_file, 'w') as f:
            json.dump(config, f)

    def get_api_key(self) -> Optional[str]:
        """Retrieve and decrypt the API key"""
        if not os.path.exists(self.config_file):
            return None
            
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            encrypted_key = config['api_key'].encode()
            return self.cipher.decrypt(encrypted_key).decode()
        except (json.JSONDecodeError, KeyError):
            return None

    def validate_api_key(self, api_key: str) -> bool:
        """Basic validation of API key format"""
        return api_key.startswith('ds-') and len(api_key) > 20
