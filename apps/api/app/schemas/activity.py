from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ActivityAction

# Response

class ActivityLogResponse(BaseModel):
    """One row of GET /logs.

    Deliberately carries no patient data: only the action, when it happened and
    which file it concerned (an id, never the name or the patient's identity).
    """

    id: int
    action: ActivityAction
    file_id: str | None
    created_at: datetime
