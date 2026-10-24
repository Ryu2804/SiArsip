import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.files import _enum_values


class ActivityAction(enum.Enum):
    UPLOAD = "upload"
    DOWNLOAD = "download"
    VIEW = "view"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"


class ActivityLogs(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    # Nullable: system events (e.g. failed login attempts) have no account yet.
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    action: Mapped[ActivityAction] = mapped_column(
        Enum(ActivityAction, name="activity_action", values_callable=_enum_values),
        nullable=False,
    )

    # Nullable: not every action concerns a file.
    file_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("files.id"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User | None"] = relationship(
        "User",
        back_populates="activity_logs",
    )
    file: Mapped["Files | None"] = relationship("Files")
