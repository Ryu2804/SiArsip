from fastAPI import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import SECRET_KEY