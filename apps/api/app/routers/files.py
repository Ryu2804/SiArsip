from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from pydantic import BaseModel, ConfigDict

from app.schemas.file import FileResponse, FileUploadRequest
from app.schemas.response import SuccessResponse, ok
from app.services import file_service

router = APIRouter(tags=["Files"])

# Anything echoed into a download response must not be cached or sniffed.
DOWNLOAD_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
}


class _UploadForm(FileUploadRequest):
    """FileUploadRequest plus the multipart 'file' part.

    FastAPI 0.162 feeds every form field into the model bound with Form(), including
    the upload itself; with extra="forbid" that part otherwise fails as an unknown
    field. Declaring it here keeps unknown fields rejected while accepting 'file'.
    """

    model_config = ConfigDict(extra="forbid")

    file: object | None = None


def content_disposition(filename: str) -> str:
    """attachment header with an ASCII fallback plus RFC 5987 UTF-8 form."""
    ascii_name = filename.encode("ascii", "replace").decode().replace('"', "_")
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{_quote(filename)}"


def _quote(value: str) -> str:
    from urllib.parse import quote

    return quote(value, safe="")


@router.post(
    "/patients/{patient_id}/files",
    response_model=SuccessResponse[FileResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    patient_id: UUID,
    form: Annotated[_UploadForm, Form()],
    file: Annotated[UploadFile, File()],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fields = FileUploadRequest(category=form.category, cipher=form.cipher)
    return ok(
        await file_service.upload(db, user, patient_id, fields, file),
        message="File uploaded",
    )


@router.get("/files/{file_id}", response_model=SuccessResponse[FileResponse])
def get_file(
    file_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(file_service.get(db, user, file_id))


@router.get("/files/{file_id}/download", response_class=Response)
def download_file(
    file_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Every check happens inside the service, before a single byte is sent.
    result = file_service.download(db, user, file_id)
    return Response(
        content=result.content,
        media_type=result.mime_type,
        headers={
            "Content-Disposition": content_disposition(result.original_name),
            "Repr-Digest": file_service.repr_digest(result.sha256),
            **DOWNLOAD_HEADERS,
        },
    )


@router.post("/files/{file_id}/share-image", response_class=Response)
def share_image(
    file_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data, kind = file_service.share_image(db, user, file_id)

    media_type = "image/jpeg" if kind == "jpg" else "image/png"
    filename = f"shared_{file_id}.{kind}"  # no patient data in filenames

    return Response(
        content=data,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            **DOWNLOAD_HEADERS,
        },
    )