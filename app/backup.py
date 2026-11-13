"""Create a consistent local SQLite snapshot without overwriting an existing file."""

import argparse
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from app.db import database_path


def backup(destination: Path) -> None:
    source = database_path().resolve()
    if not source.is_file():
        raise FileNotFoundError("Source database does not exist")
    # Exclusive creation prevents overwriting any existing file, including symlinks.
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as src:
            with closing(sqlite3.connect(destination)) as dst:
                src.backup(dst)
                if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("Backup integrity check failed")
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="A new, non-existent backup file")
    args = parser.parse_args()
    backup(args.destination)
    print("Backup created and SQLite integrity check passed. Protect and test this file.")


if __name__ == "__main__":
    main()
