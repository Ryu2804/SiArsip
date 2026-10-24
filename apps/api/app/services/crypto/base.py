from abc import ABC, abstractmethod

class BaseCipher(ABC):
    cipher_id: int
    name: str

    @abstractmethod
    def encrypt(self, plaintext: bytes, key: bytes, aad: bytes = b"", mac_key: bytes | None = None) -> bytes:
            """Mengembalikan blob kontainer SIA1 lengkap."""
            pass

    @abstractmethod
    def decrypt(self, blob: bytes, key: bytes, aad: bytes = b"", mac_key: bytes | None = None) -> bytes:
        """Memverifikasi integritas kontainer dan mengembalikan plaintext asli."""
        pass