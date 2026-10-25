"""S3-compatible object storage (MinIO).

Configuration comes from the AWS_* variables in .env:

    AWS_ENDPOINT_URL_S3   e.g. http://localhost:9000
    AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY
    AWS_REGION

The bucket is derived from the endpoint's first path segment when present
(http://host/siarsip) or from BUCKET_NAME. Only the four operations the file
feature needs are exposed; tests replace them with an in-memory fake.
"""

import threading
from functools import lru_cache

from app.core.config import (
    AWS_ACCESS_KEY_ID,
    AWS_ENDPOINT_URL_S3,
    AWS_REGION_NAME,
    AWS_SECRET_ACCESS_KEY,
    BUCKET_NAME,
)
from app.schemas.errors.common_error import NotFoundError, StorageError

DEFAULT_BUCKET = "siarsip"
ARCHIVE_PREFIX = "archives"


def bucket_name() -> str:
    if BUCKET_NAME:
        return BUCKET_NAME
    if AWS_ENDPOINT_URL_S3:
        path = AWS_ENDPOINT_URL_S3.rstrip("/").split("/", 3)
        if len(path) == 4 and path[3]:
            return path[3]
    return DEFAULT_BUCKET


def archive_key(file_id) -> str:
    """Object key for a file: archives/<file_id>.bin."""
    return f"{ARCHIVE_PREFIX}/{file_id}.bin"


@lru_cache(maxsize=1)
def _client():
    if not AWS_ENDPOINT_URL_S3:
        raise StorageError("Object storage is not configured (AWS_ENDPOINT_URL_S3)")
    try:
        from minio import Minio
    except ImportError as exc: 
        raise StorageError("MinIO client is not installed") from exc

    endpoint = AWS_ENDPOINT_URL_S3.split("://", 1)[-1]
    secure = AWS_ENDPOINT_URL_S3.startswith("https://")
    endpoint = endpoint.split("/", 1)[0]
    try:
        return Minio(
            endpoint,
            access_key=AWS_ACCESS_KEY_ID,
            secret_key=AWS_SECRET_ACCESS_KEY,
            secure=secure,
            region=AWS_REGION_NAME or None,
        )
    except Exception as exc:
        raise StorageError("Object storage client could not be created") from exc


_bucket_lock = threading.Lock()


def _ensure_bucket(client) -> None:
    name = bucket_name()
    try:
        if not client.bucket_exists(name):
            with _bucket_lock:
                if not client.bucket_exists(name):
                    client.make_bucket(name)
    except StorageError:
        raise
    except Exception as exc:
        raise StorageError("Object storage is unreachable") from exc


def put_object(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    import io

    client = _client()
    _ensure_bucket(client)
    try:
        client.put_object(
            bucket_name(),
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
    except Exception as exc:
        raise StorageError("Failed to store object") from exc


def get_object(key: str) -> bytes:
    client = _client()
    try:
        response = client.get_object(bucket_name(), key)
    except Exception as exc:
        if getattr(exc, "code", "") in ("NoSuchKey", "NoSuchObject"):
            raise NotFoundError("Object not found") from None
        raise StorageError("Object storage is unreachable") from exc
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def delete_objects(storage_keys: list[str]) -> None:
    """Delete archive objects. Failures are reported as StorageError."""
    if not storage_keys:
        return
    client = _client()
    try:
        from minio.deleteobjects import DeleteObject

        errors = list(
            client.remove_objects(
                bucket_name(), [DeleteObject(key) for key in storage_keys]
            )
        )
    except Exception as exc:
        raise StorageError("Failed to delete objects") from exc
    if errors:
        raise StorageError("Some objects could not be deleted")


def is_configured() -> bool:
    return bool(AWS_ENDPOINT_URL_S3 and AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)


__all__ = [
    "archive_key",
    "bucket_name",
    "delete_objects",
    "get_object",
    "is_configured",
    "put_object",
]
