from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models
from app.core.handlers import register_exception_handlers
from app.core.middleware import request_logging_middleware
from app.routers import auth, files, health, logs, patients, stego

app = FastAPI()

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(auth.api_router)
app.include_router(patients.router)
app.include_router(files.router)
app.include_router(logs.router)
app.include_router(stego.router)

app.middleware("http")(request_logging_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://siarsip-fe.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
