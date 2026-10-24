from app.services.crypto.base import BaseCipher
from app.services.crypto.aes import AesGcmCipher

_REGISTRY: dict[str, BaseCipher] = {}
_ID_REGISTRY: dict[int, BaseCipher] = {}

def register_cipher(cipher: BaseCipher) -> None:
    _REGISTRY[cipher.name.lower()] = cipher
    _ID_REGISTRY[cipher.cipher_id] = cipher

register_cipher(AesGcmCipher())

def get_cipher(identifier: str | int) -> BaseCipher:
    if isinstance(identifier, int):
        cipher = _ID_REGISTRY.get(identifier)
    else:
        cipher = _REGISTRY.get(identifier.lower())

    if not cipher:
        raise KeyError(f"Cipher '{identifier}' tidak terdaftar")
    return cipher