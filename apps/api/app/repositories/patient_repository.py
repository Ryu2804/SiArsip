"""Patient repository. Queries are always scoped by owner at the SQL level."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.patients import Patients


def get_owned(db: Session, patient_id: UUID, owner_id: UUID) -> Patients | None:
    """One patient, only if it belongs to ``owner_id``.

    Ownership is part of the WHERE clause on purpose: fetching first and then
    comparing owner_id would leak that the id exists.
    """
    return db.scalar(
        select(Patients).where(
            Patients.id == patient_id,
            Patients.owner_id == owner_id,
        )
    )


def list_owned(db: Session, owner_id: UUID, limit: int, offset: int) -> list[Patients]:
    """Newest first, paginated."""
    return list(
        db.scalars(
            select(Patients)
            .where(Patients.owner_id == owner_id)
            .order_by(Patients.created_at.desc(), Patients.id.desc())
            .limit(limit)
            .offset(offset)
        )
    )


def count_owned(db: Session, owner_id: UUID) -> int:
    return db.scalar(
        select(func.count()).select_from(Patients).where(Patients.owner_id == owner_id)
    )


def create(db: Session, patient: Patients) -> Patients:
    db.add(patient)
    db.flush()
    return patient


def delete(db: Session, patient: Patients) -> None:
    db.delete(patient)
    db.flush()
