from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.response import SuccessResponse, ok
from app.schemas.stego import StegoRevealResponse
from app.services import stego_service

router = APIRouter(prefix="/stego", tags=["Stego"])


@router.post("/reveal", response_model=SuccessResponse[StegoRevealResponse])
async def reveal_identity(
    file: Annotated[UploadFile, File()],
    user: Annotated[User, Depends(get_current_user)],
):
    """Decrypt the identity embedded in a shared PNG/JPEG using the current user's id."""
    return ok(await stego_service.reveal(user, file))
