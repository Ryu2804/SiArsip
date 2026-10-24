import hashlib
import os
import pytest
from app.services.crypto import get_cipher
from app.services.crypto.envelope import wrap_key, unwrap_key, rewrap_value

def test_rewrap_and_decrypt_end_to_end():
    # 1. Kunci master lama dan baru
    old_master_key = os.urandom(32)
    new_master_key = os.urandom(32)

    # 2. Simulasi pembuatan file terenkripsi AES
    cipher = get_cipher("aes")
    file_dek = os.urandom(32)
    original_data = b"Dokumen rekam medis pasien sebelum rotasi master key."
    original_sha256 = hashlib.sha256(original_data).hexdigest()
    aad = b"user_1:file_101"

    # Enkripsi data & bungkus DEK dengan master key lama
    ciphertext_blob = cipher.encrypt(original_data, file_dek, aad=aad)
    wrapped_dek_old = wrap_key(file_dek, master_key=old_master_key)

    # 3. Eksekusi rotasi: rewrap DEK ke master key baru
    wrapped_dek_new = rewrap_value(wrapped_dek_old, old_master_key, new_master_key)

    # 4. Verifikasi: Ciphertext di storage TIDAK disentuh, hanya unwrap DEK dengan master key baru
    unwrapped_dek = unwrap_key(wrapped_dek_new, master_key=new_master_key)
    decrypted_data = cipher.decrypt(ciphertext_blob, unwrapped_dek, aad=aad)

    # Pastikan data identik 100%
    assert hashlib.sha256(decrypted_data).hexdigest() == original_sha256
    assert decrypted_data == original_data

def test_rewrap_with_wrong_old_key_fails():
    old_master_key = os.urandom(32)
    fake_old_key = os.urandom(32)
    new_master_key = os.urandom(32)
    
    file_dek = os.urandom(32)
    wrapped_dek = wrap_key(file_dek, master_key=old_master_key)

    with pytest.raises(Exception):
        rewrap_value(wrapped_dek, fake_old_key, new_master_key)