class NotAuthorizedError(AppError):
    """Raised when the user is not authorized to access a resource."""
    status_code = 403
    error_code = "not_authorized"
    message = "You are not authorized to access this resource."

class PatientNotFoundError(AppError):
    """Raised when a patient is not found in the database."""
    status_code = 404
    error_code = "patient_not_found"
    message = "The requested patient was not found."

class PatientAlreadyExistsError(AppError):
    """Raised when trying to create a patient that already exists."""
    status_code = 400
    error_code = "patient_already_exists"
    message = "A patient with the given details already exists."

class IntegrityFieldError(AppError):
    """Raised when the provided patient data is invalid."""
    status_code = 422
    error_code = "invalid_patient_data"
    message = "The provided patient data is invalid."

