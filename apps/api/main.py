from fastapi import FastAPI
from app.routers import auth, files, health, patients
import app.models
from app.core.handlers import register_exception_handlers
from app.core.middleware import request_logging_middleware

app = FastAPI()

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(auth.api_router)
app.include_router(patients.router)
app.include_router(files.router)

app.middleware("http")(request_logging_middleware)
