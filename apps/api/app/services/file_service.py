import base64
import hashlib
import hmac
import logging
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models.enums import ActivityAction, FileCategory, PDPClass
from app.models.files import MAX_FILE_BYTES, Files
from app.models.patients import Patients
from app.models.user import User
from app.repositories import (
    activity_repository,
    file_repository,
    patient_repository,
)
from fastapi.exceptions import RequestValidationError

from app.schemas.errors.common_error import (
    ConflictError,
    FileTooLargeError,
    IntegrityError,
    NotFoundError,
    StorageError,
    UnsupportedFileTypeError,
)
from app.schemas.file import CIPHER_ALGORITHM, FileResponse, FileUploadRequest
from app.services import file_crypto, mime, storage
from app.services.crypto.envelope import unwrap_key, wrap_key

logger = logging.getLogger(__name__)

FILE_NOT_FOUND = "File not found"
INTEGRITY_MESSAGE = "File integrity check failed"
CHUNK_SIZE = 1024 * 1024

# category -> (allowed MIME types, PDP class)
CATEGORY_RULES: dict[FileCategory, tuple[set[str], PDPClass]] = {
    FileCategory.IDENTITY_SCAN: ({mime.JPEG, mime.PNG, mime.PDF}, PDPClass.GENERAL),
    FileCategory.OFFICE_DOCUMENT: ({mime.PDF, mime.DOCX, mime.XLSX}, PDPClass.SPECIFIC),
    FileCategory.VIDEO: ({mime.MP4}, PDPClass.SPECIFIC),
    FileCategory.CLINICAL_IMAGE: ({mime.JPEG, mime.PNG}, PDPClass.SPECIFIC),
}


@dataclass
class DownloadResult:
    content: bytes
    mime_type: str
    original_name: str
    sha256: bytes


# helpers

def _as_response(row: Files) -> FileResponse:
    return FileResponse(
        id=row.id,
        patient_id=row.patient_id,
        original_name=file_crypto.open_name(row.original_name_encrypted),
        category=row.category,
        pdp_class=row.pdp_class,
        mime_type=row.mime_type,
        size_bytes=row.size_bytes,
        sha256=row.sha256_plain.hex(),
        algorithm=row.algorithm,
        shareable=row.category == FileCategory.CLINICAL_IMAGE,
        created_at=row.created_at,
    )


def _owned_patient(db: Session, user: User, patient_id: UUID) -> Patients:
    patient = patient_repository.get_owned(db, patient_id, user.id)
    if patient is None:
        # Same 404 as "does not exist": never reveal another account's ids (F-07).
        raise NotFoundError("Patient not found")
    return patient


def _owned_file(db: Session, user: User, file_id: UUID) -> Files:
    row = file_repository.get_owned(db, file_id, user.id)
    if row is None:
        raise NotFoundError(FILE_NOT_FOUND)
    return row


async def _read_limited(upload, limit: int = MAX_FILE_BYTES) -> bytes:
    """Read the upload in chunks, refusing anything over the limit or empty."""
    total = 0
    chunks: list[bytes] = []
    while chunk := await upload.read(CHUNK_SIZE):
        total += len(chunk)
        if total > limit:
            raise FileTooLargeError(limit)
        chunks.append(chunk)
    return b"".join(chunks)


def _dek_and_mac(row: Files) -> tuple[bytes, bytes | None]:
    dek = unwrap_key(row.dek_wrapped)
    mac_key = unwrap_key(row.mac_key_wrapped) if row.mac_key_wrapped else None
    return dek, mac_key


