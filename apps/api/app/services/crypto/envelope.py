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

def derive_pin_key(pin: str, salt: bytes) -> bytes:
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

    kdf = Scrypt(salt=salt, length=32, n=2**15, r=8, p=1)
    return kdf.derive(pin.encode("utf-8"))


def wrap_key_with_pin(dek: bytes, pin: str) -> bytes:
    salt = os.urandom(16)
    pin_key = derive_pin_key(pin, salt)
    nonce = os.urandom(12)
    aesgcm = AESGCM(pin_key)
    ciphertext = aesgcm.encrypt(nonce, dek, None)
    return salt + nonce + ciphertext


def unwrap_key_with_pin(wrapped: bytes, pin: str) -> bytes:
    if len(wrapped) < 16 + 12 + 16:
        raise IntegrityError("Data wrapped key terpotong")

    salt = wrapped[:16]
    nonce = wrapped[16:28]
    ciphertext = wrapped[28:]
    pin_key = derive_pin_key(pin, salt)
    aesgcm = AESGCM(pin_key)

    try:
        return aesgcm.decrypt(nonce, ciphertext, None)
    except InvalidTag:
        from app.schemas.errors.common_error import InvalidPinError

        raise InvalidPinError("PIN salah atau data kunci telah dimanipulasi")


def rewrap_value(wrapped: bytes | None, old_key: bytes, new_key: bytes) -> bytes | None:
    if not wrapped:
        return None
    raw_secret = unwrap_key(wrapped, master_key=old_key)
    return wrap_key(raw_secret, master_key=new_key)