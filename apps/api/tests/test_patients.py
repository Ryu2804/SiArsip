"""Tests for the /patients CRUD contract (SIA-53).

Every test runs against the real PostgreSQL schema through the ``client`` fixture,
inside a transaction that is rolled back afterwards.
"""

import uuid
from datetime import date, timedelta

import jwt
import pytest
from sqlalchemy import select

from app.core.config import ALGORITHM, SECRET_KEY
from app.core.security import hash_password
from app.models.files import Files
from app.models.patients import Patients
from app.models.user import User
from app.schemas.errors.common_error import StorageError
from app.services import storage

pytestmark = pytest.mark.usefixtures("client")

PATIENTS_URL = "/patients"

VALID_BODY = {
    "name": "Siti Rahmawati",
    "mrn": "RM-2026-00123",
    "nik": "3201234567890001",
    "birth_date": "1988-04-12",
    "diagnosis": "Ulkus diabetikum kaki kanan",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(db_session, name: str | None = None) -> User:
    user = User(
        id=uuid.uuid4(),
        name=name or f"User {uuid.uuid4().hex[:8]}",
        email=f"u-{uuid.uuid4().hex[:10]}@example.com",
        password_hash=hash_password("rahasia-kuat-123"),
    )
    db_session.add(user)
    db_session.commit()
    return user


def _token(user: User) -> str:
    return jwt.encode(
        {
            "user_id": str(user.id),
            "iat": __import__("datetime").datetime.now(__import__("datetime").UTC),
            "exp": __import__("datetime").datetime.now(__import__("datetime").UTC)
            + timedelta(minutes=60),
        },
        SECRET_KEY,
        algorithm=str(ALGORITHM),
    )


def _auth(user: User) -> dict:
    return {"Authorization": f"Bearer {_token(user)}"}


def _create(client, user: User, body: dict | None = None):
    return client.post(PATIENTS_URL, json=body or VALID_BODY, headers=_auth(user))


@pytest.fixture
def user_a(db_session) -> User:
    return _make_user(db_session, "Owner A")


@pytest.fixture
def user_b(db_session) -> User:
    return _make_user(db_session, "Owner B")


@pytest.fixture
def patient_of_a(client, user_a) -> dict:
    response = _create(client, user_a)
    assert response.status_code == 201, response.text
    return response.json()["data"]


# ---------------------------------------------------------------------------
# [x] Create lalu get mengembalikan data yang sama persis
# ---------------------------------------------------------------------------


def test_create_then_get_returns_same_data(client, user_a):
    created = _create(client, user_a)
    assert created.status_code == 201
    data = created.json()["data"]

    fetched = client.get(f"{PATIENTS_URL}/{data['id']}", headers=_auth(user_a))
    assert fetched.status_code == 200

    fetched_data = fetched.json()["data"]
    for field in ("id", "name", "mrn", "nik", "birth_date", "diagnosis"):
        assert fetched_data[field] == data[field]


def test_create_envelope_shape(client, user_a):
    body = _create(client, user_a).json()
    assert body["success"] is True
    assert body["message"] == "Patient created"
    assert body["meta"] is None
    assert set(body["data"]) == {
        "id", "name", "mrn", "nik", "birth_date", "diagnosis", "created_at", "updated_at",
    }


def test_create_with_optional_fields_absent(client, user_a):
    response = _create(client, user_a, {"name": "Tanpa NIK", "mrn": "RM-1"})
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["nik"] is None
    assert data["birth_date"] is None
    assert data["diagnosis"] is None


# ---------------------------------------------------------------------------
# [x] Kolom data_encrypted tidak memuat plaintext
# ---------------------------------------------------------------------------


def test_encrypted_column_contains_no_plaintext(client, db_session, user_a):
    _create(client, user_a)

    row = db_session.scalar(select(Patients).where(Patients.owner_id == user_a.id))
    assert row is not None
    blob = row.data_encrypted

    for secret in (
        VALID_BODY["name"].encode(),
        VALID_BODY["mrn"].encode(),
        VALID_BODY["nik"].encode(),
        VALID_BODY["diagnosis"].encode(),
    ):
        assert secret not in blob

    # The cleartext fields live only in the ciphertext, never as columns.
    assert len(row.dek_wrapped) == 12 + 32 + 16  # nonce + wrapped DEK + GCM tag
    assert len(row.data_nonce) == 12


# ---------------------------------------------------------------------------
# [x] Dua kali update menghasilkan data_nonce berbeda
# ---------------------------------------------------------------------------


def test_two_updates_use_different_nonce(client, db_session, user_a, patient_of_a):
    patient_id = patient_of_a["id"]

    first = client.put(
        f"{PATIENTS_URL}/{patient_id}",
        json={**VALID_BODY, "diagnosis": "update 1"},
        headers=_auth(user_a),
    )
    assert first.status_code == 200
    db_session.expire_all()
    nonce_1 = db_session.scalar(
        select(Patients.data_nonce).where(Patients.id == uuid.UUID(patient_id))
    )

    second = client.put(
        f"{PATIENTS_URL}/{patient_id}",
        json={**VALID_BODY, "diagnosis": "update 2"},
        headers=_auth(user_a),
    )
    assert second.status_code == 200
    db_session.expire_all()
    nonce_2 = db_session.scalar(
        select(Patients.data_nonce).where(Patients.id == uuid.UUID(patient_id))
    )

    assert nonce_1 != nonce_2
    assert second.json()["data"]["diagnosis"] == "update 2"


def test_put_replaces_omitted_optional_fields_with_null(client, user_a, patient_of_a):
    response = client.put(
        f"{PATIENTS_URL}/{patient_of_a['id']}",
        json={"name": "Nama Baru", "mrn": "RM-9"},
        headers=_auth(user_a),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["nik"] is None
    assert data["diagnosis"] is None


# ---------------------------------------------------------------------------
# [x] Daftar hanya milik user A, terbaru dulu, meta.total benar
# ---------------------------------------------------------------------------


def test_list_is_owner_scoped_newest_first(client, db_session, user_a, user_b):
    a_first = _create(client, user_a, {**VALID_BODY, "name": "A satu"}).json()["data"]
    a_second = _create(client, user_a, {**VALID_BODY, "name": "A dua"}).json()["data"]
    _create(client, user_b, {**VALID_BODY, "name": "B satu"})

    # Make ordering deterministic regardless of timestamp resolution.
    db_session.execute(
        Patients.__table__.update()
        .where(Patients.id == uuid.UUID(a_first["id"]))
        .values(created_at="2020-01-01T00:00:00+00:00")
    )
    db_session.commit()

    response = client.get(PATIENTS_URL, headers=_auth(user_a))
    assert response.status_code == 200
    body = response.json()

    names = [item["name"] for item in body["data"]]
    assert names == ["A dua", "A satu"]
    assert body["meta"] == {"page": 1, "size": 20, "total": 2}


def test_list_pagination(client, user_a):
    for i in range(3):
        _create(client, user_a, {**VALID_BODY, "name": f"Pasien {i}"})

    page_1 = client.get(f"{PATIENTS_URL}?page=1&size=2", headers=_auth(user_a)).json()
    page_2 = client.get(f"{PATIENTS_URL}?page=2&size=2", headers=_auth(user_a)).json()
    beyond = client.get(f"{PATIENTS_URL}?page=9&size=2", headers=_auth(user_a)).json()

    assert len(page_1["data"]) == 2
    assert len(page_2["data"]) == 1
    assert page_1["meta"]["total"] == 3
    assert beyond["data"] == []


# ---------------------------------------------------------------------------
# [x] Daftar mengirim nik_masked, tidak pernah nik lengkap
# ---------------------------------------------------------------------------


def test_list_masks_nik_and_hides_diagnosis(client, user_a, patient_of_a):
    body = client.get(PATIENTS_URL, headers=_auth(user_a)).json()
    item = body["data"][0]

    assert item["nik_masked"] == "3201********0001"
    assert "nik" not in item
    assert "diagnosis" not in item
    assert VALID_BODY["nik"] not in str(body)


# ---------------------------------------------------------------------------
# [x] User B mendapat 404 di GET, PUT, DELETE milik user A
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_foreign_patient_is_404(client, user_b, patient_of_a, method):
    url = f"{PATIENTS_URL}/{patient_of_a['id']}"
    kwargs = {"headers": _auth(user_b)}
    if method == "put":
        kwargs["json"] = VALID_BODY

    response = getattr(client, method)(url, **kwargs)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_unknown_patient_is_same_404(client, user_a):
    response = client.get(f"{PATIENTS_URL}/{uuid.uuid4()}", headers=_auth(user_a))
    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Patient not found"


# ---------------------------------------------------------------------------
# [x] Tanpa token / token kedaluwarsa -> 401 unauthorized
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method", ["get", "post", "put", "delete"])
def test_missing_token_is_401(client, method):
    url = PATIENTS_URL if method in ("get", "post") else f"{PATIENTS_URL}/{uuid.uuid4()}"
    kwargs = {"json": VALID_BODY} if method in ("post", "put") else {}
    response = getattr(client, method)(url, **kwargs)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_expired_token_is_401(client, user_a):
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"user_id": str(user_a.id), "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1)},
        SECRET_KEY,
        algorithm=str(ALGORITHM),
    )
    response = client.get(PATIENTS_URL, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


# ---------------------------------------------------------------------------
# [x] Validasi 422
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "body"),
    [
        ("nik_15_digits", {**VALID_BODY, "nik": "320123456789000"}),
        ("mrn_empty", {**VALID_BODY, "mrn": ""}),
        ("name_empty", {**VALID_BODY, "name": "   "}),
        (
            "birth_date_future",
            {**VALID_BODY, "birth_date": (date.today() + timedelta(days=1)).isoformat()},
        ),
        ("unknown_field_owner_id", {**VALID_BODY, "owner_id": str(uuid.uuid4())}),
    ],
)
def test_invalid_body_is_422(client, user_a, label, body):
    response = _create(client, user_a, body)
    assert response.status_code == 422, f"{label}: {response.text}"
    assert response.json()["error"]["code"] == "validation_error"


