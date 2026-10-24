import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    LargeBinary,
    SmallInteger,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.patients import Patients
    from app.models.user import User

# SHA-256 digest length, enforced by a CHECK (Postgres ignores bytea(32)).
SHA256_BYTES = 32
MAX_FILE_BYTES = 100 * 1024 * 1024


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Persist member *values* ("aes-gcm"), not names ("AES_GCM")."""
    return [member.value for member in enum_cls]


class FileCategory(enum.StrEnum):
    """The four file data types from the PRD."""

    IDENTITY_SCAN = "identity_scan"  # KTP, BPJS: JPG/PNG/PDF
    OFFICE_DOCUMENT = "office_document"  # informed consent, referral: PDF/DOCX/XLSX
    VIDEO = "video"  # wound care, USG: MP4
    CLINICAL_IMAGE = "clinical_image"  # x-ray, wound photo: JPG/PNG (stego share)


class PDPClass(enum.StrEnum):
    """UU PDP Pasal 4: specific (health) vs general personal data."""

    SPECIFIC = "specific"
    GENERAL = "general"


class CipherAlgorithm(enum.StrEnum):
    AES_GCM = "aes-gcm"
    DES_CBC = "des-cbc"
    RC4 = "rc4"


class Files(Base):
    __tablename__ = "files"
    __table_args__ = (
        CheckConstraint(
            f"length(sha256_plain) = {SHA256_BYTES}",
            name="ck_files_sha256_plain_len",
        ),
        CheckConstraint(
            f"size_bytes > 0 AND size_bytes <= {MAX_FILE_BYTES}",
            name="ck_files_size_range",
        ),
        # rc4 has no IV; aes-gcm and des-cbc must have one
        CheckConstraint(
            "(algorithm = 'rc4') = (iv IS NULL)",
            name="ck_files_iv_matches_algorithm",
        ),
        # GCM authenticates itself; des-cbc and rc4 need a separate HMAC key
        CheckConstraint(
            "(algorithm = 'aes-gcm') = (mac_key_wrapped IS NULL)",
            name="ck_files_mac_key_matches_algorithm",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category: Mapped[FileCategory] = mapped_column(
        Enum(FileCategory, name="file_category", values_callable=_enum_values),
        nullable=False,
    )

    # set by the server from category, never by the client
    pdp_class: Mapped[PDPClass] = mapped_column(
        Enum(PDPClass, name="pdp_class", values_callable=_enum_values),
        nullable=False,
    )

    # detected from magic bytes, not the extension
    mime_type: Mapped[str] = mapped_column(String(127), nullable=False)

    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    original_name_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    # SHA-256 of the plaintext, re-checked after decrypting on download
    sha256_plain: Mapped[bytes] = mapped_column(LargeBinary(SHA256_BYTES), nullable=False)

    algorithm: Mapped[CipherAlgorithm] = mapped_column(
        Enum(CipherAlgorithm, name="cipher_algorithm", values_callable=_enum_values),
        nullable=False,
    )

    format_version: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)

    # 12 B nonce (aes-gcm), 8 B IV (des-cbc), NULL (rc4)
    iv: Mapped[bytes | None] = mapped_column(LargeBinary)

    # 16 B GCM tag or 32 B HMAC-SHA256
    auth_tag: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    dek_wrapped: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    mac_key_wrapped: Mapped[bytes | None] = mapped_column(LargeBinary)

    # archives/<id>.bin; unique=True alone creates the one constraint
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    owner: Mapped["User"] = relationship(back_populates="files")
    patient: Mapped["Patients"] = relationship(back_populates="files")
