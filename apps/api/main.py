from fastapi import FastAPI
from app.routers import health

app = FastAPI()

app.include_router(health.router, prefix="/health", tags=["Health"])

def get_db():
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()