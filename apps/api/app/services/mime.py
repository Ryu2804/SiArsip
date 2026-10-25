import io
import zipfile

PDF = "application/pdf"
JPEG = "image/jpeg"
PNG = "image/png"
MP4 = "video/mp4"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
UNKNOWN = "application/octet-stream"

ZIP_MAGIC = b"PK\x03\x04"


def sniff_mime(data: bytes) -> str:
    """Return the detected MIME type, or ``UNKNOWN`` when nothing matches."""
    if data.startswith(b"\xff\xd8\xff"):
        return JPEG
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return PNG
    if data.startswith(b"%PDF-"):
        return PDF
    # MP4: "ftyp" box at offset 4 (e.g. ....ftypisom / ....ftypmp42)
    if len(data) >= 12 and data[4:8] == b"ftyp":
        return MP4
    if data.startswith(ZIP_MAGIC):
        return _sniff_zip(data)
    return UNKNOWN


def _sniff_zip(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
    except (zipfile.BadZipFile, OSError):
        return UNKNOWN

    if any(name.startswith("word/") for name in names):
        return DOCX
    if any(name.startswith("xl/") for name in names):
        return XLSX
    return UNKNOWN


def is_image(mime: str) -> bool:
    return mime in (JPEG, PNG)
