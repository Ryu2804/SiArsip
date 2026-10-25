"""Patient payload encryption.

The whole patient record is stored as one AES-256-GCM blob so the database only
ever holds ciphertext:

    AAD         = owner_id.bytes + patient_id.bytes
    plaintext   = PatientCreateRequest.model_dump_json() as bytes
    data_nonce  = fresh 12-byte nonce (one per write)
    dek_wrapped = DEK encrypted under MASTER_KEY

Binding the AAD to owner + patient id means a blob copied onto another row (or
attributed to another user) fails verification instead of decrypting.
"""

import json
import os
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.schemas.errors.common_error import IntegrityError
from app.services.crypto.envelope import unwrap_key, wrap_key

NONCE_BYTES = 12
DEK_BYTES = 32


def build_aad(owner_id: UUID, patient_id: UUID) -> bytes:
    return owner_id.bytes + patient_id.bytes


def new_dek() -> bytes:
    return os.urandom(DEK_BYTES)


def new_nonce() -> bytes:
    return os.urandom(NONCE_BYTES)


def encrypt_patient(payload: dict, dek: bytes, nonce: bytes, aad: bytes) -> bytes:
    plaintext = json.dumps(payload, separators=(",", ":"), default=str).encode()
    return AESGCM(dek).encrypt(nonce, plaintext, aad)


def decrypt_patient(blob: bytes, dek: bytes, nonce: bytes, aad: bytes) -> dict:
    """Decrypt and parse the patient payload; a bad tag becomes IntegrityError."""
    try:
        plaintext = AESGCM(dek).decrypt(nonce, blob, aad)
    except InvalidTag:
        raise IntegrityError("Encrypted patient data failed integrity verification") from None
    return json.loads(plaintext)


__all__ = [
    "build_aad",
    "new_dek",
    "new_nonce",
    "encrypt_patient",
    "decrypt_patient",
    "wrap_key",
    "unwrap_key",
]
