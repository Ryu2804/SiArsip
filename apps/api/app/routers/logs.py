from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.enums import ActivityAction
from app.models.user import User
from app.schemas.activity import ActivityLogResponse
from app.schemas.response import Meta, SuccessResponse, ok
from app.services import activity_service

router = APIRouter(prefix="/logs", tags=["Logs"])

@router.get("", response_model=SuccessResponse[list[ActivityLogResponse]])
def list_activity_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    action: ActivityAction | None = Query(None, description="Only entries with this action"),
    date_from: datetime | None = Query(None, description="Only entries at/after this instant"),
    date_to: datetime | None = Query(None, description="Only entries at/before this instant"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The signed-in user's own activity log. Never includes patient identity."""
    items, total = activity_service.list_page(
        db,
        user,
        page,
        size,
        action=action,
        date_from=date_from,
        date_to=date_to,
    )
    return ok(items, meta=Meta(page=page, size=size, total=total))
