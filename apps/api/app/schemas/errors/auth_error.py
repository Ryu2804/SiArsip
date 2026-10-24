from app.schemas.exceptions import AppError

class EmailAlreadyRegisteredError(AppError):
    def __init__(self, email: str):
        self.email = email
        status = 400
        code = "email_already_registered"
        message = f"Email '{email}' is already registered."
        super().__init__(message=message, details={"email": email})
        
class UsernameAlreadyTakenError(AppError):
    def __init__(self, username: str):
        self.username = username
        status = 400
        code = "username_already_taken"
        message = f"Username '{username}' is already taken."
        super().__init__(message=message, details={"username": username})

class InvalidCredentialsError(AppError):
    def __init__(self):
        status = 401
        code = "invalid_credentials"
        message = "Invalid email or password."
        super().__init__(message=message)