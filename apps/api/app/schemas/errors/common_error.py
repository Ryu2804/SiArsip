
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
