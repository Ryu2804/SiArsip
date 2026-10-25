"""activity_logs writes used by the file endpoints."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.activity_logs import ActivityLogs
from app.models.enums import ActivityAction


def record(db: Session, *, action: ActivityAction, user_id: UUID, file_id: UUID | None = None) -> ActivityLogs:
    entry = ActivityLogs(user_id=user_id, action=action, file_id=file_id)
    db.add(entry)
    return entry
