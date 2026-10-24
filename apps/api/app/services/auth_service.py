from sqlalchemy.orm import Session
from datetime import datetime

from app.models.user import User
from app.repositories import user_repository
from app.core.security import hash_password, generate_jwt_token, verify_password
from app.schemas.errors.auth_error import InvalidCredentialsError
from app.schemas.errors.auth_error import (
    EmailAlreadyRegisteredError,
    UsernameAlreadyTakenError,
)


def register_user_service(
    db: Session,
    email: str,
    name: str,
    password: str,
) -> User:
    existing_user = user_repository.get_by_email(db, email)
    if existing_user:
        raise EmailAlreadyRegisteredError(email)

    existing_user = user_repository.get_by_username(db, name)
    if existing_user:
        raise UsernameAlreadyTakenError(name)

    new_user = User(
        email=email,
        name=name,
        password_hash=hash_password(password),
        stego_key_wrapped=None,
    )

    return user_repository.create_user(db, new_user)

def login_user_service(
    db: Session,
    email: str,
    password: str,
) -> tuple[User, str]:
    user = user_repository.get_by_email(db, email)

    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()

    token = generate_jwt_token(str(user.id))

    res = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "created_at": user.created_at,
        "jwt_token": token
    }
    return res