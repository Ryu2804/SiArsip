from fastapi import FastAPI
from app.routers import health, auth
import app.models

app = FastAPI()

app.include_router(health.router)
app.include_router(auth.api_router, prefix="/auth", tags=["Authentication"])
