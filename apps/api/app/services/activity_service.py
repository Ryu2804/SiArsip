from datetime import datetime

from sqlalchemy.orm import Session

from app.models.enums import ActivityAction
from app.models.user import User
from app.repositories import activity_repository
from app.schemas.activity import ActivityLogResponse

def list_page(
    db: Session,
    user: User,
    page: int,
    size: int,
    *,
    action: ActivityAction | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[list[ActivityLogResponse], int]:
    """The caller's own activity, newest first. Other users' entries are unreachable."""
    total = activity_repository.count_owned(
        db, user.id, action=action, date_from=date_from, date_to=date_to
    )
    rows = activity_repository.list_owned(
        db,
        user.id,
        action=action,
        date_from=date_from,
        date_to=date_to,
        limit=size,
        offset=(page - 1) * size,
    )
    return [
        ActivityLogResponse(
            id=row.id,
            action=row.action,
            file_id=str(row.file_id) if row.file_id else None,
            created_at=row.created_at,
        )
        for row in rows
    ], total
