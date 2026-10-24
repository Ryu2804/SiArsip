"""Tests for the /auth/register and /auth/login endpoints.

Each test runs against the real (PostgreSQL) schema inside a transaction that is
rolled back afterwards, so no data is persisted to the development database.
"""

import uuid

import jwt
import pytest
from sqlalchemy import func, select

from app.core.config import ALGORITHM, SECRET_KEY
from app.core.security import hash_password
from app.models.user import User

pytestmark = pytest.mark.usefixtures("client")

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:10]}@example.com"


def _unique_name() -> str:
    return f"User {uuid.uuid4().hex[:10]}"


def _register(client, payload: dict):
    return client.post(REGISTER_URL, json=payload)


def _login(client, email: str, password: str):
    return client.post(LOGIN_URL, json={"email": email, "password": password})


@pytest.fixture
def registered_user(client):
    payload = {
        "name": _unique_name(),
        "email": _unique_email(),
        "password": "rahasia-kuat-123",
    }
    response = _register(client, payload)
    assert response.status_code == 201, response.text
    return {**payload, "body": response.json()}


# ---------------------------------------------------------------------------
# Register - success
# ---------------------------------------------------------------------------


def test_register_creates_user(client, db_session):
    payload = {
        "name": _unique_name(),
        "email": _unique_email(),
        "password": "rahasia-kuat-123",
    }

    response = _register(client, payload)

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    data = body["data"]

    assert set(data) == {"id", "name", "email", "created_at"}
    assert data["name"] == payload["name"]
    assert data["email"] == payload["email"]
    assert uuid.UUID(data["id"])  # valid UUID serialized correctly
    assert "created_at" in data

    # Credentials must never be echoed back.
    assert "password" not in data
    assert "password_hash" not in data


def test_register_persists_user_with_hashed_password(client, db_session):
    payload = {
        "name": _unique_name(),
        "email": _unique_email(),
        "password": "rahasia-kuat-123",
    }

    response = _register(client, payload)
    assert response.status_code == 201

    user = db_session.scalar(select(User).where(User.email == payload["email"]))
    assert user is not None
    assert user.name == payload["name"]
    assert user.password_hash != payload["password"]
    # Argon2 hash format (pwdlib.recommended())
    assert user.password_hash.startswith("$argon2")
    assert user.stego_key_wrapped is None


def test_register_returns_unique_ids_for_distinct_users(client):
    first = _register(
        client,
        {"name": _unique_name(), "email": _unique_email(), "password": "password-123"},
    )
    second = _register(
        client,
        {"name": _unique_name(), "email": _unique_email(), "password": "password-123"},
    )

    assert first.status_code == second.status_code == 201
    assert first.json()["data"]["id"] != second.json()["data"]["id"]


# ---------------------------------------------------------------------------
# Register - conflicts
# ---------------------------------------------------------------------------


