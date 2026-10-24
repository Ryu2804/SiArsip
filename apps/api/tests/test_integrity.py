import hashlib
import os
import pytest
from app.services.crypto import get_cipher
from app.services.crypto.exceptions import CryptoError

CIPHER_CONFIGS = [
    ("aes", 32, None),        # AES-256-GCM
    ("des", 8, 32),           # DES-CBC + HMAC
    ("rc4", 16, 32),          # RC4 + HMAC
]

TEST_SIZES = [
    1 * 1024,                 # 1 KB (form data)
    300 * 1024,               # 300 KB (scan KTP)
    2 * 1024 * 1024,          # 2 MB (dokumen consent)
    10 * 1024 * 1024,         # 10 MB (foto rontgen)
    50 * 1024 * 1024,         # 50 MB (video MP4)
]

def _get_keys(cipher_name: str, key_len: int, mac_len: int | None):
    key = os.urandom(key_len)
    mac_key = os.urandom(mac_len) if mac_len else None
    return key, mac_key

# SIA-69: Test keutuhan 100% dengan SHA-256 hash matching
@pytest.mark.parametrize("cipher_name,key_len,mac_len", CIPHER_CONFIGS)
@pytest.mark.parametrize("size", TEST_SIZES)
def test_integrity_roundtrip_sha256(cipher_name, key_len, mac_len, size):
    cipher = get_cipher(cipher_name)
    key, mac_key = _get_keys(cipher_name, key_len, mac_len)
    aad = f"user_1:file_{size}".encode("utf-8")
    
    plaintext = os.urandom(size)
    original_sha256 = hashlib.sha256(plaintext).hexdigest()

    blob = cipher.encrypt(plaintext, key, aad=aad, mac_key=mac_key)
    decrypted = cipher.decrypt(blob, key, aad=aad, mac_key=mac_key)

    assert hashlib.sha256(decrypted).hexdigest() == original_sha256
    assert decrypted == plaintext

# SIA-70: Test bit flip di seluruh bagian kontainer (Header, IV, Ciphertext, Tag)
@pytest.mark.parametrize("cipher_name,key_len,mac_len", CIPHER_CONFIGS)
@pytest.mark.parametrize("section", ["magic", "cipher_id", "iv", "ciphertext", "tag"])
def test_bit_flip_tamper_detection(cipher_name, key_len, mac_len, section):
    cipher = get_cipher(cipher_name)
    key, mac_key = _get_keys(cipher_name, key_len, mac_len)
    aad = b"user:secure_doc"
    
    blob = bytearray(cipher.encrypt(b"Data Rekam Medis Sangat Rahasia", key, aad=aad, mac_key=mac_key))

    # Tentukan offset pembalikan bit sesuai section
    if section == "magic":
        idx = 1
    elif section == "cipher_id":
        idx = 4
    elif section == "iv":
        if cipher_name == "rc4":
            pytest.skip("RC4 tidak memiliki segmen IV")
        idx = 6
    elif section == "ciphertext":
        idx = len(blob) // 2
    elif section == "tag":
        idx = len(blob) - 1

    blob[idx] ^= 0x01

    with pytest.raises((CryptoError, ValueError)):
        cipher.decrypt(bytes(blob), key, aad=aad, mac_key=mac_key)