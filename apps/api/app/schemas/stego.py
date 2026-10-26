from datetime import date
from uuid import UUID

from pydantic import BaseModel


class StegoRevealResponse(BaseModel):
    """Identity recovered from a shared clinical image."""

    patient_id: UUID
    name: str
    mrn: str
    birth_date: date | None = None
    diagnosis: str | None = None
