from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Wrapped steganography key; NULL until the user has a key provisioned.
    stego_key_wrapped: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    patients: Mapped[list["Patients"]] = relationship(
        "Patients",
        back_populates="owner",
    )
    activity_logs: Mapped[list["ActivityLogs"]] = relationship(
        "ActivityLogs",
        back_populates="user",
    )
    files: Mapped[list["Files"]] = relationship(
        "Files",
        back_populates="owner",
    )
