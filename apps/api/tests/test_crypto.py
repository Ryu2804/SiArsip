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

@pytest.mark.parametrize("size", [0, 7, 8, 16, 25])  # Termasuk kelipatan 8 & boundary padding
def test_des_round_trip(size):
    cipher = get_cipher("des")
    key = os.urandom(8)
    mac_key = os.urandom(32)
    plaintext = os.urandom(size)
    aad = b"user_1:file_10"

    blob = cipher.encrypt(plaintext, key, aad=aad, mac_key=mac_key)
    assert cipher.decrypt(blob, key, aad=aad, mac_key=mac_key) == plaintext

def test_des_tamper_fails():
    cipher = get_cipher("des")
    key = os.urandom(8)
    mac_key = os.urandom(32)
    blob = bytearray(cipher.encrypt(b"Data rahasia", key, aad=b"user:1", mac_key=mac_key))

    blob[6] ^= 0x01  # Manipulasi IV
    with pytest.raises(IntegrityError):
        cipher.decrypt(bytes(blob), key, aad=b"user:1", mac_key=mac_key)

def test_rc4_round_trip():
    cipher = get_cipher("rc4")
    key = os.urandom(16)
    mac_key = os.urandom(32)
    plaintext = b"Payload stream medis"
    aad = b"user_1:file_11"

    blob = cipher.encrypt(plaintext, key, aad=aad, mac_key=mac_key)
    assert cipher.decrypt(blob, key, aad=aad, mac_key=mac_key) == plaintext

def test_rc4_tamper_fails():
    cipher = get_cipher("rc4")
    key = os.urandom(16)
    mac_key = os.urandom(32)
    blob = bytearray(cipher.encrypt(b"Payload", key, aad=b"user:1", mac_key=mac_key))

    blob[-1] ^= 0x01  # Manipulasi tag HMAC
    with pytest.raises(IntegrityError):
        cipher.decrypt(bytes(blob), key, aad=b"user:1", mac_key=mac_key)