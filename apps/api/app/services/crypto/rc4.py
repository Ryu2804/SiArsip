import hashlib
import hmac
from Crypto.Cipher import ARC4
from app.services.crypto.base import BaseCipher
from app.services.crypto.container import MAGIC, parse_container, serialize_container
from app.services.crypto.exceptions import IntegrityError

class Rc4HmacCipher(BaseCipher):
    cipher_id = 3
    name = "rc4"

    def encrypt(self, plaintext: bytes, key: bytes, aad: bytes = b"", mac_key: bytes | None = None) -> bytes:
        if len(key) != 16:
            raise ValueError("Kunci RC4 harus tepat 16 byte (128-bit)")
        if not mac_key or len(mac_key) != 32:
            raise ValueError("Kunci MAC wajib disediakan dan tepat 32 byte untuk HMAC-SHA256")

        cipher = ARC4.new(key, drop=3072)
        ciphertext = cipher.encrypt(plaintext)
        iv = b""

        # Encrypt-then-MAC: HMAC dihitung atas header + IV(kosong) + ciphertext + AAD
        header = MAGIC + bytes([self.cipher_id])
        mac_payload = header + iv + ciphertext + aad
        tag = hmac.new(mac_key, mac_payload, hashlib.sha256).digest()

        return serialize_container(self.cipher_id, iv, ciphertext, tag)

    def decrypt(self, blob: bytes, key: bytes, aad: bytes = b"", mac_key: bytes | None = None) -> bytes:
        if len(key) != 16:
            raise ValueError("Kunci RC4 harus tepat 16 byte (128-bit)")
        if not mac_key or len(mac_key) != 32:
            raise ValueError("Kunci MAC wajib disediakan dan tepat 32 byte untuk HMAC-SHA256")

        cipher_id, iv, ciphertext, tag = parse_container(blob)
        if cipher_id != self.cipher_id:
            raise ValueError(f"Blob bukan milik RC4 (cipher_id={cipher_id})")

        header = MAGIC + bytes([self.cipher_id])
        mac_payload = header + iv + ciphertext + aad
        expected_tag = hmac.new(mac_key, mac_payload, hashlib.sha256).digest()

        if not hmac.compare_digest(tag, expected_tag):
            raise IntegrityError("Verifikasi HMAC RC4 gagal. Data atau AAD telah dimanipulasi")

        cipher = ARC4.new(key, drop=3072)
        return cipher.decrypt(ciphertext)