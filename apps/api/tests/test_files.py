"""Tests for the /patients/{id}/files and /files endpoints (file contract).

Object storage is replaced by an in-memory fake so nothing leaves the machine; all
database work happens inside the rollback transaction from ``conftest.client``.
"""

import base64
import hashlib
import io
import uuid

import numpy as np
import pytest
from PIL import Image
from sqlalchemy import select

from app.models.activity_logs import ActivityLogs
from app.models.files import Files
from app.models.user import User
from app.services import storage

from tests.test_patients import VALID_BODY, _auth, _create, _make_user

pytestmark = pytest.mark.usefixtures("client")

UPLOAD_URL = "/patients/{patient_id}/files"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class FakeBucket:
    """In-memory replacement for the MinIO calls used by file_service."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.fail_writes = False

    def put_object(self, key, data, content_type="application/octet-stream"):
        if self.fail_writes:
            from app.schemas.errors.common_error import StorageError

            raise StorageError("bucket down")
        self.objects[key] = data

    def get_object(self, key):
        from app.schemas.errors.common_error import NotFoundError

        if key not in self.objects:
            raise NotFoundError("File not found")
        return self.objects[key]

    def delete_objects(self, keys):
        for key in keys:
            self.objects.pop(key, None)


@pytest.fixture
def bucket(monkeypatch) -> FakeBucket:
    fake = FakeBucket()
    monkeypatch.setattr(storage, "put_object", fake.put_object)
    monkeypatch.setattr(storage, "get_object", fake.get_object)
    monkeypatch.setattr(storage, "delete_objects", fake.delete_objects)
    return fake


@pytest.fixture
def alice(db_session) -> User:
    return _make_user(db_session, "Alice")


@pytest.fixture
def bob(db_session) -> User:
    return _make_user(db_session, "Bob")


@pytest.fixture
def alice_patient(client, alice) -> dict:
    response = _create(client, alice)
    assert response.status_code == 201
    return response.json()["data"]


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------


def jpeg_bytes(size=(64, 64)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(buffer, format="JPEG")
    return buffer.getvalue()


def png_bytes(size=(64, 64)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, (10, 200, 10)).save(buffer, format="PNG")
    return buffer.getvalue()


def pdf_bytes() -> bytes:
    return b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\ntrailer\n%%EOF\n"


def upload(client, user, patient_id, content, category="clinical_image", cipher=None,
           filename="luka-kaki-siti.jpg"):
    data = {"category": category}
    if cipher is not None:
        data["cipher"] = cipher
    return client.post(
        UPLOAD_URL.format(patient_id=patient_id),
        files={"file": (filename, content, "application/octet-stream")},
        data=data,
        headers=_auth(user),
    )


def activity_rows(db_session, file_id):
    return list(
        db_session.scalars(
            select(ActivityLogs).where(ActivityLogs.file_id == uuid.UUID(str(file_id)))
        )
    )


# ---------------------------------------------------------------------------
# [x] Upload -> download round trip for all three ciphers, with correct Repr-Digest
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cipher", ["aes", "des", "rc4"])
def test_roundtrip_each_cipher(client, bucket, alice, alice_patient, cipher):
    content = jpeg_bytes()
    created = upload(client, alice, alice_patient["id"], content, cipher=cipher)
    assert created.status_code == 201, created.text
    file_id = created.json()["data"]["id"]

    response = client.get(f"/files/{file_id}/download", headers=_auth(alice))

    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["content-length"] == str(len(content))
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "attachment;" in response.headers["content-disposition"]

    expected = base64.b64encode(hashlib.sha256(content).digest()).decode()
    assert response.headers["repr-digest"] == f"sha-256=:{expected}:"


# ---------------------------------------------------------------------------
# [x] No cipher -> aes-gcm
# ---------------------------------------------------------------------------


def test_default_cipher_is_aes(client, bucket, alice, alice_patient):
    created = upload(client, alice, alice_patient["id"], jpeg_bytes())
    assert created.status_code == 201
    assert created.json()["data"]["algorithm"] == "aes-gcm"


# ---------------------------------------------------------------------------
# [x] Object and original_name_encrypted hold no plaintext
# ---------------------------------------------------------------------------


def test_no_plaintext_in_object_or_name(client, bucket, db_session, alice, alice_patient):
    content = jpeg_bytes()
    created = upload(client, alice, alice_patient["id"], content, filename="rahasia-klinik.jpg")
    file_id = created.json()["data"]["id"]

    blob = bucket.objects[storage.archive_key(file_id)]
    row = db_session.scalar(select(Files).where(Files.id == uuid.UUID(file_id)))

    assert b"rahasia-klinik" not in blob
    assert b"rahasia-klinik" not in row.original_name_encrypted
    assert content not in blob
    assert content != blob
    assert row.original_name_encrypted != b"rahasia-klinik.jpg"
    # name is recoverable only through the key
    assert created.json()["data"]["original_name"] == "rahasia-klinik.jpg"


# ---------------------------------------------------------------------------
# [x] Column shape per cipher
# ---------------------------------------------------------------------------


def test_crypto_columns_per_cipher(client, bucket, db_session, alice, alice_patient):
    aes_id = upload(client, alice, alice_patient["id"], jpeg_bytes(), cipher="aes").json()["data"]["id"]
    rc4_id = upload(client, alice, alice_patient["id"], jpeg_bytes(), cipher="rc4").json()["data"]["id"]

    db_session.expire_all()
    aes_row = db_session.scalar(select(Files).where(Files.id == uuid.UUID(aes_id)))
    rc4_row = db_session.scalar(select(Files).where(Files.id == uuid.UUID(rc4_id)))

    assert len(aes_row.iv) == 12
    assert len(aes_row.auth_tag) == 16
    assert aes_row.mac_key_wrapped is None

    assert rc4_row.iv is None
    assert len(rc4_row.auth_tag) == 32
    assert rc4_row.mac_key_wrapped is not None


# ---------------------------------------------------------------------------
# [x] Magic-byte checks: PDF as clinical_image, and a .jpg that is really a PDF
# ---------------------------------------------------------------------------


def test_pdf_with_clinical_image_is_415(client, bucket, alice, alice_patient):
    response = upload(client, alice, alice_patient["id"], pdf_bytes())
    assert response.status_code == 415
    body = response.json()["error"]
    assert body["code"] == "unsupported_file_type"
    assert body["details"]["detected"] == "application/pdf"
    assert body["details"]["allowed"] == ["image/jpeg", "image/png"]


def test_pdf_disguised_as_jpg_is_415(client, bucket, alice, alice_patient):
    response = upload(
        client, alice, alice_patient["id"], pdf_bytes(), filename="looks-like.jpg"
    )
    assert response.status_code == 415
    assert response.json()["error"]["details"]["detected"] == "application/pdf"


# ---------------------------------------------------------------------------
# [x] Size limits
# ---------------------------------------------------------------------------


def test_upload_over_100mb_is_413(client, bucket, alice, alice_patient):
    oversized = b"\xff\xd8\xff" + b"0" * (100 * 1024 * 1024 + 1)
    response = upload(client, alice, alice_patient["id"], oversized)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_empty_upload_is_422(client, bucket, alice, alice_patient):
    response = upload(client, alice, alice_patient["id"], b"")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


# ---------------------------------------------------------------------------
# [x] Bad form values are 422
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "form",
    [
        {"category": "clinical_image", "cipher": "3des"},
        {"category": "not_a_category"},
        {"category": "clinical_image", "owner_id": "abc"},
        {"category": "clinical_image", "algorithm": "aes-gcm"},
    ],
)
def test_bad_form_is_422(client, bucket, alice, alice_patient, form):
    response = client.post(
        UPLOAD_URL.format(patient_id=alice_patient["id"]),
        files={"file": ("x.jpg", jpeg_bytes(), "image/jpeg")},
        data=form,
        headers=_auth(alice),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


# ---------------------------------------------------------------------------
# [x] Ownership: user B gets 404 everywhere on A's resources
# ---------------------------------------------------------------------------


def test_bob_cannot_upload_to_alice_patient(client, bucket, bob, alice_patient):
    response = upload(client, bob, alice_patient["id"], jpeg_bytes())
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize(
    "suffix", ["", "/download"]
)
def test_bob_cannot_read_alice_file(client, bucket, bob, alice, alice_patient, suffix):
    file_id = upload(client, alice, alice_patient["id"], jpeg_bytes()).json()["data"]["id"]

    response = client.get(f"/files/{file_id}{suffix}", headers=_auth(bob))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


# ---------------------------------------------------------------------------
# [x] 401 without token / with expired token
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("suffix", ["", "/download"])
def test_file_reads_require_token(client, bucket, alice, alice_patient, suffix):
    file_id = upload(client, alice, alice_patient["id"], jpeg_bytes()).json()["data"]["id"]
    response = client.get(f"/files/{file_id}{suffix}")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_upload_requires_token(client, bucket, alice_patient):
    response = client.post(
        UPLOAD_URL.format(patient_id=alice_patient["id"]),
        files={"file": ("x.jpg", jpeg_bytes(), "image/jpeg")},
        data={"category": "clinical_image"},
    )
    assert response.status_code == 401


def test_expired_token_is_401(client, bucket, alice, alice_patient):
    import jwt
    from datetime import datetime, timedelta, timezone

    from app.core.config import ALGORITHM, SECRET_KEY

    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"user_id": str(alice.id), "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1)},
        SECRET_KEY, algorithm=str(ALGORITHM),
    )
    file_id = upload(client, alice, alice_patient["id"], jpeg_bytes()).json()["data"]["id"]

    response = client.get(f"/files/{file_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


# ---------------------------------------------------------------------------
# [x] Metadata call: no storage, no secrets leaked
# ---------------------------------------------------------------------------


def test_metadata_does_not_touch_storage_or_leak_secrets(
    client, bucket, monkeypatch, alice, alice_patient
):
    file_id = upload(client, alice, alice_patient["id"], jpeg_bytes()).json()["data"]["id"]

    def explode(_key):
        raise AssertionError("GET metadata must not read object storage")

    monkeypatch.setattr(storage, "get_object", explode)

    response = client.get(f"/files/{file_id}", headers=_auth(alice))
    assert response.status_code == 200
    data = response.json()["data"]

    assert set(data) == {
        "id", "patient_id", "original_name", "category", "pdp_class",
        "mime_type", "size_bytes", "sha256", "algorithm", "shareable", "created_at",
    }
    text = str(data)
    for secret in ("owner_id", "storage_key", "format_version", "dek_wrapped",
                   "mac_key_wrapped", "auth_tag", '"iv"'):
        assert secret not in text


# ---------------------------------------------------------------------------
# [x] Tampering: one byte in the object -> 422 for all ciphers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cipher", ["aes", "des", "rc4"])
def test_flipped_byte_is_422(client, bucket, db_session, alice, alice_patient, cipher):
    """A byte flipped in the body keeps the tag intact -> integrity_failed (422)."""
    file_id = upload(client, alice, alice_patient["id"], jpeg_bytes(), cipher=cipher).json()["data"]["id"]
    db_session.expire_all()
    row = db_session.scalar(select(Files).where(Files.id == uuid.UUID(file_id)))

    key = storage.archive_key(file_id)
    blob = bytearray(bucket.objects[key])
    # Offset 20 sits inside the ciphertext for every cipher (5 header + <=12 IV).
    assert 20 < len(blob) - len(row.auth_tag)
    blob[20] ^= 0x01
    bucket.objects[key] = bytes(blob)

    response = client.get(f"/files/{file_id}/download", headers=_auth(alice))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "integrity_failed"


@pytest.mark.parametrize("cipher", ["aes", "des", "rc4"])
def test_flipped_tag_is_409(client, bucket, alice, alice_patient, cipher):
    """A byte flipped inside the trailing tag makes the object not match its row."""
    file_id = upload(client, alice, alice_patient["id"], jpeg_bytes(), cipher=cipher).json()["data"]["id"]

    key = storage.archive_key(file_id)
    blob = bytearray(bucket.objects[key])
    blob[-1] ^= 0x01
    bucket.objects[key] = bytes(blob)

    response = client.get(f"/files/{file_id}/download", headers=_auth(alice))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


# ---------------------------------------------------------------------------
# [x] sha256_plain changed in DB -> 422
# ---------------------------------------------------------------------------


def test_sha256_mismatch_is_422(client, bucket, db_session, alice, alice_patient):
    file_id = upload(client, alice, alice_patient["id"], jpeg_bytes()).json()["data"]["id"]
    row = db_session.scalar(select(Files).where(Files.id == uuid.UUID(file_id)))
    row.sha256_plain = hashlib.sha256(b"something else").digest()
    db_session.commit()

    response = client.get(f"/files/{file_id}/download", headers=_auth(alice))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "integrity_failed"


# ---------------------------------------------------------------------------
# [x] Swapped objects -> 409
# ---------------------------------------------------------------------------


def test_swapped_objects_is_409(client, bucket, alice, alice_patient):
    first = upload(client, alice, alice_patient["id"], jpeg_bytes()).json()["data"]["id"]
    second = upload(client, alice, alice_patient["id"], jpeg_bytes((80, 80))).json()["data"]["id"]

    k1, k2 = storage.archive_key(first), storage.archive_key(second)
    bucket.objects[k1], bucket.objects[k2] = bucket.objects[k2], bucket.objects[k1]

    response = client.get(f"/files/{first}/download", headers=_auth(alice))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


# ---------------------------------------------------------------------------
# [x] Storage down during upload -> 503 and no row
# ---------------------------------------------------------------------------


def test_storage_down_on_upload_is_503(client, bucket, db_session, alice, alice_patient):
    bucket.fail_writes = True
    before = len(list(db_session.scalars(select(Files))))

    response = upload(client, alice, alice_patient["id"], jpeg_bytes())

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "storage_unavailable"
    db_session.expire_all()
    assert len(list(db_session.scalars(select(Files)))) == before


# ---------------------------------------------------------------------------
# [x] activity_logs: success records one row, failures record none
# ---------------------------------------------------------------------------


def test_activity_logged_for_upload_and_download(
    client, bucket, db_session, alice, alice_patient
):
    file_id = upload(client, alice, alice_patient["id"], jpeg_bytes((128, 128))).json()["data"]["id"]
    client.get(f"/files/{file_id}/download", headers=_auth(alice))

    db_session.expire_all()
    actions = sorted(row.action.value for row in activity_rows(db_session, file_id))
    assert actions == ["download", "upload"]

    for row in activity_rows(db_session, file_id):
        assert row.user_id == alice.id


def test_failed_operations_log_nothing(client, bucket, db_session, alice, alice_patient):
    file_id = upload(client, alice, alice_patient["id"], jpeg_bytes()).json()["data"]["id"]
    db_session.expire_all()
    before = len(activity_rows(db_session, file_id))

    # corrupt the ciphertext body (tag untouched), then attempt a download
    key = storage.archive_key(file_id)
    blob = bytearray(bucket.objects[key]); blob[20] ^= 0x01
    bucket.objects[key] = bytes(blob)
    assert client.get(f"/files/{file_id}/download", headers=_auth(alice)).status_code == 422

    db_session.expire_all()
    assert len(activity_rows(db_session, file_id)) == before
