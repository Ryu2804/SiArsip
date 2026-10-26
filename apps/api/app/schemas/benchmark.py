from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CipherAlgorithm

DEFAULT_SIZE_BYTES = 1024 * 1024  # 1 MiB
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MiB
DEFAULT_ITERATIONS = 5
MAX_ITERATIONS = 10


class BenchmarkRequest(BaseModel):
    """Optional body for POST /benchmark/run."""

    model_config = ConfigDict(extra="forbid")

    size_bytes: int = Field(
        DEFAULT_SIZE_BYTES,
        ge=1024,
        le=MAX_SIZE_BYTES,
        description="Plaintext size per operation, in bytes",
    )
    iterations: int = Field(
        DEFAULT_ITERATIONS,
        ge=1,
        le=MAX_ITERATIONS,
        description="Number of encrypt/decrypt rounds per cipher",
    )


class CipherBenchmark(BaseModel):
    """Timing and integrity result for one cipher."""

    algorithm: CipherAlgorithm
    size_bytes: int
    iterations: int

    # Average time per single encrypt/decrypt operation.
    encrypt_ms: float
    decrypt_ms: float

    # Total time spent across all iterations.
    encrypt_total_ms: float
    decrypt_total_ms: float
    total_ms: float

    encrypt_mb_s: float
    decrypt_mb_s: float

    overhead_bytes: int
    overhead_percent: float
    verified: bool
    tamper_detected: bool


class BenchmarkResponse(BaseModel):
    size_bytes: int
    iterations: int
    results: list[CipherBenchmark]
