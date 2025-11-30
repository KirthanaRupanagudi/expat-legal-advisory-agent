import os
from cryptography.fernet import Fernet
class SessionMemory:
    def __init__(self):
        key = os.getenv('SESSION_SECRET')
        self._key = key.encode() if key else Fernet.generate_key()
        self._fernet = Fernet(self._key)
        self._store = {}
    def store(self, k, v):
        self._store[k] = self._fernet.encrypt(str(v).encode())
    def retrieve(self, k):
        return self._fernet.decrypt(self._store[k]).decode() if k in self._store else None
