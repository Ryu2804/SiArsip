from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.benchmark import BenchmarkRequest, BenchmarkResponse
from app.schemas.response import SuccessResponse, ok
from app.services import benchmark_service

router = APIRouter(prefix="/benchmark", tags=["Benchmark"])


@router.post("/run", response_model=SuccessResponse[BenchmarkResponse])
def run_benchmark(
    user: Annotated[User, Depends(get_current_user)],
    body: BenchmarkRequest | None = None,
):
    """Benchmark AES-GCM, DES-CBC, and RC4 with the same crypto path as uploads."""
    request = body or BenchmarkRequest()
    return ok(benchmark_service.run(request, user.id), message="Benchmark completed")
