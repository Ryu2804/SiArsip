from fastapi import APIRouter
from app.schemas.response import SuccessResponse

router = APIRouter()

@router.get(
    "/health",
    response_model=SuccessResponse
)
async def health_check():
    return SuccessResponse[dict](
        success=True,
        data={"status": "ok"}
    )