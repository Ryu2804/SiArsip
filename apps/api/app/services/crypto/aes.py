import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from app.services.crypto.base import BaseCipher
from app.services.crypto.container import serialize_container, parse_container
from app.services.crypto.exceptions import IntegrityError

class AesGcmCipher(BaseCipher):
    cipher_id = 1
    name = "aes"

    def encrypt(self, plaintext: bytes, key: bytes, aad: bytes = b"", mac_key: bytes | None = None) -> bytes:
        if len(key) != 32:
            raise ValueError("Kunci AES-256 harus tepat 32 byte (256 bit)")
        
        nonce = os.urandom(12)
        aesgcm = AESGCM(key)
        # AESGCM.encrypt mengembalikan ciphertext + 16 byte tag di akhir
        encrypted = aesgcm.encrypt(nonce, plaintext, aad)
        ciphertext = encrypted[:-16]
        tag = encrypted[-16:]
        
        return serialize_container(self.cipher_id, nonce, ciphertext, tag)

    def decrypt(self, blob: bytes, key: bytes, aad: bytes = b"", mac_key: bytes | None = None) -> bytes:
        if len(key) != 32:
            raise ValueError("Kunci AES-256 harus tepat 32 byte (256 bit)")
        
        cipher_id, nonce, ciphertext, tag = parse_container(blob)
        if cipher_id != self.cipher_id:
            raise ValueError(f"Blob bukan milik AES (cipher_id={cipher_id})")
        
        aesgcm = AESGCM(key)
        try:
            return aesgcm.decrypt(nonce, ciphertext + tag, aad)
        except InvalidTag:
            raise IntegrityError("Tag AES-GCM tidak valid. Data atau AAD telah dimanipulasi")