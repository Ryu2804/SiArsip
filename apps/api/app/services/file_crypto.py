"""File payload encryption for the three ciphers of the SIA1 container.

Every archive object looks like:

    SIA1 | cipher_id | IV/nonce | ciphertext | tag

``aes``  : AES-256-GCM, 32-byte DEK, 12-byte nonce, 16-byte tag.
``des``  : DES-CBC + PKCS#7, 8-byte key, 8-byte IV, HMAC-SHA256 tag (32 bytes).
``rc4``  : RC4-drop3072, 16-byte key, no IV, HMAC-SHA256 tag (32 bytes).

DES and RC4 authenticate with a separate 32-byte MAC key (encrypt-then-MAC).

For AES-GCM the AAD binds the object to its owner and row id
(``owner_id.bytes + file_id.bytes``); DES/RC4 prepend the same bytes to the MAC
input, so a blob moved to another row fails verification instead of decrypting.
"""

import hashlib
import hmac as hmac_mod
import json
import os
from dataclasses import dataclass
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.models.enums import CipherAlgorithm
from app.schemas.errors.common_error import IntegrityError
from app.services.crypto.container import MAGIC, parse_container, serialize_container
from app.services.crypto.envelope import unwrap_key

CIPHER_IDS = {
    CipherAlgorithm.AES_GCM: 1,
    CipherAlgorithm.DES_CBC: 2,
    CipherAlgorithm.RC4: 3,
}

# key size, IV size (0 = no IV), tag size per algorithm
_KEY_IV_TAG = {
    CipherAlgorithm.AES_GCM: (32, 12, 16),
    CipherAlgorithm.DES_CBC: (8, 8, 32),
    CipherAlgorithm.RC4: (16, 0, 32),
}


def build_aad(owner_id: UUID, file_id: UUID) -> bytes:
    return owner_id.bytes + file_id.bytes


def needs_mac_key(algorithm: CipherAlgorithm) -> bool:
    return algorithm is not CipherAlgorithm.AES_GCM


def new_dek(algorithm: CipherAlgorithm) -> bytes:
    return os.urandom(_KEY_IV_TAG[algorithm][0])


def new_mac_key(algorithm: CipherAlgorithm) -> bytes | None:
    return os.urandom(32) if needs_mac_key(algorithm) else None


@dataclass
class EncryptedObject:
    blob: bytes
    iv: bytes | None
    tag: bytes


def _mac(algorithm: CipherAlgorithm, mac_key: bytes, iv: bytes, ciphertext: bytes, aad: bytes) -> bytes:
    header = MAGIC + bytes([CIPHER_IDS[algorithm]])
    return hmac_mod.new(mac_key, header + iv + ciphertext + aad, hashlib.sha256).digest()


def encrypt(algorithm: CipherAlgorithm, plaintext: bytes, dek: bytes, aad: bytes,
            mac_key: bytes | None = None) -> EncryptedObject:
    _, iv_len, _ = _KEY_IV_TAG[algorithm]
    iv = os.urandom(iv_len) if iv_len else b""

    if algorithm is CipherAlgorithm.AES_GCM:
        sealed = AESGCM(dek).encrypt(iv, plaintext, aad)
        ciphertext, tag = sealed[:-16], sealed[-16:]
    elif algorithm is CipherAlgorithm.DES_CBC:
        from Crypto.Cipher import DES
        from Crypto.Util.Padding import pad

        ciphertext = DES.new(dek, DES.MODE_CBC, iv=iv).encrypt(pad(plaintext, DES.block_size))
        tag = _mac(algorithm, _require(mac_key), iv, ciphertext, aad)
    else:
        from Crypto.Cipher import ARC4

        ciphertext = ARC4.new(dek, drop=3072).encrypt(plaintext)
        tag = _mac(algorithm, _require(mac_key), iv, ciphertext, aad)

    blob = serialize_container(CIPHER_IDS[algorithm], iv, ciphertext, tag)
    return EncryptedObject(blob=blob, iv=iv or None, tag=tag)


def decrypt(algorithm: CipherAlgorithm, blob: bytes, dek: bytes, aad: bytes,
            mac_key: bytes | None = None) -> bytes:
    """Verify and decrypt one SIA1 object. Any failure becomes IntegrityError."""
    cipher_id, iv, ciphertext, tag = parse_container(blob)
    if cipher_id != CIPHER_IDS[algorithm]:
        raise IntegrityError("File integrity check failed")

    if algorithm is CipherAlgorithm.AES_GCM:
        try:
            return AESGCM(dek).decrypt(iv, ciphertext + tag, aad)
        except InvalidTag:
            raise IntegrityError("File integrity check failed") from None

    expected = _mac(algorithm, _require(mac_key), iv, ciphertext, aad)
    if not hmac_mod.compare_digest(tag, expected):
        raise IntegrityError("File integrity check failed")

    if algorithm is CipherAlgorithm.DES_CBC:
        from Crypto.Cipher import DES
        from Crypto.Util.Padding import unpad

        try:
            return unpad(DES.new(dek, DES.MODE_CBC, iv=iv).decrypt(ciphertext), DES.block_size)
        except ValueError:
            raise IntegrityError("File integrity check failed") from None

    from Crypto.Cipher import ARC4

    return ARC4.new(dek, drop=3072).decrypt(ciphertext)


def object_tag(blob: bytes) -> bytes:
    """The authentication tag stored at the end of an SIA1 object."""
    return parse_container(blob)[3]


def _require(mac_key: bytes | None) -> bytes:
    if not mac_key or len(mac_key) != 32:
        raise ValueError("A 32-byte MAC key is required for des and rc4")
    return mac_key


# Original File Name (Encrypted)


def seal_name(name: str, master_key: bytes | None = None) -> bytes:
    """AES-256-GCM under MASTER_KEY; format = nonce(12) || ciphertext || tag."""
    from app.core.config import get_master_key

    nonce = os.urandom(12)
    return nonce + AESGCM(master_key or get_master_key()).encrypt(nonce, name.encode(), None)


def open_patient_identity(patient) -> dict:
    """Decrypt the patient blob to read mrn/name for the stego payload."""
    dek = unwrap_key(patient.dek_wrapped)
    aad = patient.owner_id.bytes + patient.id.bytes
    try:
        plaintext = AESGCM(dek).decrypt(patient.data_nonce, patient.data_encrypted, aad)
    except InvalidTag:
        raise IntegrityError("File integrity check failed") from None
    return json.loads(plaintext)


def open_name(sealed: bytes, master_key: bytes | None = None) -> str:
    from app.core.config import get_master_key

    if len(sealed) < 12 + 16:
        raise IntegrityError("File integrity check failed")
    try:
        plaintext = AESGCM(master_key or get_master_key()).decrypt(sealed[:12], sealed[12:], None)
    except InvalidTag:
        raise IntegrityError("File integrity check failed") from None
    return plaintext.decode()
