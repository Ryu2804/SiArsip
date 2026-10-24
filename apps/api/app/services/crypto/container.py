import struct
from app.services.crypto.exceptions import InvalidContainerError

MAGIC = b"SIA1"

# Metadata panjang [IV/nonce, Tag/HMAC] per cipher id
CIPHER_SPECS = {
    1: {"name": "aes", "iv_len": 12, "tag_len": 16},   # AES-256-GCM
    2: {"name": "des", "iv_len": 8, "tag_len": 32},    # DES-CBC + HMAC-SHA256
    3: {"name": "rc4", "iv_len": 0, "tag_len": 32},    # RC4-drop3072 + HMAC-SHA256
}

def serialize_container(cipher_id: int, iv: bytes, ciphertext: bytes, tag: bytes) -> bytes:
    if cipher_id not in CIPHER_SPECS:
        raise InvalidContainerError(f"Cipher ID {cipher_id} tidak valid")
    return MAGIC + struct.pack("B", cipher_id) + iv + ciphertext + tag

def parse_container(blob: bytes) -> tuple[int, bytes, bytes, bytes]:
    if len(blob) < 5 or blob[:4] != MAGIC:
        raise InvalidContainerError("Magic header tidak valid (harus SIA1)")
    
    cipher_id = blob[4]
    if cipher_id not in CIPHER_SPECS:
        raise InvalidContainerError(f"Cipher ID {cipher_id} tidak dikenal")
    
    spec = CIPHER_SPECS[cipher_id]
    iv_len = spec["iv_len"]
    tag_len = spec["tag_len"]
    min_len = 5 + iv_len + tag_len
    
    if len(blob) < min_len:
        raise InvalidContainerError("Ukuran blob kontainer terlalu pendek atau terpotong")
    
    iv = blob[5 : 5 + iv_len]
    tag = blob[-tag_len:] if tag_len > 0 else b""
    ciphertext = blob[5 + iv_len : -tag_len] if tag_len > 0 else blob[5 + iv_len :]
    
    return cipher_id, iv, ciphertext, tag