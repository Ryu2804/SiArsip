from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, LargeBinary, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

# AES-GCM nonce length
DATA_NONCE_BYTES = 12


class Patients(Base):
    __tablename__ = "patients"
    __table_args__ = (
        CheckConstraint(
            f"length(data_nonce) = {DATA_NONCE_BYTES}",
            name="ck_patients_data_nonce_len",
        ),
    )

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    # Foreign key -> users.id
    owner_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # Encrypted patient data
    data_encrypted: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
    )

    # AES-GCM nonce (12 bytes)
    data_nonce: Mapped[bytes] = mapped_column(
        LargeBinary(DATA_NONCE_BYTES),
        nullable=False,
    )

    # Wrapped data encryption key
    dek_wrapped: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship -> User
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="patients",
    )
    files: Mapped[list["Files"]] = relationship(
        "Files",
        back_populates="patient", cascade="all, delete-orphan", passive_deletes=True
    )
