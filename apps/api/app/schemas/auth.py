
from app.schemas.exceptions import AppError


class EmailAlreadyRegisteredError(AppError):
    """Raised when a registration email is already in use."""

    status_code = 409
    code = "email_already_registered"

    def __init__(self, email: str) -> None:
        super().__init__(
            message=f"Email '{email}' is already registered.",
            details={"email": email},
        )
        self.email = email


class UsernameAlreadyTakenError(AppError):
    """Raised when a registration username is already in use."""

    status_code = 409
    code = "username_already_taken"

    def __init__(self, username: str) -> None:
        super().__init__(
            message=f"Username '{username}' is already taken.",
            details={"username": username},
        )
        self.username = username
