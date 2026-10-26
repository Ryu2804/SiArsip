"""activity_logs writes used by the file endpoints and reads for GET /logs."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.activity_logs import ActivityLogs
from app.models.enums import ActivityAction

def record(db: Session, *, action: ActivityAction, user_id: UUID, file_id: UUID | None = None) -> ActivityLogs:
    entry = ActivityLogs(user_id=user_id, action=action, file_id=file_id)
    db.add(entry)
    return entry

def _owned_query(
    user_id: UUID,
    *,
    action: ActivityAction | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> Select:
    """Base filter. Ownership is in the WHERE clause, never a post-check."""
    stmt = select(ActivityLogs).where(ActivityLogs.user_id == user_id)
    if action is not None:
        stmt = stmt.where(ActivityLogs.action == action)
    if date_from is not None:
        stmt = stmt.where(ActivityLogs.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(ActivityLogs.created_at <= date_to)
    return stmt

def list_owned(
    db: Session,
    user_id: UUID,
    *,
    action: ActivityAction | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int,
    offset: int,
) -> list[ActivityLogs]:
    """The user's own entries, newest first, paginated."""
    stmt = (
        _owned_query(user_id, action=action, date_from=date_from, date_to=date_to)
        .order_by(ActivityLogs.created_at.desc(), ActivityLogs.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt))

def count_owned(
    db: Session,
    user_id: UUID,
    *,
    action: ActivityAction | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> int:
    stmt = _owned_query(user_id, action=action, date_from=date_from, date_to=date_to)
    return db.scalar(select(func.count()).select_from(stmt.subquery()))
