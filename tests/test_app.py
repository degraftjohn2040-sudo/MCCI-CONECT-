import time

import pytest
from fastapi.testclient import TestClient

from app.db import connection
from app.main import app
from app.security import ROLES, hash_password, token_hash

PASSWORD = "a-long-test-password"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MCCI_DATABASE", str(tmp_path / "test.sqlite3"))
    monkeypatch.setenv("MCCI_SECURE_COOKIES", "0")
    with TestClient(app) as client:
        with connection() as db:
            password_hash = hash_password(PASSWORD)
            for role in ROLES:
                db.execute(
                    "INSERT INTO users(email, password_hash, role) VALUES (?, ?, ?)",
                    (f"{role}@example.test", password_hash, role),
                )
        yield client


def login(client, role="owner", password=PASSWORD):
    return client.post(
        "/api/session",
        json={"email": f"{role}@example.test", "password": password},
        headers={"X-Requested-With": "MCCI-CONNECT"},
    )


def test_authentication_csrf_logout_and_audit(client):
    assert client.get("/api/members").status_code == 401
    assert client.post("/api/session", json={"email": "x@y", "password": "x"}).status_code == 403
    assert login(client, password="wrong").status_code == 401
    response = login(client)
    assert response.status_code == 200
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "samesite=strict" in response.headers["set-cookie"].lower()
    token = response.json()["csrf_token"]
    assert client.post("/api/members", json={"name": "Test"}).status_code == 403
    assert (
        client.post(
            "/api/members", json={"name": "Test"}, headers={"X-CSRF-Token": token}
        ).status_code
        == 201
    )
    actions = [row["action"] for row in client.get("/api/audit").json()["items"]]
    assert "member.created" in actions
    assert "session.login_failed" in actions
    assert client.delete("/api/session", headers={"X-CSRF-Token": token}).status_code == 204
    assert client.get("/api/session").status_code == 401


@pytest.mark.parametrize("role", ROLES)
def test_role_permissions(client, role):
    result = login(client, role)
    assert result.status_code == 200
    headers = {"X-CSRF-Token": result.json()["csrf_token"]}
    admin = role in {"owner", "admin", "super_admin"}
    reader = admin or role == "pastor"
    assert client.get("/api/announcements").status_code == 200
    assert client.get("/api/members").status_code == (200 if reader else 403)
    assert client.get("/api/attendance").status_code == (200 if reader else 403)
    assert client.get("/api/audit").status_code == (200 if admin else 403)
    for path, body in [
        ("members", {"name": "Example"}),
        ("announcements", {"title": "Hello", "body": "Update"}),
        ("attendance", {"event_name": "Service", "event_date": "2026-11-01", "headcount": 2}),
    ]:
        assert client.post(f"/api/{path}", json=body, headers=headers).status_code == (
            201 if admin else 403
        )


def test_validation_pagination_and_persistence(client):
    headers = {"X-CSRF-Token": login(client).json()["csrf_token"]}
    for name in ["Zoe", "Alice", "Beth"]:
        assert client.post("/api/members", json={"name": name}, headers=headers).status_code == 201
    first = client.get("/api/members?limit=2").json()
    assert [item["name"] for item in first["items"]] == ["Alice", "Beth"]
    assert first["has_more"] is True
    assert client.get("/api/members?limit=2&offset=2").json()["items"][0]["name"] == "Zoe"
    assert client.get("/api/members?limit=101").status_code == 422
    assert client.post("/api/members", json={"name": " "}, headers=headers).status_code == 422
    assert (
        client.post(
            "/api/attendance",
            json={"event_name": "Service", "event_date": "not-a-date", "headcount": -1},
            headers=headers,
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/announcements", json={"title": "Hi", "body": "ok", "extra": 1}, headers=headers
        ).status_code
        == 422
    )
    with connection() as db:
        assert db.execute("SELECT count(*) FROM members").fetchone()[0] == 3


def test_expired_and_disabled_sessions(client):
    login(client)
    token = client.cookies.get("mcci_session")
    with connection() as db:
        db.execute(
            "UPDATE sessions SET expires_at = ? WHERE token_hash = ?",
            (int(time.time()) - 1, token_hash(token)),
        )
    assert client.get("/api/session").status_code == 401
    login(client)
    with connection() as db:
        db.execute("UPDATE users SET active = 0 WHERE role = 'owner'")
    assert client.get("/api/session").status_code == 401


def test_login_rate_limit(client):
    for _ in range(10):
        assert login(client, password="wrong").status_code == 401
    assert login(client).status_code == 429


