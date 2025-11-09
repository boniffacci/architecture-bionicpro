from cryptography.fernet import Fernet


class EncryptionService:
    def __init__(self):
        # TODO: убрать в .env
        self.key = b"W2Ds6CHxMi9U3XpMl0zHXXUCAkwtXhCpe8fCv-aynzM="

    def encrypt(self, payload: str) -> str:
        f = Fernet(self.key)
        return f.encrypt(payload.encode()).decode()

    def decrypt(self, encrypted_payload: str) -> str:
        f = Fernet(self.key)
        return f.decrypt(encrypted_payload.encode()).decode()
