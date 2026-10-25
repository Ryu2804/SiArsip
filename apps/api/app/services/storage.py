"""Object-storage boundary.

Only the pieces the API needs are declared here. ``delete_objects`` is the seam
tests replace to assert which storage keys were removed, so the real client
(MinIO / S3) can be plugged in without touching the patient service.
"""

import logging
import os

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Object storage is unreachable or an operation failed."""


def delete_objects(storage_keys: list[str]) -> None:
    """Delete the given object keys from the archive bucket.

    Deliberately unimplemented: the project has no storage client yet (only
    STORAGE_PATH is configured). Callers must treat a failure as non-fatal.
    """
    raise StorageError(
        f"object storage is not configured; cannot delete {len(storage_keys)} key(s) "
        f"from STORAGE_PATH={os.getenv('STORAGE_PATH') or '<unset>'}"
    )
