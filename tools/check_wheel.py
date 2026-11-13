"""Check that the built wheel contains the server and browser assets."""

from pathlib import Path
from zipfile import ZipFile

wheels = list(Path("dist").glob("mcci_connect-*.whl"))
if len(wheels) != 1:
    raise SystemExit("Expected exactly one MCCI CONNECT wheel in dist/")
with ZipFile(wheels[0]) as wheel:
    required = {
        "app/main.py",
        "app/db.py",
        "app/security.py",
        "app/backup.py",
        "app/restore.py",
        "app/static/index.html",
        "app/static/app.js",
        "app/static/styles.css",
    }
    missing = required - set(wheel.namelist())
    if missing:
        raise SystemExit(f"Missing wheel contents: {sorted(missing)}")
print("Wheel contains the server and static assets.")