def test_invalid_patient_id_is_422(client, user_a):
    response = client.get(f"{PATIENTS_URL}/not-a-uuid", headers=_auth(user_a))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize("query", ["page=0", "size=0", "size=101"])
def test_invalid_pagination_is_422(client, user_a, query):
    response = client.get(f"{PATIENTS_URL}?{query}", headers=_auth(user_a))
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# [x] Mengubah satu byte ciphertext -> 422 integrity_failed
# ---------------------------------------------------------------------------


def test_tampered_ciphertext_is_422_integrity_failed(client, db_session, user_a, patient_of_a):
    row = db_session.scalar(select(Patients).where(Patients.id == uuid.UUID(patient_of_a["id"])))
    tampered = bytearray(row.data_encrypted)
    tampered[0] ^= 0x01
    row.data_encrypted = bytes(tampered)
    db_session.commit()

    response = client.get(f"{PATIENTS_URL}/{patient_of_a['id']}", headers=_auth(user_a))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "integrity_failed"


# ---------------------------------------------------------------------------
# [x] Delete menghapus file pasien dan memanggil storage untuk setiap key
# ---------------------------------------------------------------------------


def test_delete_removes_files_and_calls_storage(
    client, db_session, user_a, patient_of_a, monkeypatch
):
    deleted: list[str] = []
    monkeypatch.setattr(storage, "delete_objects", deleted.extend)

    for key in ("archives/a.bin", "archives/b.bin", "archives/c.bin"):
        db_session.add(
            Files(
                id=uuid.uuid4(),
                owner_id=user_a.id,
                patient_id=uuid.UUID(patient_of_a["id"]),
                category="identity_scan",
                pdp_class="specific",
                mime_type="application/pdf",
                size_bytes=10,
                original_name_encrypted=b"n",
                sha256_plain=b"0" * 32,
                algorithm="aes-gcm",
                format_version=1,
                iv=b"i" * 12,
                auth_tag=b"t" * 16,
                dek_wrapped=b"dek",
                storage_key=key,
            )
        )
    db_session.commit()

    response = client.delete(f"{PATIENTS_URL}/{patient_of_a['id']}", headers=_auth(user_a))

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Patient deleted"
    assert body["data"] == {"id": patient_of_a["id"], "deleted_files": 3}

    assert sorted(deleted) == ["archives/a.bin", "archives/b.bin", "archives/c.bin"]

    db_session.expire_all()
    assert db_session.scalar(
        select(Files).where(Files.patient_id == uuid.UUID(patient_of_a["id"]))
    ) is None
    assert db_session.scalar(
        select(Patients).where(Patients.id == uuid.UUID(patient_of_a["id"]))
    ) is None


