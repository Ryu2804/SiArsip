from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.response import SuccessResponse, ok
from app.schemas.user import CreateUserRequest, LoginRequest, LoginResponse, UserResponse
from app.services.auth_service import login_user_service, register_user_service

api_router = APIRouter(prefix="/auth", tags=["Authentication"])


@api_router.post(
    "/register",
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
def register_router(
    payload: CreateUserRequest,
    db: Session = Depends(get_db),
):
    user = register_user_service(
        db=db,
        email=str(payload.email),
        name=payload.name,
        password=payload.password,
    )

    db.commit()
    db.refresh(user)

    return ok(UserResponse.model_validate(user), message="User registered")


@api_router.post(
    "/login",
    response_model=SuccessResponse[LoginResponse],
    status_code=status.HTTP_200_OK,
)
def login_router(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    res = login_user_service(
        db=db,
        email=str(payload.email),
        password=payload.password,
    )

    return ok(LoginResponse.model_validate(res), message="Login successful")
