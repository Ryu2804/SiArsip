import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.files import Files
from app.models.patients import Patients
from app.models.user import User
from app.repositories import patient_repository
from app.schemas.errors.common_error import NotFoundError
from app.schemas.patients import (
    PatientCreateRequest,
    PatientDeleteResponse,
    PatientListItemResponse,
    PatientResponse,
    PatientUpdateRequest,
)
from app.services import patient_crypto

logger = logging.getLogger(__name__)

PATIENT_NOT_FOUND = "Patient not found"


# -helper


def mask_nik(nik: str | None) -> str | None:
    """3201234567890001 -> 3201********0001 (keep first 4 and last 4)."""
    if not nik:
        return None
    if len(nik) <= 8:
        return "*" * len(nik)
    return f"{nik[:4]}{'*' * (len(nik) - 8)}{nik[-4:]}"


def _payload(body: PatientCreateRequest) -> dict:
    """The cleartext JSON that goes inside the blob."""
    data = body.model_dump(mode="json")
    # Optional fields absent from the request are stored as explicit nulls.
    return {
        "name": data["name"],
        "mrn": data["mrn"],
        "nik": data.get("nik"),
        "birth_date": data.get("birth_date"),
        "diagnosis": data.get("diagnosis"),
    }


def _decrypt(patient: Patients) -> dict:
    aad = patient_crypto.build_aad(patient.owner_id, patient.id)
    dek = patient_crypto.unwrap_key(patient.dek_wrapped)
    return patient_crypto.decrypt_patient(
        patient.data_encrypted, dek, patient.data_nonce, aad
    )


def _as_response(patient: Patients, data: dict) -> PatientResponse:
    return PatientResponse(
        id=patient.id,
        name=data["name"],
        mrn=data["mrn"],
        nik=data.get("nik"),
        birth_date=data.get("birth_date"),
        diagnosis=data.get("diagnosis"),
        created_at=patient.created_at,
        updated_at=patient.updated_at,
    )


def _as_list_item(patient: Patients, data: dict) -> PatientListItemResponse:
    return PatientListItemResponse(
        id=patient.id,
        name=data["name"],
        mrn=data["mrn"],
        nik_masked=mask_nik(data.get("nik")),
        birth_date=data.get("birth_date"),
        created_at=patient.created_at,
        updated_at=patient.updated_at,
    )


# Service functions


def create(db: Session, user: User, body: PatientCreateRequest) -> PatientResponse:
    # The id is chosen before insert because it is part of the AAD.
    patient_id = uuid4()
    dek = patient_crypto.new_dek()
    nonce = patient_crypto.new_nonce()
    aad = patient_crypto.build_aad(user.id, patient_id)
    payload = _payload(body)

    patient = Patients(
        id=patient_id,
        owner_id=user.id,
        data_encrypted=patient_crypto.encrypt_patient(payload, dek, nonce, aad),
        data_nonce=nonce,
        dek_wrapped=patient_crypto.wrap_key(dek),
    )
    patient_repository.create(db, patient)
    db.commit()
    db.refresh(patient)

    return _as_response(patient, payload)


def get(db: Session, user: User, patient_id: UUID) -> PatientResponse:
    patient = patient_repository.get_owned(db, patient_id, user.id)
    if patient is None:
        raise NotFoundError(PATIENT_NOT_FOUND)
    return _as_response(patient, _decrypt(patient))


def list_page(
    db: Session, user: User, page: int, size: int
) -> tuple[list[PatientListItemResponse], int]:
    total = patient_repository.count_owned(db, user.id)
    rows = patient_repository.list_owned(db, user.id, limit=size, offset=(page - 1) * size)
    return [_as_list_item(row, _decrypt(row)) for row in rows], total


def update(
    db: Session, user: User, patient_id: UUID, body: PatientUpdateRequest
) -> PatientResponse:
    patient = patient_repository.get_owned(db, patient_id, user.id)
    if patient is None:
        raise NotFoundError(PATIENT_NOT_FOUND)

    # Same DEK, but a fresh nonce: reusing a nonce with the same key breaks GCM.
    dek = patient_crypto.unwrap_key(patient.dek_wrapped)
    nonce = patient_crypto.new_nonce()
    aad = patient_crypto.build_aad(patient.owner_id, patient.id)
    payload = _payload(body)

    patient.data_encrypted = patient_crypto.encrypt_patient(payload, dek, nonce, aad)
    patient.data_nonce = nonce
    patient.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(patient)

    return _as_response(patient, payload)


def delete(db: Session, user: User, patient_id: UUID) -> PatientDeleteResponse:
    patient = patient_repository.get_owned(db, patient_id, user.id)
    if patient is None:
        raise NotFoundError(PATIENT_NOT_FOUND)

    # Collect the object keys BEFORE the rows disappear (files cascade on delete).
    storage_keys = list(
        db.scalars(select(Files.storage_key).where(Files.patient_id == patient.id))
    )

    patient_repository.delete(db, patient)
    # Commit first: a rolled-back transaction must not leave objects already removed.
    db.commit()

    _delete_objects(storage_keys)

    return PatientDeleteResponse(id=patient_id, deleted_files=len(storage_keys))


def _delete_objects(storage_keys: list[str]) -> None:
    """Remove the blobs from object storage.

    A failure here is logged and swallowed: the patient row is already gone, so the
    response still reports success (contract: "response tetap sukses").
    """
    if not storage_keys:
        return
    try:
        from app.services.storage import delete_objects

        delete_objects(storage_keys)
    except Exception:
        logger.exception("Failed to delete %d object(s) from storage", len(storage_keys))
