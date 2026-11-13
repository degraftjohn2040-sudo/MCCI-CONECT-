"""Single-installation church management foundation; see docs/status.md for limits."""

import csv
import hashlib
import hmac
import io
import os
import secrets
import time
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.db import connection, initialize
from app.limits import RequestSizeLimit
from app.security import ADMINS, MEMBER_READERS, ROLES, hash_password, token_hash, verify_password

STATIC = Path(__file__).parent / "static"
SESSION_SECONDS = 8 * 60 * 60
DUMMY_HASH = hash_password("not-a-real-password")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize()
    yield


app = FastAPI(
    title="MCCI CONNECT", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan
)
app.add_middleware(RequestSizeLimit)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    # Pydantic error objects contain submitted input, including passwords. Never echo it.
    details = [
        {"loc": error["loc"], "msg": error["msg"], "type": error["type"]} for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": details})


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


class MemberImport(Input):
    csv_text: str = Field(min_length=1, max_length=60000)
    confirmed_permission: bool = Field(strict=True)

    @field_validator("confirmed_permission")
    @classmethod
    def must_confirm(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Confirm permission before importing")
        return value


class MemberUpdate(Member):
    version: int = Field(ge=1, strict=True)


class Announcement(Input):
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=4000)


class Attendance(Input):
    event_name: str = Field(min_length=1, max_length=160)
    event_date: date
    headcount: int = Field(ge=0, le=1000000, strict=True)


def login_limit(request: Request) -> None:
    # Shared by processes using this SQLite database. A trusted edge must still limit traffic.
    peer = request.client.host if request.client else "unknown"
    peer_hash = hashlib.sha256(peer.encode()).hexdigest()
    now = int(time.time())
    limited = False
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM login_limits WHERE window_start <= ?", (now - 900,))
        row = db.execute(
            "SELECT attempts FROM login_limits WHERE peer_hash = ?", (peer_hash,)
        ).fetchone()
        if row and row["attempts"] >= 10:
            limited = True
        elif row:
            db.execute(
                "UPDATE login_limits SET attempts = attempts + 1 WHERE peer_hash = ?", (peer_hash,)
            )
        else:
            db.execute("INSERT INTO login_limits VALUES (?, ?, 1)", (peer_hash, now))
    if limited:
        raise HTTPException(429, "Too many sign-in attempts. Try again later.")


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
        # Serialize with account changes and recheck the credential after hashing, so a
        # concurrent reset or deactivation cannot issue a session using an old password.
        db.execute("BEGIN IMMEDIATE")
        fresh = db.execute(
            "SELECT password_hash, active, role FROM users WHERE id = ?", (row["id"],)
        ).fetchone()
        if (
            not fresh
            or not fresh["active"]
            or fresh["role"] not in ROLES
            or fresh["password_hash"] != row["password_hash"]
        ):
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
        return {"email": row["email"], "role": fresh["role"], "csrf_token": csrf}


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
    _user: Reader,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0, le=100000),
    q: str = Query("", max_length=120),
) -> dict[str, Any]:
    # Prefix search uses the existing NOCASE name index; treat wildcards literally.
    escaped = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    with connection() as db:
        rows = db.execute(
            "SELECT id, name, phone, email, created_at, version FROM members "
            "WHERE name LIKE ? ESCAPE '\\' "
            "ORDER BY name COLLATE NOCASE, id LIMIT ? OFFSET ?",
            (escaped + "%", limit + 1, offset),
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


@app.post("/api/members/import", status_code=201)
def import_members(data: MemberImport, user: Admin) -> dict[str, int]:
    # Strict bounded CSV: no automatic merge, overwrite or partial import.
    try:
        reader = csv.DictReader(io.StringIO(data.csv_text, newline=""), strict=True)
        fields = reader.fieldnames or []
        if not fields or len(fields) != len(set(fields)) or "name" not in fields:
            raise HTTPException(422, "CSV must have a name header and no duplicate headers")
        if set(fields) - {"name", "phone", "email"}:
            raise HTTPException(422, "CSV headers must be name, phone, and/or email")
        members_to_import: list[tuple[int, Member]] = []
        for row in reader:
            if len(members_to_import) >= 100:
                raise HTTPException(422, "Import is limited to 100 rows")
            if None in row or any(value is None for value in row.values()):
                raise HTTPException(422, f"Invalid CSV columns at row {reader.line_num}")
            try:
                members_to_import.append((reader.line_num, Member.model_validate(row)))
            except ValidationError:
                raise HTTPException(422, f"Invalid member at row {reader.line_num}") from None
    except csv.Error:
        raise HTTPException(422, "Invalid CSV format") from None
    if not members_to_import:
        raise HTTPException(422, "CSV contains no members")
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        for position, member in members_to_import:
            duplicate = db.execute(
                "SELECT 1 FROM members WHERE (email != '' AND email = ? COLLATE NOCASE) "
                "OR (phone != '' AND phone = ?) LIMIT 1",
                (member.email, member.phone),
            ).fetchone()
            if duplicate:
                raise HTTPException(
                    409, f"Possible duplicate contact at row {position}; nothing was imported"
                )
            cur = db.execute(
                "INSERT INTO members(name, phone, email) VALUES (?, ?, ?)",
                (member.name, member.phone, member.email),
            )
            audit(db, user["id"], "member.imported", cur.lastrowid)
    return {"imported": len(members_to_import)}


@app.put("/api/members/{member_id}")
def update_member(member_id: int, data: MemberUpdate, user: Admin) -> dict[str, int]:
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT version FROM members WHERE id = ?", (member_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Member not found")
        if row["version"] != data.version:
            raise HTTPException(409, "This record changed. Refresh before editing again.")
        db.execute(
            "UPDATE members SET name = ?, phone = ?, email = ?, version = version + 1 WHERE id = ?",
            (data.name, data.phone, data.email, member_id),
        )
        audit(db, user["id"], "member.updated", member_id)
        return {"id": member_id, "version": data.version + 1}


@app.delete("/api/members/{member_id}", status_code=204)
def delete_member(member_id: int, user: Admin, version: int = Query(ge=1)) -> None:
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT version FROM members WHERE id = ?", (member_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Member not found")
        if row["version"] != version:
            raise HTTPException(409, "This record changed. Refresh before deleting it.")
        db.execute("DELETE FROM members WHERE id = ?", (member_id,))
        audit(db, user["id"], "member.deleted", member_id)


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
