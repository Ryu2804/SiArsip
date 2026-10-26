"""Tests for GET /logs (SIA-107 / #39).

Every test runs against the real PostgreSQL schema through the ``client`` fixture,
inside a transaction that is rolled back afterwards.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.activity_logs import ActivityLogs
from app.models.enums import ActivityAction
from app.models.user import User

from tests.test_files import bucket, jpeg_bytes, upload  # noqa: F401 (fixtures)
from tests.test_patients import _auth, _create, _make_user

pytestmark = pytest.mark.usefixtures("client")

LOGS_URL = "/logs"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log(db_session, user: User, action: ActivityAction, *, file_id=None, at=None) -> ActivityLogs:
    entry = ActivityLogs(user_id=user.id, action=action, file_id=file_id)
    if at is not None:
        entry.created_at = at
    db_session.add(entry)
    db_session.commit()
    return entry

@pytest.fixture
def user_a(db_session) -> User:
    return _make_user(db_session, "Owner A")

@pytest.fixture
def user_b(db_session) -> User:
    return _make_user(db_session, "Owner B")

# ---------------------------------------------------------------------------
# List & isolation
# ---------------------------------------------------------------------------

def test_requires_auth(client):
    assert client.get(LOGS_URL).status_code == 401

def test_returns_only_own_entries(client, db_session, user_a, user_b):
    mine = _log(db_session, user_a, ActivityAction.UPLOAD)
    _log(db_session, user_b, ActivityAction.DOWNLOAD)

    response = client.get(LOGS_URL, headers=_auth(user_a))

    assert response.status_code == 200
    body = response.json()
    assert [row["id"] for row in body["data"]] == [mine.id]
    assert body["meta"] == {"page": 1, "size": 20, "total": 1}

def test_entry_shape_has_no_patient_identity(client, bucket, db_session, user_a):
    # Upload for real so file_id points at an existing file.
    patient = _create(client, user_a).json()["data"]
    file_id = upload(client, user_a, patient["id"], jpeg_bytes()).json()["data"]["id"]
    _log(db_session, user_a, ActivityAction.SHARE_IMAGE, file_id=uuid.UUID(file_id))

    row = client.get(LOGS_URL, headers=_auth(user_a)).json()["data"][0]

    assert set(row) == {"id", "action", "file_id", "created_at"}
    assert row["action"] == "share_image"
    assert row["file_id"] == file_id

def test_newest_first_and_paginated(client, db_session, user_a):
    now = datetime.now(timezone.utc)
    older = _log(db_session, user_a, ActivityAction.VIEW, at=now - timedelta(minutes=2))
    newer = _log(db_session, user_a, ActivityAction.DOWNLOAD, at=now - timedelta(minutes=1))

    page1 = client.get(LOGS_URL, params={"page": 1, "size": 1}, headers=_auth(user_a)).json()
    page2 = client.get(LOGS_URL, params={"page": 2, "size": 1}, headers=_auth(user_a)).json()

    assert [row["id"] for row in page1["data"]] == [newer.id]
    assert [row["id"] for row in page2["data"]] == [older.id]
    assert page1["meta"]["total"] == 2

def test_empty_log_returns_empty_list(client, user_a):
    body = client.get(LOGS_URL, headers=_auth(user_a)).json()
    assert body["data"] == []
    assert body["meta"]["total"] == 0

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

def test_filter_by_action(client, db_session, user_a):
    view = _log(db_session, user_a, ActivityAction.VIEW)
    _log(db_session, user_a, ActivityAction.DOWNLOAD)

    body = client.get(LOGS_URL, params={"action": "view"}, headers=_auth(user_a)).json()

    assert [row["id"] for row in body["data"]] == [view.id]
    assert body["meta"]["total"] == 1

def test_filter_by_date_range(client, db_session, user_a):
    now = datetime.now(timezone.utc)
    inside = _log(db_session, user_a, ActivityAction.UPLOAD, at=now - timedelta(hours=1))
    _log(db_session, user_a, ActivityAction.UPLOAD, at=now - timedelta(days=3))

    body = client.get(
        LOGS_URL,
        params={
            "date_from": (now - timedelta(days=1)).isoformat(),
            "date_to": now.isoformat(),
        },
        headers=_auth(user_a),
    ).json()

    assert [row["id"] for row in body["data"]] == [inside.id]

def test_invalid_action_is_rejected(client, user_a):
    response = client.get(LOGS_URL, params={"action": "hack"}, headers=_auth(user_a))
    assert response.status_code == 422

@pytest.mark.parametrize("params", [{"size": 0}, {"size": 101}, {"page": 0}])
def test_invalid_pagination_is_rejected(client, user_a, params):
    response = client.get(LOGS_URL, params=params, headers=_auth(user_a))
    assert response.status_code == 422
