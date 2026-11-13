"""Administrative commands; run only from a trusted host."""

import argparse
import getpass
import sqlite3

from app.db import connection, initialize
from app.security import ROLES, hash_password


def account_change(email: str, action: str, password: str | None = None) -> None:
    """Atomically modify an account and revoke sessions where appropriate."""
    if action not in {"reset-password", "disable-user", "enable-user", "revoke-sessions"}:
        raise ValueError("Unknown account action")
    if action == "reset-password" and (password is None or not 12 <= len(password) <= 256):
        raise ValueError("Password must be 12 to 256 characters")
    password_hash = hash_password(password) if password is not None else None
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        user = db.execute("SELECT id, role, active FROM users WHERE email = ?", (email,)).fetchone()
        if user is None:
            raise ValueError("Account not found")
        if action == "disable-user":
            if user["role"] == "owner" and user["active"]:
                count = db.execute(
                    "SELECT count(*) FROM users WHERE role = 'owner' AND active = 1"
                ).fetchone()[0]
                if count <= 1:
                    raise ValueError("Cannot disable the last active owner")
            db.execute("UPDATE users SET active = 0 WHERE id = ?", (user["id"],))
        elif action == "enable-user":
            db.execute("UPDATE users SET active = 1 WHERE id = ?", (user["id"],))
        elif action == "reset-password":
            db.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user["id"])
            )
        if action != "enable-user":
            db.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))
        db.execute(
            "INSERT INTO audit_log(actor_id, action, resource_id) VALUES (NULL, ?, ?)",
            (f"user.{action.replace('-', '_')}_by_cli", user["id"]),
        )


def prompt_password(parser: argparse.ArgumentParser) -> str:
    password = getpass.getpass("Password (at least 12 characters): ")
    if not 12 <= len(password) <= 256:
        parser.error("Password must be 12 to 256 characters")
    if password != getpass.getpass("Confirm password: "):
        parser.error("Passwords do not match")
    return password


def main() -> None:
    parser = argparse.ArgumentParser(description="MCCI CONNECT local administration")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create-user", help="Create a local account")
    create.add_argument("email")
    create.add_argument("--role", choices=ROLES, required=True)
    for command in ("reset-password", "disable-user", "enable-user", "revoke-sessions"):
        command_parser = sub.add_parser(command)
        command_parser.add_argument("email")
    args = parser.parse_args()
    email = args.email.strip().lower()
    if len(email) > 254 or "@" not in email or any(c.isspace() for c in email):
        parser.error("Enter a valid email address")
    password = (
        prompt_password(parser) if args.command in {"create-user", "reset-password"} else None
    )
    initialize()
    try:
        if args.command == "create-user":
            assert password is not None
            with connection() as db:
                cursor = db.execute(
                    "INSERT INTO users(email, password_hash, role) VALUES (?, ?, ?)",
                    (email, hash_password(password), args.role),
                )
                db.execute(
                    "INSERT INTO audit_log(actor_id, action, resource_id) VALUES (NULL, ?, ?)",
                    ("user.created_by_cli", cursor.lastrowid),
                )
        else:
            account_change(email, args.command, password)
    except sqlite3.IntegrityError:
        parser.error("Account already exists")
    except ValueError as exc:
        parser.error(str(exc))
    print("Account operation completed.")


if __name__ == "__main__":
    main()