def decrypt_verified(row: Files) -> bytes:
    """Fetch the object, verify tag + SHA-256, and return the plaintext.

    Everything is checked before any byte is handed to the client.
    """
    try:
        blob = storage.get_object(row.storage_key)
    except NotFoundError:
        logger.warning("Object missing for file %s (%s)", row.id, row.storage_key)
        raise NotFoundError(FILE_NOT_FOUND) from None

    dek, mac_key = _dek_and_mac(row)
    aad = file_crypto.build_aad(row.owner_id, row.id)

    try:
        plaintext = file_crypto.decrypt(row.algorithm, blob, dek, aad, mac_key)
    except IntegrityError:
        # The object failed its own authentication. If its stored tag also differs
        # from the row, this is a different (validly sealed) object -> 409; a flipped
        # byte inside a matching object stays a 422.
        if not hmac.compare_digest(file_crypto.object_tag(blob), row.auth_tag):
            logger.warning("SIA1 tag differs from files.auth_tag for file %s", row.id)
            raise ConflictError("File integrity check failed") from None
        logger.warning("Cipher verification failed for file %s", row.id)
        raise IntegrityError(INTEGRITY_MESSAGE) from None

    digest = hashlib.sha256(plaintext).digest()
    if not hmac.compare_digest(digest, row.sha256_plain):
        logger.warning("SHA-256 mismatch for file %s", row.id)
        raise IntegrityError(INTEGRITY_MESSAGE)
    return plaintext


# ---------- use cases ----------


async def upload(
    db: Session, user: User, patient_id: UUID, form: FileUploadRequest, upload_file
) -> FileResponse:
    patient = _owned_patient(db, user, patient_id)

    content = await _read_limited(upload_file)
    if not content:
        # A 0-byte upload is a validation problem, not an unsupported type.
        raise RequestValidationError([{"loc": ("body", "file"), "msg": "File is empty",
                                       "type": "value_error.empty_file"}])

    detected = mime.sniff_mime(content)
    allowed, pdp_class = CATEGORY_RULES[form.category]
    if detected not in allowed:
        raise UnsupportedFileTypeError(
            form.category.value, detected, sorted(allowed)
        )

    algorithm = CIPHER_ALGORITHM[form.cipher]
    file_id = uuid4()
    aad = file_crypto.build_aad(user.id, file_id)
    dek = file_crypto.new_dek(algorithm)
    mac_key = file_crypto.new_mac_key(algorithm)
    encrypted = file_crypto.encrypt(algorithm, content, dek, aad, mac_key)

    storage_key = storage.archive_key(file_id)
    # Store first: a failure here must not leave a row behind.
    storage.put_object(storage_key, encrypted.blob)

    row = Files(
        id=file_id,
        # owner is copied from the patient, never from the client.
        owner_id=patient.owner_id,
        patient_id=patient.id,
        category=form.category,
        pdp_class=pdp_class,
        mime_type=detected,
        size_bytes=len(content),
        original_name_encrypted=file_crypto.seal_name(upload_file.filename or "file"),
        sha256_plain=hashlib.sha256(content).digest(),
        algorithm=algorithm,
        format_version=1,
        iv=encrypted.iv,
        auth_tag=encrypted.tag,
        dek_wrapped=wrap_key(dek),
        mac_key_wrapped=wrap_key(mac_key) if mac_key else None,
        storage_key=storage_key,
    )

    try:
        file_repository.create(db, row)
        activity_repository.record(
            db, action=ActivityAction.UPLOAD, user_id=user.id, file_id=file_id
        )
        db.commit()
    except Exception:
        db.rollback()
        # The object was already written; drop it so no orphan remains.
        try:
            storage.delete_objects([storage_key])
        except Exception:
            logger.exception("Failed to clean up object %s after a failed commit", storage_key)
        raise

    db.refresh(row)
    return _as_response(row)


def get(db: Session, user: User, file_id: UUID) -> FileResponse:
    # Metadata only: no object storage call, no activity_logs row.
    return _as_response(_owned_file(db, user, file_id))


def download(db: Session, user: User, file_id: UUID) -> DownloadResult:
    row = _owned_file(db, user, file_id)
    content = decrypt_verified(row)

    activity_repository.record(
        db, action=ActivityAction.DOWNLOAD, user_id=user.id, file_id=row.id
    )
    db.commit()

    return DownloadResult(
        content=content,
        mime_type=row.mime_type,
        original_name=file_crypto.open_name(row.original_name_encrypted),
        sha256=row.sha256_plain,
    )


def repr_digest(sha256: bytes) -> str:
    """RFC 9530 Repr-Digest header value."""
    return f"sha-256=:{base64.b64encode(sha256).decode()}:"
