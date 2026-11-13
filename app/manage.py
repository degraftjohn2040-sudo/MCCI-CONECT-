"""Administrative commands; run only from a trusted host."""

import argparse
import getpass
import sqlite3

from app.db import connection, initialize
from app.security import ROLES, hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="MCCI CONNECT local administration")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create-user", help="Create a local account")
    create.add_argument("email")
    create.add_argument("--role", choices=ROLES, required=True)
    args = parser.parse_args()
    email = args.email.strip().lower()
    if len(email) > 254 or "@" not in email or any(c.isspace() for c in email):
        parser.error("Enter a valid email address")
    password = getpass.getpass("Password (at least 12 characters): ")
    if len(password) < 12 or len(password) > 256:
        parser.error("Password must be 12 to 256 characters")
    if password != getpass.getpass("Confirm password: "):
        parser.error("Passwords do not match")
    initialize()
    try:
        with connection() as db:
            cursor = db.execute(
                "INSERT INTO users(email, password_hash, role) VALUES (?, ?, ?)",
                (email, hash_password(password), args.role),
            )
            db.execute(
                "INSERT INTO audit_log(actor_id, action, resource_id) VALUES (NULL, ?, ?)",
                ("user.created_by_cli", cursor.lastrowid),
            )
    except sqlite3.IntegrityError:
        parser.error("Account already exists")
    print("Account created.")


if __name__ == "__main__":
    main()
