import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError
from app.schemas.response import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


def error_response(status_code: int, code: str, message: str, details: dict | None = None):
    body = ErrorResponse(error=ErrorDetail(code=code, message=message, details=details or {}))
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


async def app_error_handler(request: Request, exc: AppError):
    return error_response(exc.status_code, exc.code, exc.message, exc.details)


async def http_error_handler(request: Request, exc: StarletteHTTPException):
    # e.g. 404 for unknown routes, 405 wrong method
    return error_response(exc.status_code, "http_error", str(exc.detail))


async def validation_error_handler(request: Request, exc: RequestValidationError):
    # bad request body / query params from Pydantic
    return error_response(
        422, "validation_error", "Invalid request", {"fields": jsonable_encoder(exc.errors())}
    )


async def unhandled_error_handler(request: Request, exc: Exception):
    # log the real cause, never send it to the client
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return error_response(500, "internal_error", "Internal server error")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