def test_security_headers(client, monkeypatch):
    monkeypatch.setenv("MCCI_SECURE_COOKIES", "1")
    response = login(client)
    assert "secure" in response.headers["set-cookie"].lower()
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_backup_is_consistent_and_never_overwrites(client, tmp_path):
    import sqlite3

    from app.backup import backup

    headers = {"X-CSRF-Token": login(client).json()["csrf_token"]}
    client.post("/api/members", json={"name": "Snapshot"}, headers=headers)
    destination = tmp_path / "snapshot.sqlite3"
    backup(destination)
    with sqlite3.connect(destination) as db:
        assert db.execute("SELECT name FROM members").fetchone()[0] == "Snapshot"
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    original = destination.read_bytes()
    with pytest.raises(FileExistsError):
        backup(destination)
    assert destination.read_bytes() == original


def test_password_whitespace_is_preserved(client):
    with connection() as db:
        db.execute(
            "UPDATE users SET password_hash = ? WHERE role = 'owner'",
            (hash_password("  padded password  "),),
        )
    assert login(client, password="  padded password  ").status_code == 200


def test_unknown_role_is_denied(client):
    login(client)
    with connection() as db:
        db.execute("UPDATE users SET role = 'unknown' WHERE role = 'owner'")
    assert client.get("/api/announcements").status_code == 401


def test_static_page_and_private_database(client, tmp_path):
    response = client.get("/")
    assert response.status_code == 200
    assert "MCCI CONNECT" in response.text
    assert client.get("/static/app.js").status_code == 200
    assert (tmp_path / "test.sqlite3").stat().st_mode & 0o077 == 0


def test_oversized_and_validation_errors_do_not_echo_secrets(client):
    too_large = client.post(
        "/api/session", content=b"x" * 65537, headers={"Content-Type": "application/json"}
    )
    assert too_large.status_code == 413
    secret = "sensitive-password-" * 20
    invalid = client.post(
        "/api/session",
        json={"email": "x@y", "password": secret},
        headers={"X-Requested-With": "MCCI-CONNECT"},
    )
    assert invalid.status_code == 422
    assert secret not in invalid.text
    assert "input" not in invalid.text


def test_rate_limit_survives_new_clients(client):
    from fastapi.testclient import TestClient

    for _ in range(10):
        assert login(client, password="wrong").status_code == 401
    with TestClient(app) as another_client:
        assert login(another_client).status_code == 429


def test_reset_or_deactivation_during_login_cannot_issue_session(client, monkeypatch):
    import app.main as main

    original = main.verify_password

    def change_password(password, encoded):
        result = original(password, encoded)
        with connection() as db:
            db.execute("UPDATE users SET active = 0 WHERE role = 'owner'")
        return result

    monkeypatch.setattr(main, "verify_password", change_password)
    assert login(client).status_code == 401
    with connection() as db:
        assert db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0


def test_account_administration_and_session_revocation(client):
    from app.manage import account_change

    login(client)
    with pytest.raises(ValueError, match="last active owner"):
        account_change("owner@example.test", "disable-user")
    account_change("owner@example.test", "reset-password", "a-new-long-password")
    assert client.get("/api/session").status_code == 401
    assert login(client, password=PASSWORD).status_code == 401
    assert login(client, password="a-new-long-password").status_code == 200
    account_change("owner@example.test", "revoke-sessions")
    assert client.get("/api/session").status_code == 401
    account_change("pastor@example.test", "disable-user")
    assert login(client, "pastor").status_code == 401
    account_change("pastor@example.test", "enable-user")
    assert login(client, "pastor").status_code == 200
    with connection() as db:
        actions = {row[0] for row in db.execute("SELECT action FROM audit_log")}
        assert "user.reset_password_by_cli" in actions
        assert "user.disable_user_by_cli" in actions


def test_limit_is_atomic_across_threads(client):
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace

    from fastapi import HTTPException

    from app.main import login_limit

    request = SimpleNamespace(client=SimpleNamespace(host="parallel-test"))

    def attempt(_):
        try:
            login_limit(request)
            return 200
        except HTTPException as exc:
            return exc.status_code

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(attempt, range(20)))
    assert results.count(200) == 10
    assert results.count(429) == 10


def test_startup_preserves_existing_data(client):
    from app.db import initialize

    headers = {"X-CSRF-Token": login(client).json()["csrf_token"]}
    client.post("/api/members", json={"name": "Existing"}, headers=headers)
    initialize()
    initialize()
    assert client.get("/api/members").json()["items"][0]["name"] == "Existing"
