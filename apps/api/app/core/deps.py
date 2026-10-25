"""Shared FastAPI dependencies."""

from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_jwt_token
from app.db.database import get_db
from app.models.user import User
from app.repositories import user_repository
from app.core.security import InvalidTokenError, TokenExpiredError
from app.schemas.errors.common_error import UnauthorizedError

# auto_error=False so a missing header reaches us and is raised as UnauthorizedError
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the bearer token to a User, or raise 401 unauthorized."""
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Missing bearer token")

    try:
        payload = decode_jwt_token(credentials.credentials)
    except (TokenExpiredError, InvalidTokenError) as exc:
        raise UnauthorizedError(str(exc)) from None

    try:
        user_id = UUID(str(payload["user_id"]))
    except (KeyError, ValueError):
        raise UnauthorizedError("Invalid token") from None

    user = user_repository.get_user_by_id(db, user_id)
    if user is None:
        raise UnauthorizedError("Invalid token")
    return user
