# api_handler.py
import os
import requests
from dotenv import load_dotenv
from typing import Dict, Optional

load_dotenv()

class DeepSeekAPI:
    BASE_URL = "https://api.deepseek.com/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('DEEPSEEK_API_KEY')
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })

    def is_authenticated(self) -> bool:
        """Check if API key is valid"""
        return self.api_key is not None

    def translate_text(self, text: str, source_lang: str, target_lang: str) -> Dict:
        """
        Translate text using DeepSeek API
        Returns dictionary with translation or error
        """
        if not self.is_authenticated():
            return {'error': 'API key not configured'}
        
        try:
            payload = {
                'text': text,
                'source_language': source_lang,
                'target_language': target_lang
            }
            
            response = self.session.post(
                f"{self.BASE_URL}/translate",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'translation': data.get('translated_text'),
                    'source_lang': source_lang,
                    'target_lang': target_lang
                }
            else:
                return {
                    'error': f"API request failed with status {response.status_code}",
                    'details': response.text
                }
                
        except requests.exceptions.RequestException as e:
            return {'error': f"API request failed: {str(e)}"}
