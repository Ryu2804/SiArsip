class AppError(Exception):
    """Base error for SiArsip. Raise subclasses from services, crypto, stego, storage."""

    status_code = 400
    code = "bad_request"

    def __init__(self, message: str = "Something went wrong", *, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class IntegrityError(AppError):
    """Ciphertext failed its GCM tag or HMAC check (tampered or wrong key)."""

    status_code = 422
    code = "integrity_failed"


class StorageError(AppError):
    """Bucket is unreachable or an object operation failed."""

    status_code = 503
    code = "storage_unavailable"
