import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from app.core.config import get_master_key
from app.services.crypto.exceptions import IntegrityError

def wrap_key(dek: bytes, master_key: bytes | None = None) -> bytes:
    mk = master_key or get_master_key()
    nonce = os.urandom(12)
    aesgcm = AESGCM(mk)
    ciphertext = aesgcm.encrypt(nonce, dek, None)
    return nonce + ciphertext

def unwrap_key(wrapped: bytes, master_key: bytes | None = None) -> bytes:
    mk = master_key or get_master_key()
    if len(wrapped) < 28:
        raise IntegrityError("Data wrapped key terpotong")

    nonce = wrapped[:12]
    ciphertext = wrapped[12:]
    aesgcm = AESGCM(mk)

    try:
        return aesgcm.decrypt(nonce, ciphertext, None)
    except InvalidTag:
        raise IntegrityError("Gagal membuka kunci: master key salah atau data kunci telah dimanipulasi")

def rewrap_value(wrapped: bytes | None, old_key: bytes, new_key: bytes) -> bytes | None:
    if not wrapped:
        return None
    raw_secret = unwrap_key(wrapped, master_key=old_key)
    return wrap_key(raw_secret, master_key=new_key)