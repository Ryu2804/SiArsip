"""Tests for POST /stego/reveal (SIA-122 / #43).

The image is embedded with the same helper used by ``share-image`` and the
password is the uploader's user id, so a reveal with another account must fail.
"""

import io
import json
import uuid

import numpy as np
import pytest
from PIL import Image

from app.services import stego
from tests.test_files import bucket, upload  # noqa: F401 (fixture)
from tests.test_files import png_bytes as uploaded_png
from tests.test_patients import _auth, _create, _make_user

pytestmark = pytest.mark.usefixtures("client")

REVEAL_URL = "/stego/reveal"

IDENTITY = {
    "patient_id": str(uuid.uuid4()),
    "name": "Siti Rahmawati",
    "mrn": "RM-2026-00123",
    "birth_date": "1988-04-12",
    "diagnosis": "Ulkus diabetikum kaki kanan",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def png_bytes(size=(256, 256)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, (10, 200, 10)).save(buffer, format="PNG")
    return buffer.getvalue()


def jpeg_bytes(size=(256, 256)) -> bytes:
    # Noise gives the DCT embedding enough non-zero coefficients to hide a payload.
    rng = np.random.default_rng(42)
    pixels = rng.integers(0, 256, (size[1], size[0], 3), dtype=np.uint8)
    buffer = io.BytesIO()
    Image.fromarray(pixels).save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()


def embed_png(user, identity=None) -> bytes:
    message = json.dumps(identity or IDENTITY).encode("utf-8")
    return stego.embed_png_bytes(png_bytes(), message, str(user.id))


def embed_jpeg(user, identity=None) -> bytes:
    message = json.dumps(identity or IDENTITY).encode("utf-8")
    return stego.embed_jpg_bytes(jpeg_bytes(), message, str(user.id))


def reveal(client, user, content, filename="shared.png", content_type="image/png"):
    return client.post(
        REVEAL_URL,
        files={"file": (filename, content, content_type)},
        headers=_auth(user),
    )


@pytest.fixture
def alice(db_session):
    return _make_user(db_session, "Alice")


@pytest.fixture
def bob(db_session):
    return _make_user(db_session, "Bob")


# ---------------------------------------------------------------------------
# Auth & happy paths
# ---------------------------------------------------------------------------


def test_requires_auth(client):
    response = client.post(
        REVEAL_URL,
        files={"file": ("shared.png", png_bytes(), "image/png")},
    )
    assert response.status_code == 401


def test_reveal_png_returns_identity(client, alice):
    response = reveal(client, alice, embed_png(alice))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["data"] == IDENTITY


def test_reveal_jpeg_returns_identity(client, alice):
    response = reveal(
        client,
        alice,
        embed_jpeg(alice),
        filename="shared.jpg",
        content_type="image/jpeg",
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"] == IDENTITY


def test_magic_bytes_win_over_filename_and_content_type(client, alice):
    # A PNG named .jpg and sent as image/jpeg must still be detected as PNG.
    response = reveal(
        client,
        alice,
        embed_png(alice),
        filename="shared.jpg",
        content_type="image/jpeg",
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["mrn"] == IDENTITY["mrn"]


@pytest.mark.usefixtures("bucket")
def test_reveal_after_share_image_roundtrip(client, alice):
    """The real share-image output must decrypt with the owner's user id."""
    patient = _create(client, alice).json()["data"]
    uploaded = upload(client, alice, patient["id"], uploaded_png())
    assert uploaded.status_code == 201, uploaded.text
    file_id = uploaded.json()["data"]["id"]

    shared = client.post(f"/files/{file_id}/share-image", headers=_auth(alice))
    assert shared.status_code == 200, shared.text

    response = reveal(client, alice, shared.content)

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["patient_id"] == patient["id"]
    assert data["name"] == patient["name"]
    assert data["mrn"] == patient["mrn"]


# ---------------------------------------------------------------------------
# Failure notifications
# ---------------------------------------------------------------------------


def test_another_user_cannot_decrypt(client, alice, bob):
    response = reveal(client, bob, embed_png(alice))

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "reveal_failed"
    assert body["error"]["details"]["reason"] == "decryption"
    assert "decrypt" in body["error"]["message"].lower()


def test_plain_image_reports_no_hidden_data(client, alice):
    response = reveal(client, alice, png_bytes())

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "reveal_failed"
    assert body["error"]["details"]["reason"] == "no_data"


def test_malformed_payload_is_reported(client, alice):
    message = b"this is not json"
    content = stego.embed_png_bytes(png_bytes(), message, str(alice.id))

    response = reveal(client, alice, content)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "reveal_failed"
    assert body["error"]["details"]["reason"] == "malformed"


def test_corrupted_ciphertext_is_reported_as_decryption_failure(client, alice):
    # Flip one bit inside the ciphertext (header/salt/IV stay intact).
    content = embed_png(alice)
    pixels = np.array(Image.open(io.BytesIO(content)).convert("RGB"))
    flat = pixels.ravel()
    flat[300] ^= 1
    buffer = io.BytesIO()
    Image.fromarray(flat.reshape(pixels.shape)).save(buffer, format="PNG")

    response = reveal(client, alice, buffer.getvalue())

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "reveal_failed"
    assert body["error"]["details"]["reason"] in {"decryption", "malformed"}


def test_missing_identity_fields_are_malformed(client, alice):
    response = reveal(client, alice, embed_png(alice, {"name": "Only a name"}))

    assert response.status_code == 422
    assert response.json()["error"]["details"]["reason"] == "malformed"


def test_unsupported_image_type(client, alice):
    response = reveal(client, alice, b"%PDF-1.7\nnot an image", filename="x.pdf")

    assert response.status_code == 415
    body = response.json()
    assert body["error"]["code"] == "unsupported_image_type"


def test_empty_file_is_rejected(client, alice):
    response = reveal(client, alice, b"")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
