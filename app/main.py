"""Single-installation church management foundation; see docs/status.md for limits."""

import hmac
import os
import secrets
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db import connection, initialize
from app.security import ADMINS, MEMBER_READERS, ROLES, hash_password, token_hash, verify_password

STATIC = Path(__file__).parent / "static"
SESSION_SECONDS = 8 * 60 * 60
DUMMY_HASH = hash_password("not-a-real-password")
_attempts: dict[str, deque[float]] = defaultdict(deque)
_attempt_lock = threading.Lock()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize()
    yield


app = FastAPI(
    title="MCCI CONNECT", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan
)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.middleware("http")
async def security_headers(request: Request, call_next: Any) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
    )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(Input):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class Member(Input):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(default="", max_length=40)
    email: str = Field(default="", max_length=254)

    @field_validator("email")
    @classmethod
    def email_format(cls, value: str) -> str:
        if value and ("@" not in value or any(c.isspace() for c in value)):
            raise ValueError("Enter a valid email address")
        return value


class Announcement(Input):
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=4000)


class Attendance(Input):
    event_name: str = Field(min_length=1, max_length=160)
    event_date: date
    headcount: int = Field(ge=0, le=1000000, strict=True)


def login_limit(request: Request) -> None:
    # Single-process best-effort guard. A trusted edge must enforce shared limits in production.
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _attempt_lock:
        for key in list(_attempts):
            if not _attempts[key] or _attempts[key][-1] < now - 900:
                del _attempts[key]
        attempts = _attempts[ip]
        while attempts and attempts[0] < now - 900:
            attempts.popleft()
        if len(attempts) >= 10:
            raise HTTPException(429, "Too many sign-in attempts. Try again later.")
        attempts.append(now)


def current_user(request: Request) -> dict[str, Any]:
    token = request.cookies.get("mcci_session", "")
    if not token or len(token) > 128:
        raise HTTPException(401, "Sign in required")
    with connection() as db:
        row = db.execute(
            """SELECT u.id, u.email, u.role, s.csrf_token FROM sessions s
               JOIN users u ON u.id = s.user_id
               WHERE s.token_hash = ? AND s.expires_at > ? AND u.active = 1""",
            (token_hash(token), int(time.time())),
        ).fetchone()
    if row is None or row["role"] not in ROLES:
        raise HTTPException(401, "Session expired or invalid")
    user = dict(row)
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        csrf = request.headers.get("X-CSRF-Token", "")
        if not hmac.compare_digest(csrf.encode("utf-8"), user["csrf_token"].encode("utf-8")):
            raise HTTPException(403, "Invalid request token")
    return user


User = Annotated[dict[str, Any], Depends(current_user)]


def require_admin(user: User) -> dict[str, Any]:
    if user["role"] not in ADMINS:
        raise HTTPException(403, "You do not have permission")
    return user


def require_member_reader(user: User) -> dict[str, Any]:
    if user["role"] not in MEMBER_READERS:
        raise HTTPException(403, "You do not have permission")
    return user


Admin = Annotated[dict[str, Any], Depends(require_admin)]
Reader = Annotated[dict[str, Any], Depends(require_member_reader)]


def audit(db: Any, actor: int | None, action: str, resource_id: int | None = None) -> None:
    db.execute(
        "INSERT INTO audit_log(actor_id, action, resource_id) VALUES (?, ?, ?)",
        (actor, action, resource_id),
    )


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-store"})


@app.post("/api/session")
def login(data: Login, request: Request, response: Response) -> dict[str, Any]:
    # A custom header and JSON request cannot be sent cross-origin by a browser without CORS.
    if request.headers.get("X-Requested-With") != "MCCI-CONNECT":
        raise HTTPException(403, "Invalid request")
    login_limit(request)
    with connection() as db:
        row = db.execute(
            "SELECT id, email, role, password_hash, active FROM users WHERE email = ?",
            (data.email.strip().lower(),),
        ).fetchone()
        valid = verify_password(data.password, row["password_hash"] if row else DUMMY_HASH)
        if not row or not valid or not row["active"]:
            # Commit before raising so the audit event survives.
            audit(db, None, "session.login_failed")
            db.commit()
            raise HTTPException(401, "Invalid email or password")
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        db.execute("DELETE FROM sessions WHERE expires_at <= ?", (int(time.time()),))
        db.execute(
            "INSERT INTO sessions(token_hash, user_id, csrf_token, expires_at) VALUES (?, ?, ?, ?)",
            (token_hash(token), row["id"], csrf, int(time.time()) + SESSION_SECONDS),
        )
        audit(db, row["id"], "session.login")
        response.set_cookie(
            "mcci_session",
            token,
            max_age=SESSION_SECONDS,
            httponly=True,
            samesite="strict",
            secure=os.environ.get("MCCI_SECURE_COOKIES", "1") != "0",
            path="/",
        )
        return {"email": row["email"], "role": row["role"], "csrf_token": csrf}


