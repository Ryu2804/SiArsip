"""Reveal the identity hidden in a shared clinical image.

``file_service.share_image`` encrypts the patient identity with the uploader's
user id as the password.  Reveal derives the same password from the *current*
user's id, so only the account that created the image can decrypt it.
"""

from fastapi.exceptions import RequestValidationError
from PIL import Image
from pydantic import ValidationError

from app.models.files import MAX_FILE_BYTES
from app.models.user import User
from app.schemas.errors.common_error import (
    FileTooLargeError,
    RevealError,
    UnsupportedImageError,
)
from app.schemas.stego import StegoRevealResponse
from app.services import stego

CHUNK_SIZE = 1024 * 1024


async def _read_limited(upload) -> bytes:
    """Read the upload in chunks, refusing anything over the limit."""
    total = 0
    chunks: list[bytes] = []
    while chunk := await upload.read(CHUNK_SIZE):
        total += len(chunk)
        if total > MAX_FILE_BYTES:
            raise FileTooLargeError(MAX_FILE_BYTES)
        chunks.append(chunk)
    return b"".join(chunks)


def _parse_identity(payload: bytes) -> StegoRevealResponse:
    """Parse the decrypted JSON; anything unexpected is a malformed payload."""
    try:
        return StegoRevealResponse.model_validate_json(payload)
    except (ValidationError, ValueError, TypeError):
        raise RevealError("malformed") from None


async def reveal(user: User, upload) -> StegoRevealResponse:
    content = await _read_limited(upload)
    if not content:
        raise RequestValidationError(
            [{"loc": ("body", "file"), "msg": "File is empty", "type": "value_error.empty_file"}]
        )

    if stego.detect_image_type(content) is None:
        raise UnsupportedImageError()

    # Same password as share_image: the uploader's user id, never the file id.
    try:
        payload = stego.extract_bytes(content, str(user.id))
    except stego.NoHiddenDataError:
        raise RevealError("no_data") from None
    except stego.DecryptionError:
        raise RevealError("decryption") from None
    except (ValueError, OSError, RuntimeError, Image.DecompressionBombError):
        # Corrupt image or an unreadable payload: the client gets a clear
        # "decryption failed" notification instead of a generic 500.
        raise RevealError("decryption") from None

    return _parse_identity(payload)
