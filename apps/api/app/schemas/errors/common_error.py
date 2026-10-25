
from app.schemas.exceptions import AppError


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    status_code = 404
    code = "not_found"


class UnauthorizedError(AppError):
    """Raised when authentication is missing or invalid."""

    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    """Raised when the authenticated user lacks permission."""

    status_code = 403
    code = "forbidden"


class ConflictError(AppError):
    """Raised when a request conflicts with the current resource state."""

    status_code = 409
    code = "conflict"


class IntegrityError(AppError):
    """Raised when ciphertext or authenticated data fails integrity verification."""

    status_code = 422
    code = "integrity_failed"


class StorageError(AppError):
    """Raised when an object-storage operation fails or storage is unavailable."""

    status_code = 503
    code = "storage_unavailable"


class NotShareableError(AppError):
    """share-image asked for a file that is not a clinical image, or is too small for the payload."""

    status_code = 400
    code = "not_shareable"

    def __init__(self, reason: str) -> None:
        messages = {
            "category": "File is not shareable: only clinical images can be shared",
            "capacity": "Image is too small to carry the embedded identity",
        }
        super().__init__(messages.get(reason, "File is not shareable"), details={"reason": reason})


class FileTooLargeError(AppError):
    status_code = 413
    code = "file_too_large"

    def __init__(self, limit_bytes: int) -> None:
        super().__init__(
            "File exceeds the maximum allowed size",
            details={"limit_bytes": limit_bytes},
        )


class UnsupportedFileTypeError(AppError):
    """Magic bytes do not match a MIME type allowed for the chosen category."""

    status_code = 415
    code = "unsupported_file_type"

    def __init__(self, category: str, detected: str, allowed: list[str]) -> None:
        super().__init__(
            "File type not allowed for this category",
            details={"category": category, "detected": detected, "allowed": allowed},
        )
