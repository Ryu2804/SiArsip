from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------- Request ----------


class PatientCreateRequest(BaseModel):
    """Body for POST /patients. Unknown fields such as owner_id are rejected."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    mrn: str = Field(min_length=1, max_length=30, pattern=r"^[A-Za-z0-9/-]+$")
    nik: str | None = Field(default=None, pattern=r"^\d{16}$")
    birth_date: date | None = None
    diagnosis: str | None = Field(default=None, max_length=500)

    @field_validator("nik", "diagnosis", mode="before")
    @classmethod
    def blank_to_none(cls, v):
        # empty form inputs arrive as ""
        return None if isinstance(v, str) and not v.strip() else v

    @field_validator("birth_date")
    @classmethod
    def not_in_future(cls, v: date | None) -> date | None:
        if v and v > date.today():
            raise ValueError("birth_date cannot be in the future")
        return v


class PatientUpdateRequest(PatientCreateRequest):
    """Body for PUT /patients/{patient_id}. Full replacement, same rules as create."""


# ---------- Response ----------


class PatientResponse(BaseModel):
    """One patient with every field. Used by POST, GET detail and PUT."""

    id: UUID
    name: str
    mrn: str
    nik: str | None
    birth_date: date | None
    diagnosis: str | None
    created_at: datetime
    updated_at: datetime


class PatientListItemResponse(BaseModel):
    """One row of GET /patients. No diagnosis, NIK masked."""

    id: UUID
    name: str
    mrn: str
    nik_masked: str | None  # "3201********0001"
    birth_date: date | None
    created_at: datetime
    updated_at: datetime


class PatientDeleteResponse(BaseModel):
    id: UUID
    deleted_files: int