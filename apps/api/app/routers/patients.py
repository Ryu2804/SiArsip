from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.patients import (
    PatientCreateRequest,
    PatientDeleteResponse,
    PatientListItemResponse,
    PatientResponse,
    PatientUpdateRequest,
)
from app.schemas.response import Meta, SuccessResponse, ok
from app.services import patient_service

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get("", response_model=SuccessResponse[list[PatientListItemResponse]])
def list_patients(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = patient_service.list_page(db, user, page, size)
    return ok(items, meta=Meta(page=page, size=size, total=total))


@router.post(
    "",
    response_model=SuccessResponse[PatientResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_patient(
    body: PatientCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(patient_service.create(db, user, body), message="Patient created")


@router.get("/{patient_id}", response_model=SuccessResponse[PatientResponse])
def get_patient(
    patient_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(patient_service.get(db, user, patient_id))


@router.put("/{patient_id}", response_model=SuccessResponse[PatientResponse])
def update_patient(
    patient_id: UUID,
    body: PatientUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(
        patient_service.update(db, user, patient_id, body), message="Patient updated"
    )


@router.delete("/{patient_id}", response_model=SuccessResponse[PatientDeleteResponse])
def delete_patient(
    patient_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(
        patient_service.delete(db, user, patient_id), message="Patient deleted"
    )
