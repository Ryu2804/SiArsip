"""Tests for POST /benchmark/run (SIA-131 / #46)."""

import pytest

from tests.test_patients import _auth, _make_user

pytestmark = pytest.mark.usefixtures("client")

BENCHMARK_URL = "/benchmark/run"


@pytest.fixture
def user(db_session):
    return _make_user(db_session, "Benchmarker")


def run_benchmark(client, user, body=None):
    return client.post(BENCHMARK_URL, json=body or {}, headers=_auth(user))


def test_requires_auth(client):
    response = client.post(BENCHMARK_URL, json={})
    assert response.status_code == 401


def test_body_is_optional(client, user):
    response = client.post(BENCHMARK_URL, headers=_auth(user))

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["size_bytes"] == 1024 * 1024
    assert data["iterations"] == 5


def test_runs_all_three_ciphers_with_defaults(client, user):
    response = run_benchmark(client, user)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True

    data = body["data"]
    assert data["size_bytes"] == 1024 * 1024
    assert data["iterations"] == 5
    assert [row["algorithm"] for row in data["results"]] == ["aes-gcm", "des-cbc", "rc4"]

    for row in data["results"]:
        assert row["size_bytes"] == data["size_bytes"]
        assert row["iterations"] == data["iterations"]
        assert row["encrypt_ms"] > 0
        assert row["decrypt_ms"] > 0
        assert row["encrypt_total_ms"] >= row["encrypt_ms"]
        assert row["decrypt_total_ms"] >= row["decrypt_ms"]
        assert row["total_ms"] > 0
        assert row["encrypt_mb_s"] > 0
        assert row["decrypt_mb_s"] > 0
        assert row["overhead_bytes"] > 0
        assert row["overhead_percent"] > 0
        assert row["verified"] is True
        assert row["tamper_detected"] is True


def test_accepts_custom_size_and_iterations(client, user):
    response = run_benchmark(client, user, {"size_bytes": 4096, "iterations": 2})

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["size_bytes"] == 4096
    assert data["iterations"] == 2
    assert all(
        row["size_bytes"] == 4096 and row["iterations"] == 2
        for row in data["results"]
    )


@pytest.mark.parametrize(
    "body",
    [
        {"size_bytes": 1023},
        {"size_bytes": 10 * 1024 * 1024 + 1},
        {"iterations": 0},
        {"iterations": 11},
        {"unknown_field": True},
    ],
)
def test_rejects_invalid_input(client, user, body):
    response = run_benchmark(client, user, body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
