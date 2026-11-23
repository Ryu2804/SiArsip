import enum
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.enums import CipherAlgorithm, FileCategory, PDPClass


# Request


class CipherChoice(enum.StrEnum):
    """Short names the upload form accepts."""

    AES = "aes"
    DES = "des"
    RC4 = "rc4"


CIPHER_ALGORITHM = {
    CipherChoice.AES: CipherAlgorithm.AES_GCM,
    CipherChoice.DES: CipherAlgorithm.DES_CBC,
    CipherChoice.RC4: CipherAlgorithm.RC4,
}


class FileUploadRequest(BaseModel):
    """Form fields of POST /patients/{patient_id}/files. The file itself is a separate UploadFile."""

    model_config = ConfigDict(extra="forbid")

    category: FileCategory
    cipher: CipherChoice = CipherChoice.AES
    pin: str | None = None

    @field_validator("pin", mode="before")
    @classmethod
    def normalize_pin(cls, v: object) -> str | None:
        if v is None or v == "":
            return None
        if isinstance(v, str):
            cleaned = v.strip()
            if not cleaned:
                return None
            if not cleaned.isdigit() or len(cleaned) < 4 or len(cleaned) > 8:
                raise ValueError("PIN harus terdiri dari 4 hingga 8 digit angka")
            return cleaned
        raise ValueError("PIN harus berupa string")


# Response


class FileResponse(BaseModel):
    """File metadata without content. Used by upload and GET /files/{file_id}."""

    id: UUID
    patient_id: UUID
    original_name: str  # decrypted from original_name_encrypted
    category: FileCategory
    pdp_class: PDPClass
    mime_type: str
    size_bytes: int
    sha256: str  # sha256_plain as 64 hex chars
    algorithm: CipherAlgorithm
    shareable: bool  # category == clinical_image
    has_pin: bool = False
    created_at: datetime
