import hashlib
import hmac
import time
import jwt
from typing import Optional

from shared.config import Config

class AuthManager:
    def __init__(self):
        self.secret_key = Config.SECRET_KEY
        self.token_expiry = Config.AUTH_TOKEN_EXPIRY
    
    def generate_token(self, client_id: str) -> str:
        """Generate JWT token for client"""
        payload = {
            'client_id': client_id,
            'iat': time.time(),
            'exp': time.time() + self.token_expiry
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token: str) -> Optional[str]:
        """Verify JWT token and return client_id"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload.get('client_id')
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def generate_client_hash(self, client_id: str, timestamp: float) -> str:
        """Generate hash for client authentication"""
        message = f"{client_id}:{timestamp}"
        return hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def verify_client_hash(self, client_id: str, timestamp: float, hash_value: str) -> bool:
        """Verify client hash"""
        expected_hash = self.generate_client_hash(client_id, timestamp)
        return hmac.compare_digest(expected_hash, hash_value)