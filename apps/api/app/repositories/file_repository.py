"""File repository. Queries are always scoped by owner on ``files`` alone."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.files import Files


def get_owned(db: Session, file_id: UUID, owner_id: UUID) -> Files | None:
    """One file, only if it belongs to ``owner_id`` (no join to patients)."""
    return db.scalar(
        select(Files).where(Files.id == file_id, Files.owner_id == owner_id)
    )


def storage_keys_for_patient(db: Session, patient_id: UUID) -> list[str]:
    return list(db.scalars(select(Files.storage_key).where(Files.patient_id == patient_id)))


def create(db: Session, file: Files) -> Files:
    db.add(file)
    db.flush()
    return file


def delete_row(db: Session, file: Files) -> None:
    db.delete(file)
    db.flush()
