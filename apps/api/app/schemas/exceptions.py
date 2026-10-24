
class AppError(Exception):
    """Base error for SiArsip.

    Raise subclasses from services, crypto, steganography, and storage.
    """

    status_code: int = 400
    code: str = "bad_request"

    def __init__(
        self,
        message: str = "Something went wrong",
        *,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict:
        """Serialize the exception into a consistent API error payload."""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }
