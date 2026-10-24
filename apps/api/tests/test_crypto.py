import os
import pytest
from app.services.crypto import get_cipher, IntegrityError, InvalidContainerError

def test_aes_round_trip():
    cipher = get_cipher("aes")
    key = os.urandom(32)
    aad = b"user_1:file_99"
    plaintext = b"Data rekam medis rahasia pasien klinik."

    blob = cipher.encrypt(plaintext, key, aad)
    decrypted = cipher.decrypt(blob, key, aad)
    assert decrypted == plaintext

def test_aes_tamper_bit_flip():
    cipher = get_cipher("aes")
    key = os.urandom(32)
    aad = b"user_1:file_99"
    blob = bytearray(cipher.encrypt(b"Data penting", key, aad))

    # Balik 1 bit pada bagian payload
    blob[-5] ^= 0x01

    with pytest.raises(IntegrityError):
        cipher.decrypt(bytes(blob), key, aad)

def test_aes_wrong_aad_rejected():
    cipher = get_cipher("aes")
    key = os.urandom(32)
    blob = cipher.encrypt(b"Data rahasia", key, aad=b"user_1:file_99")

    # Akses ditolak saat context AAD berbeda (user lain)
    with pytest.raises(IntegrityError):
        cipher.decrypt(blob, key, aad=b"user_2:file_99")

def test_invalid_magic_rejected():
    cipher = get_cipher(1)
    with pytest.raises(InvalidContainerError):
        cipher.decrypt(b"FAKE\x01" + b"\x00" * 30, os.urandom(32))