def test_register_duplicate_email_returns_400(client, registered_user):
    response = _register(
        client,
        {
            "name": _unique_name(),
            "email": registered_user["email"],
            "password": "password-lain-123",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "email_already_registered"
    assert registered_user["email"] in body["error"]["message"]
    assert body["error"]["details"] == {"email": registered_user["email"]}


def test_register_email_lookup_is_case_sensitive(client, registered_user):
    """Current behaviour: lookups are exact-match, so a cased variant is accepted.

    Pinned deliberately. If email handling is normalised (lowercased) later this
    test should flip to expect a 400 ``email_already_registered``.
    """
    mixed_case = registered_user["email"].upper()

    response = _register(
        client,
        {"name": _unique_name(), "email": mixed_case, "password": "password-123"},
    )

    assert response.status_code == 201
    # EmailStr lowercases the domain but preserves the local part.
    local, _, domain = mixed_case.partition("@")
    assert response.json()["data"]["email"] == f"{local}@{domain.lower()}"


def test_register_duplicate_email_does_not_create_second_row(
    client, db_session, registered_user
):
    count_before = db_session.scalar(select(func.count()).select_from(User))

    response = _register(
        client,
        {
            "name": _unique_name(),
            "email": registered_user["email"],
            "password": "password-lain-123",
        },
    )

    assert response.status_code == 400
    count_after = db_session.scalar(select(func.count()).select_from(User))
    assert count_after == count_before


def test_register_duplicate_name_returns_400(client, registered_user):
    """``users.name`` is enforced unique by the service, not by the DB schema."""
    response = _register(
        client,
        {
            "name": registered_user["name"],
            "email": _unique_email(),
            "password": "password-123",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "username_already_taken"
    assert body["error"]["details"] == {"username": registered_user["name"]}


# ---------------------------------------------------------------------------
# Register - validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "missing_field",
    ["name", "email", "password"],
)
def test_register_missing_required_field_returns_422(client, missing_field):
    payload = {
        "name": _unique_name(),
        "email": _unique_email(),
        "password": "password-123",
    }
    payload.pop(missing_field)

    response = _register(client, payload)

    assert response.status_code == 422
    locations = [err["loc"] for err in response.json()["detail"]]
    assert any(missing_field in loc for loc in locations)


@pytest.mark.parametrize("bad_email", ["not-an-email", "user@", "user@.com", "user @example.com"])
def test_register_invalid_email_returns_422(client, bad_email):
    response = _register(
        client,
        {"name": _unique_name(), "email": bad_email, "password": "password-123"},
    )

    assert response.status_code == 422
    assert any(
        err["loc"][-1] == "email" for err in response.json()["detail"]
    )


@pytest.mark.parametrize("short_password", ["", "abc", "1234567"])
def test_register_short_password_returns_422(client, short_password):
    response = _register(
        client,
        {"name": _unique_name(), "email": _unique_email(), "password": short_password},
    )

    assert response.status_code == 422
    assert any(
        err["loc"][-1] == "password" for err in response.json()["detail"]
    )


def test_register_password_too_long_returns_422(client):
    response = _register(
        client,
        {"name": _unique_name(), "email": _unique_email(), "password": "a" * 129},
    )

    assert response.status_code == 422
    assert any(err["loc"][-1] == "password" for err in response.json()["detail"])


@pytest.mark.parametrize("bad_name", ["", " " * 3])
def test_register_empty_name_returns_422(client, bad_name):
    response = _register(
        client, {"name": bad_name, "email": _unique_email(), "password": "password-123"}
    )

    assert response.status_code == 422
    assert any(err["loc"][-1] == "name" for err in response.json()["detail"])


def test_register_name_too_long_returns_422(client):
    response = _register(
        client,
        {"name": "n" * 256, "email": _unique_email(), "password": "password-123"},
    )

    assert response.status_code == 422
    assert any(err["loc"][-1] == "name" for err in response.json()["detail"])


# ---------------------------------------------------------------------------
# Login - success
# ---------------------------------------------------------------------------


def test_login_with_valid_credentials_returns_token(client, registered_user):
    response = _login(client, registered_user["email"], registered_user["password"])

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True

    data = body["data"]
    assert set(data) == {"id", "name", "email", "created_at", "jwt_token"}
    assert data["id"] == registered_user["body"]["data"]["id"]
    assert data["name"] == registered_user["name"]
    assert data["email"] == registered_user["email"]
    assert "password" not in data
    assert "password_hash" not in data


def test_login_jwt_token_is_valid_and_encodes_user_id(client, registered_user):
    response = _login(client, registered_user["email"], registered_user["password"])
    assert response.status_code == 200

    data = response.json()["data"]
    payload = jwt.decode(data["jwt_token"], SECRET_KEY, algorithms=[ALGORITHM])

    assert payload["user_id"] == data["id"]
    assert "iat" in payload and "exp" in payload
    assert payload["exp"] > payload["iat"]


def test_login_issues_consistent_tokens_for_same_user(client, registered_user):
    """Every login is stateless: repeated logins succeed and agree on the user id."""
    first = _login(client, registered_user["email"], registered_user["password"])
    second = _login(client, registered_user["email"], registered_user["password"])

    assert first.status_code == second.status_code == 200
    # Both tokens are valid and reference the same user.
    first_id = jwt.decode(
        first.json()["data"]["jwt_token"], SECRET_KEY, algorithms=[ALGORITHM]
    )["user_id"]
    second_id = jwt.decode(
        second.json()["data"]["jwt_token"], SECRET_KEY, algorithms=[ALGORITHM]
    )["user_id"]
    assert first_id == second_id == first.json()["data"]["id"]


# ---------------------------------------------------------------------------
# Login - failures
# ---------------------------------------------------------------------------


def test_login_wrong_password_returns_401(client, registered_user):
    response = _login(client, registered_user["email"], "password-yang-salah")

    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "invalid_credentials"
    assert body["error"]["message"] == "Invalid email or password."
    assert "jwt_token" not in body


def test_login_unknown_email_returns_401(client):
    response = _login(client, _unique_email(), "password-123")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_login_wrong_password_and_unknown_email_share_error(client, registered_user):
    """No user enumeration: both failure modes return an identical payload shape."""
    wrong_password = _login(client, registered_user["email"], "password-yang-salah")
    unknown_email = _login(client, _unique_email(), "password-yang-salah")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["error"]["code"] == unknown_email.json()["error"]["code"]
    assert wrong_password.json()["error"]["message"] == unknown_email.json()["error"]["message"]


def test_login_is_email_based_not_name_based(client, registered_user):
    """Passing the user's `name` in the email field must not authenticate."""
    response = _login(client, registered_user["name"], registered_user["password"])

    assert response.status_code == 422  # invalid email format rejected by validation


@pytest.mark.parametrize("missing_field", ["email", "password"])
def test_login_missing_required_field_returns_422(client, missing_field):
    payload = {"email": _unique_email(), "password": "password-123"}
    payload.pop(missing_field)

    response = client.post(LOGIN_URL, json=payload)

    assert response.status_code == 422
    assert any(
        missing_field in err["loc"] for err in response.json()["detail"]
    )


def test_login_invalid_email_format_returns_422(client):
    response = _login(client, "bukan-email", "password-123")

    assert response.status_code == 422


def test_login_short_password_returns_422(client, registered_user):
    """Request schema enforces min length before hitting the service."""
    response = _login(client, registered_user["email"], "short")

    assert response.status_code == 422


def test_login_with_hash_as_password_returns_401(client, db_session):
    """Sending the stored hash instead of the plaintext must not authenticate."""
    email = _unique_email()
    plain = "password-asli-123"
    db_session.add(
        User(email=email, name=_unique_name(), password_hash=hash_password(plain))
    )
    db_session.flush()

    stored = db_session.scalar(select(User).where(User.email == email))

    response = _login(client, email, stored.password_hash)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


# ---------------------------------------------------------------------------
# Full flow
# ---------------------------------------------------------------------------


def test_register_then_login_roundtrip(client):
    payload = {
        "name": _unique_name(),
        "email": _unique_email(),
        "password": "Kata-Sandi-Aman-9",
    }

    register_response = _register(client, payload)
    assert register_response.status_code == 201
    registered_id = register_response.json()["data"]["id"]

    login_response = _login(client, payload["email"], payload["password"])
    assert login_response.status_code == 200
    assert login_response.json()["data"]["id"] == registered_id


def test_repeated_registration_does_not_accumulate_rows(client, db_session):
    email = _unique_email()
    payload = {"name": _unique_name(), "email": email, "password": "password-123"}

    first = _register(client, payload)
    second = _register(client, payload)
    third = _register(client, payload)

    assert first.status_code == 201
    assert second.status_code == third.status_code == 400

    count = db_session.scalar(
        select(func.count()).select_from(User).where(User.email == email)
    )
    assert count == 1
