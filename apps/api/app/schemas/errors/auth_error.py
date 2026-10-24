from app.schemas.exceptions import AppError

class EmailAlreadyRegisteredError(AppError):
    status_code = 400
    code = "email_already_registered"

    def __init__(self, email: str):
        self.email = email
        message = f"Email '{email}' is already registered."
        super().__init__(message=message, details={"email": email})

class UsernameAlreadyTakenError(AppError):
    status_code = 400
    code = "username_already_taken"

    def __init__(self, username: str):
        self.username = username
        message = f"Username '{username}' is already taken."
        super().__init__(message=message, details={"username": username})

class InvalidCredentialsError(AppError):
    status_code = 401
    code = "invalid_credentials"

    def __init__(self):
        message = "Invalid email or password."
        super().__init__(message=message)