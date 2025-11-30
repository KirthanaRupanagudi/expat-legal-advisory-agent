import os
from cryptography.fernet import Fernet

class SessionMemory:
    def __init__(self):
        key = os.getenv('SESSION_SECRET')
        self._key = key.encode() if key else Fernet.generate_key()
        self._fernet = Fernet(self._key)
        self._store = {}
    
    def store(self, k, v):
        """Store encrypted value."""
        try:
            self._store[k] = self._fernet.encrypt(str(v).encode())
        except Exception as e:
            print(f"⚠️  Warning: Failed to store session data for key '{k}': {e}")
    
    def retrieve(self, k):
        """Retrieve and decrypt value."""
        if k not in self._store:
            return None
        try:
            return self._fernet.decrypt(self._store[k]).decode()
        except Exception as e:
            print(f"⚠️  Warning: Failed to retrieve session data for key '{k}': {e}")
            return None
