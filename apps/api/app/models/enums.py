"""Enumerations shared by models and schemas.

Values (not member names) are what gets stored: every ``Enum(...)`` column passes
``values_callable=_enum_values`` so the database holds "aes-gcm", not "AES_GCM".
"""

import enum


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Persist member *values* ("aes-gcm"), not names ("AES_GCM")."""
    return [member.value for member in enum_cls]


class FileCategory(enum.StrEnum):
    """The four file data types from the PRD."""

    IDENTITY_SCAN = "identity_scan"  # KTP, BPJS: JPG/PNG/PDF
    OFFICE_DOCUMENT = "office_document"  # informed consent, referral: PDF/DOCX/XLSX
    VIDEO = "video"  # wound care, USG: MP4
    CLINICAL_IMAGE = "clinical_image"  # x-ray, wound photo: JPG/PNG (stego share)


class PDPClass(enum.StrEnum):
    """UU PDP Pasal 4: specific (health) vs general personal data."""

    SPECIFIC = "specific"
    GENERAL = "general"


class CipherAlgorithm(enum.StrEnum):
    AES_GCM = "aes-gcm"
    DES_CBC = "des-cbc"
    RC4 = "rc4"


class ActivityAction(enum.Enum):
    UPLOAD = "upload"
    DOWNLOAD = "download"
    VIEW = "view"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    SHARE_IMAGE = "share_image"
