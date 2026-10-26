"""Benchmark the three SIA1 ciphers using the production file-crypto path.

Only the encrypt and decrypt calls are timed.  Payload creation, key
generation, the warm-up round, and the tamper check happen outside the timed
regions so the numbers reflect the cipher work itself.
"""

import os
import time
from uuid import UUID, uuid4

from app.models.enums import CipherAlgorithm
from app.schemas.benchmark import BenchmarkRequest, BenchmarkResponse, CipherBenchmark
from app.schemas.errors.common_error import IntegrityError
from app.services import file_crypto
from app.services.crypto.container import parse_container

ALGORITHMS = (
    CipherAlgorithm.AES_GCM,
    CipherAlgorithm.DES_CBC,
    CipherAlgorithm.RC4,
)


def _throughput_mb_s(size_bytes: int, iterations: int, elapsed_ns: int) -> float:
    seconds = max(elapsed_ns, 1) / 1_000_000_000
    return round(size_bytes * iterations / 1_000_000 / seconds, 2)


def _tamper_detected(
    algorithm: CipherAlgorithm,
    blob: bytes,
    dek: bytes,
    aad: bytes,
    mac_key: bytes | None,
) -> bool:
    """Flip one ciphertext byte and confirm the cipher rejects the object."""
    _, iv, ciphertext, _ = parse_container(blob)
    if not ciphertext:
        return False

    tampered = bytearray(blob)
    tampered[5 + len(iv) + len(ciphertext) // 2] ^= 0x01

    try:
        file_crypto.decrypt(algorithm, bytes(tampered), dek, aad, mac_key)
    except IntegrityError:
        return True
    return False


def _benchmark_cipher(
    algorithm: CipherAlgorithm,
    plaintext: bytes,
    aad: bytes,
    iterations: int,
) -> CipherBenchmark:
    # Warm-up: lazy Crypto imports and caches, excluded from the measurements.
    warm_dek = file_crypto.new_dek(algorithm)
    warm_mac_key = file_crypto.new_mac_key(algorithm)
    warm_blob = file_crypto.encrypt(algorithm, plaintext, warm_dek, aad, warm_mac_key).blob
    file_crypto.decrypt(algorithm, warm_blob, warm_dek, aad, warm_mac_key)

    encrypt_ns = 0
    decrypt_ns = 0
    verified = True
    blob = b""
    dek = b""
    mac_key: bytes | None = None

    for _ in range(iterations):
        # Fresh keys per round, as on upload; key generation is not timed.
        dek = file_crypto.new_dek(algorithm)
        mac_key = file_crypto.new_mac_key(algorithm)

        start = time.perf_counter_ns()
        blob = file_crypto.encrypt(algorithm, plaintext, dek, aad, mac_key).blob
        encrypt_ns += time.perf_counter_ns() - start

        start = time.perf_counter_ns()
        decrypted = file_crypto.decrypt(algorithm, blob, dek, aad, mac_key)
        decrypt_ns += time.perf_counter_ns() - start
        verified = verified and decrypted == plaintext

    overhead = len(blob) - len(plaintext)
    return CipherBenchmark(
        algorithm=algorithm,
        size_bytes=len(plaintext),
        iterations=iterations,
        encrypt_ms=round(encrypt_ns / iterations / 1_000_000, 3),
        decrypt_ms=round(decrypt_ns / iterations / 1_000_000, 3),
        encrypt_total_ms=round(encrypt_ns / 1_000_000, 3),
        decrypt_total_ms=round(decrypt_ns / 1_000_000, 3),
        total_ms=round((encrypt_ns + decrypt_ns) / 1_000_000, 3),
        encrypt_mb_s=_throughput_mb_s(len(plaintext), iterations, encrypt_ns),
        decrypt_mb_s=_throughput_mb_s(len(plaintext), iterations, decrypt_ns),
        overhead_bytes=overhead,
        overhead_percent=round(overhead / len(plaintext) * 100, 6),
        verified=verified,
        tamper_detected=_tamper_detected(algorithm, blob, dek, aad, mac_key),
    )


def run(request: BenchmarkRequest, owner_id: UUID) -> BenchmarkResponse:
    plaintext = os.urandom(request.size_bytes)
    aad = file_crypto.build_aad(owner_id, uuid4())

    results = [
        _benchmark_cipher(algorithm, plaintext, aad, request.iterations)
        for algorithm in ALGORITHMS
    ]

    return BenchmarkResponse(
        size_bytes=request.size_bytes,
        iterations=request.iterations,
        results=results,
    )