def test_delete_succeeds_when_storage_fails(client, user_a, patient_of_a, monkeypatch):
    def boom(_keys):
        raise StorageError("bucket down")

    monkeypatch.setattr(storage, "delete_objects", boom)

    response = client.delete(f"{PATIENTS_URL}/{patient_of_a['id']}", headers=_auth(user_a))
    assert response.status_code == 200
    assert response.json()["data"]["deleted_files"] == 0


# ---------------------------------------------------------------------------
# [x] Ciphertext pasien A disalin ke baris pasien B gagal didekripsi (AAD)
# ---------------------------------------------------------------------------


def test_ciphertext_copied_to_another_patient_fails(client, db_session, user_a):
    first = _create(client, user_a, {**VALID_BODY, "name": "Pasien A"}).json()["data"]
    second = _create(client, user_a, {**VALID_BODY, "name": "Pasien B"}).json()["data"]

    row_a = db_session.scalar(select(Patients).where(Patients.id == uuid.UUID(first["id"])))
    row_b = db_session.scalar(select(Patients).where(Patients.id == uuid.UUID(second["id"])))
    row_b.data_encrypted = row_a.data_encrypted
    row_b.data_nonce = row_a.data_nonce
    db_session.commit()

    response = client.get(f"{PATIENTS_URL}/{second['id']}", headers=_auth(user_a))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "integrity_failed"


def test_ciphertext_copied_across_users_fails(client, db_session, user_a, user_b):
    from_b = _create(client, user_b, {**VALID_BODY, "name": "Pasien B"}).json()["data"]
    from_a = _create(client, user_a, {**VALID_BODY, "name": "Pasien A"}).json()["data"]

    row_b = db_session.scalar(select(Patients).where(Patients.id == uuid.UUID(from_b["id"])))
    row_a = db_session.scalar(select(Patients).where(Patients.id == uuid.UUID(from_a["id"])))
    # Attacker B overwrites their own row with A's ciphertext.
    row_b.data_encrypted = row_a.data_encrypted
    row_b.data_nonce = row_a.data_nonce
    row_b.dek_wrapped = row_a.dek_wrapped
    db_session.commit()

    response = client.get(f"{PATIENTS_URL}/{from_b['id']}", headers=_auth(user_b))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "integrity_failed"
