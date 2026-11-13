"""Restore a SQLite snapshot to a new file and invalidate all restored sessions."""

import argparse
import os
import sqlite3
from contextlib import closing
from pathlib import Path


def restore(snapshot: Path, destination: Path) -> None:
    source = snapshot.resolve()
    if not source.is_file():
        raise FileNotFoundError("Snapshot does not exist")
    # Never replace a live database or another existing file.
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as src:
            with closing(sqlite3.connect(destination)) as dst:
                src.backup(dst)
                if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("Snapshot integrity check failed")
                required = {
                    "users",
                    "sessions",
                    "members",
                    "attendance",
                    "announcements",
                    "audit_log",
                }
                tables = {
                    row[0]
                    for row in dst.execute("SELECT name FROM sqlite_master WHERE type='table'")
                }
                if not required.issubset(tables):
                    raise RuntimeError("Snapshot is not an MCCI database")
                dst.execute("DELETE FROM sessions")
                dst.commit()
                if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("Restored database integrity check failed")
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="Existing backup file")
    parser.add_argument("destination", type=Path, help="A new, non-existent database file")
    args = parser.parse_args()
    restore(args.snapshot, args.destination)
    print("Restored to new file. Sessions revoked. Review and approve cutover separately.")


if __name__ == "__main__":
    main()
