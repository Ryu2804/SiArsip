
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.services.auth_service import register_user_service, login_user_service
from app.schemas.response import ErrorResponse, SuccessResponse
from app.schemas.errors.auth_error import (
    EmailAlreadyRegisteredError,
    UsernameAlreadyTakenError,
    InvalidCredentialsError,
)
from app.schemas.user import UserResponse, CreateUserRequest, LoginResponse, LoginRequest
from app.db.database import get_db

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
    try:
        user = register_user_service(
            db=db,
            email=str(payload.email),
            name=payload.name,
            password=payload.password,
        )

        db.commit()
        db.refresh(user)

        return SuccessResponse[UserResponse](
            success=True,
            data=UserResponse.model_validate(user),
        )

    except (EmailAlreadyRegisteredError, UsernameAlreadyTakenError) as e:
        db.rollback()

        error_response = ErrorResponse(
            success=False,
            error={
                "code": e.code,
                "message": e.message,
                "details": e.details,
            },
        )

        return JSONResponse(
            status_code=e.status_code,
            content=error_response.model_dump(mode="json"),
        )

@api_router.post(
    "/login", 
    response_model=SuccessResponse[LoginResponse],
    status_code=status.HTTP_200_OK
    )
def login_router(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):

    try:
        res = login_user_service(
            db=db,
            email=str(payload.email),
            password=payload.password,
        )

        return SuccessResponse[LoginResponse](
            success=True,
            data=LoginResponse.model_validate(res),
        )

    except InvalidCredentialsError as e:
        error_response = ErrorResponse(
            success=False,
            error={
                "code": e.code,
                "message": e.message,
                "details": e.details,
            },
        )

        return JSONResponse(
            status_code=e.status_code,
            content=error_response.model_dump(mode="json"),
        )