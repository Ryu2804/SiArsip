import hashlib
import hmac
import os
from Crypto.Cipher import DES
from Crypto.Util.Padding import pad, unpad
from app.services.crypto.base import BaseCipher
from app.services.crypto.container import MAGIC, parse_container, serialize_container
from app.services.crypto.exceptions import IntegrityError

class DesCbcHmacCipher(BaseCipher):
    cipher_id = 2
    name = "des"

    def encrypt(self, plaintext: bytes, key: bytes, aad: bytes = b"", mac_key: bytes | None = None) -> bytes:
        if len(key) != 8:
            raise ValueError("Kunci DES harus tepat 8 byte (64-bit)")
        if not mac_key or len(mac_key) != 32:
            raise ValueError("Kunci MAC wajib disediakan dan tepat 32 byte untuk HMAC-SHA256")

        iv = os.urandom(8)
        cipher = DES.new(key, DES.MODE_CBC, iv=iv)
        padded = pad(plaintext, DES.block_size)
        ciphertext = cipher.encrypt(padded)

        #HMAC dihitung atas header + IV + ciphertext + AAD
        header = MAGIC + bytes([self.cipher_id])
        mac_payload = header + iv + ciphertext + aad
        tag = hmac.new(mac_key, mac_payload, hashlib.sha256).digest()

        return serialize_container(self.cipher_id, iv, ciphertext, tag)

    def decrypt(self, blob: bytes, key: bytes, aad: bytes = b"", mac_key: bytes | None = None) -> bytes:
        if len(key) != 8:
            raise ValueError("Kunci DES harus tepat 8 byte (64-bit)")
        if not mac_key or len(mac_key) != 32:
            raise ValueError("Kunci MAC wajib disediakan dan tepat 32 byte untuk HMAC-SHA256")

        cipher_id, iv, ciphertext, tag = parse_container(blob)
        if cipher_id != self.cipher_id:
            raise ValueError(f"Blob bukan milik DES (cipher_id={cipher_id})")

        # Verifikasi HMAC sebelum dekripsi
        header = MAGIC + bytes([self.cipher_id])
        mac_payload = header + iv + ciphertext + aad
        expected_tag = hmac.new(mac_key, mac_payload, hashlib.sha256).digest()

        if not hmac.compare_digest(tag, expected_tag):
            raise IntegrityError("Verifikasi HMAC DES gagal. Data atau AAD telah dimanipulasi")

        cipher = DES.new(key, DES.MODE_CBC, iv=iv)
        padded = cipher.decrypt(ciphertext)
        try:
            return unpad(padded, DES.block_size)
        except ValueError:
            raise IntegrityError("Padding PKCS#7 tidak valid")