@app.get("/api/session")
def session(user: User) -> dict[str, Any]:
    return {"email": user["email"], "role": user["role"], "csrf_token": user["csrf_token"]}


@app.delete("/api/session", status_code=204)
def logout(request: Request, response: Response, user: User) -> None:
    with connection() as db:
        db.execute(
            "DELETE FROM sessions WHERE token_hash = ?",
            (token_hash(request.cookies["mcci_session"]),),
        )
        audit(db, user["id"], "session.logout")
    response.delete_cookie("mcci_session", path="/", samesite="strict")


@app.get("/api/members")
def members(
    _user: Reader, limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0, le=100000)
) -> dict[str, Any]:
    with connection() as db:
        rows = db.execute(
            "SELECT id, name, phone, email, created_at FROM members "
            "ORDER BY name COLLATE NOCASE, id LIMIT ? OFFSET ?",
            (limit + 1, offset),
        ).fetchall()
    return {"items": [dict(row) for row in rows[:limit]], "has_more": len(rows) > limit}


@app.post("/api/members", status_code=201)
def add_member(data: Member, user: Admin) -> dict[str, int]:
    with connection() as db:
        cur = db.execute(
            "INSERT INTO members(name, phone, email) VALUES (?, ?, ?)",
            (data.name, data.phone, data.email),
        )
        assert cur.lastrowid is not None
        audit(db, user["id"], "member.created", cur.lastrowid)
        return {"id": cur.lastrowid}


@app.get("/api/announcements")
def announcements(
    _user: User, limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0, le=100000)
) -> dict[str, Any]:
    with connection() as db:
        rows = db.execute(
            "SELECT id, title, body, created_at FROM announcements "
            "ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit + 1, offset),
        ).fetchall()
    return {"items": [dict(row) for row in rows[:limit]], "has_more": len(rows) > limit}


@app.post("/api/announcements", status_code=201)
def add_announcement(data: Announcement, user: Admin) -> dict[str, int]:
    with connection() as db:
        cur = db.execute(
            "INSERT INTO announcements(title, body) VALUES (?, ?)", (data.title, data.body)
        )
        assert cur.lastrowid is not None
        audit(db, user["id"], "announcement.created", cur.lastrowid)
        return {"id": cur.lastrowid}


@app.get("/api/attendance")
def attendance(
    _user: Reader, limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0, le=100000)
) -> dict[str, Any]:
    with connection() as db:
        rows = db.execute(
            "SELECT id, event_name, event_date, headcount, created_at FROM attendance "
            "ORDER BY event_date DESC, id DESC LIMIT ? OFFSET ?",
            (limit + 1, offset),
        ).fetchall()
    return {"items": [dict(row) for row in rows[:limit]], "has_more": len(rows) > limit}


@app.post("/api/attendance", status_code=201)
def add_attendance(data: Attendance, user: Admin) -> dict[str, int]:
    with connection() as db:
        cur = db.execute(
            "INSERT INTO attendance(event_name, event_date, headcount) VALUES (?, ?, ?)",
            (data.event_name, data.event_date.isoformat(), data.headcount),
        )
        assert cur.lastrowid is not None
        audit(db, user["id"], "attendance.created", cur.lastrowid)
        return {"id": cur.lastrowid}


@app.get("/api/audit")
def audit_log(
    _user: Admin, limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0, le=100000)
) -> dict[str, Any]:
    with connection() as db:
        rows = db.execute(
            "SELECT id, actor_id, action, resource_id, created_at FROM audit_log "
            "ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit + 1, offset),
        ).fetchall()
    return {"items": [dict(row) for row in rows[:limit]], "has_more": len(rows) > limit}
