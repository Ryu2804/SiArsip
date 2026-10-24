from fastapi import APIRouter
from app.schemas.response import SuccessResponse

router = APIRouter()

@router.get(
    "/",
    response_model=SuccessResponse
)
async def health_check():
    return SuccessResponse(message="API is healthy")