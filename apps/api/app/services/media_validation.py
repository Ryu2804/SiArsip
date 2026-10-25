import io
import re
import zipfile

from app.schemas.errors.common_error import UnsupportedFileTypeError
from app.services import mime

# Signatures of native executables and scripts that must never be accepted.
_EXECUTABLE_SIGNATURES = (
    b"MZ",  # PE / DOS (Windows .exe, .dll)
    b"\x7fELF",  # Linux ELF
    b"\xfe\xed\xfa\xce",  # Mach-O 32-bit
    b"\xfe\xed\xfa\xcf",  # Mach-O 64-bit
    b"\xca\xfe\xba\xbe",  # Mach-O universal / Java class
    b"#!",  # shebang script
)

_OOXML_MAIN_PARTS = {
    mime.DOCX: "word/document.xml",
    mime.XLSX: "xl/workbook.xml",
}


def validate(data: bytes, category: str, detected: str, allowed: set[str]) -> None:
    """Raise UnsupportedFileTypeError unless `data` really is `detected`."""
    if detected not in allowed:
        raise UnsupportedFileTypeError(category, detected, sorted(allowed))

    if _has_executable(data):
        raise UnsupportedFileTypeError(category, detected, sorted(allowed))

    if detected in (mime.JPEG, mime.PNG):
        _validate_image(data, category, detected, allowed)
    elif detected == mime.PDF:
        _validate_pdf(data, category, detected, allowed)
    elif detected == mime.MP4:
        _validate_mp4(data, category, detected, allowed)
    elif detected in (mime.DOCX, mime.XLSX):
        _validate_ooxml(data, category, detected, allowed)


def _reject(category: str, detected: str, allowed: set[str]) -> None:
    raise UnsupportedFileTypeError(category, detected, sorted(allowed))


# .exe


def _has_executable(data: bytes) -> bool:
    if data.startswith(_EXECUTABLE_SIGNATURES):
        return True
    # Header-grafted executable: "%PDF-1.7\n...MZ..." or after a JPEG/PNG/MP4 header.
    body = data[2:] if data[:1] in (b"%", b"\xff", b"\x89", b"\x00") else data
    return b"MZ" in body[:4096]


# Images


def _validate_image(data: bytes, category: str, detected: str, allowed: set[str]) -> None:
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()  # parses headers/stream, does not decode pixels
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        _reject(category, detected, allowed)

    expected = {mime.JPEG: ("JPEG",), mime.PNG: ("PNG",)}[detected]
    try:
        with Image.open(io.BytesIO(data)) as image:
            actual = image.format
            # A real image must have usable dimensions.
            if image.width < 1 or image.height < 1:
                _reject(category, detected, allowed)
    except (UnidentifiedImageError, OSError):
        _reject(category, detected, allowed)

    if actual not in expected:
        _reject(category, detected, allowed)


# PDF


def _validate_pdf(data: bytes, category: str, detected: str, allowed: set[str]) -> None:
    if not data.startswith(b"%PDF-"):
        _reject(category, detected, allowed)
    # A PDF must end with %%EOF (allowing trailing whitespace/newlines).
    if not re.search(rb"%%EOF\s*$", data[-1024:]):
        _reject(category, detected, allowed)
    # Structural markers a viewer needs: an object, a catalog, xref or trailer.
    if not re.search(rb"\d+\s+\d+\s+obj", data):
        _reject(category, detected, allowed)
    if not re.search(rb"/(Type\s*/Catalog|Root\s+\d+\s+\d+\s+R)", data):
        _reject(category, detected, allowed)
    if b"xref" not in data and b"/XRef" not in data and b"startxref" not in data:
        _reject(category, detected, allowed)


# MP4


def _validate_mp4(data: bytes, category: str, detected: str, allowed: set[str]) -> None:
    boxes = _mp4_boxes(data, limit=len(data))
    types = [box for box, _, _ in boxes]
    if "ftyp" not in types or "moov" not in types:
        _reject(category, detected, allowed)
    # ftyp is required first; moov must be parseable (its own children readable).
    if types.index("ftyp") != 0:
        _reject(category, detected, allowed)
    start, end = next((s, e) for box, s, e in boxes if box == "moov")
    children = _mp4_boxes(data[start:end], limit=end - start)
    if not children:
        _reject(category, detected, allowed)


def _mp4_boxes(data: bytes, limit: int) -> list[tuple[str, int, int]]:
    """Top-level boxes as (type, payload_start, payload_end); stops on malformed input."""
    boxes: list[tuple[str, int, int]] = []
    offset = 0
    while offset + 8 <= limit:
        size = int.from_bytes(data[offset : offset + 4], "big")
        box_type = data[offset + 4 : offset + 8]
        if not box_type.isalnum() and box_type not in (b"ftyp", b"moov", b"mdat", b"free"):
            break
        if size == 1:  # 64-bit size
            if offset + 16 > limit:
                break
            size = int.from_bytes(data[offset + 8 : offset + 16], "big")
            header = 16
        elif size == 0:  # extends to end of file
            size, header = limit - offset, 8
        else:
            header = 8
        if size < header or offset + size > limit:
            break
        boxes.append((box_type.decode("latin-1"), offset + header, offset + size))
        offset += size
    return boxes


# OOXML (Office Open XML, e.g. DOCX/XLSX)


def _validate_ooxml(data: bytes, category: str, detected: str, allowed: set[str]) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = set(archive.namelist())
            if "[Content_Types].xml" not in names:
                _reject(category, detected, allowed)
            if _OOXML_MAIN_PARTS[detected] not in names:
                _reject(category, detected, allowed)
            # The package must not ship a native executable as a part.
            for name in names:
                info = archive.getinfo(name)
                if info.file_size > 512 * 1024:
                    continue
                if _has_executable(archive.read(name)):
                    _reject(category, detected, allowed)
            bad = archive.testzip()
            if bad is not None:
                _reject(category, detected, allowed)
    except (zipfile.BadZipFile, OSError, RuntimeError):
        _reject(category, detected, allowed)
