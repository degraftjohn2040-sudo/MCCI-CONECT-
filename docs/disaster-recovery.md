# Backup and recovery

The manual command uses SQLite's online backup API for a consistent snapshot, checks `PRAGMA integrity_check`, creates the destination exclusively with owner-only file permissions, and refuses to overwrite an existing path:

```sh
# Set MCCI_DATABASE to the source if not using the default.
python -m app.backup /secure/backups/mcci-2026-11-13.sqlite3
```

The destination directory must already exist and be private. The snapshot contains personal data, password hashes and sessions; encrypt it using approved infrastructure, restrict access, store offsite, rotate and monitor according to a documented retention policy. The command does not encrypt, schedule, upload, or verify a restore.

For a recovery drill: stop all application processes; make a separate copy of the current database and its WAL/SHM files; restore a verified snapshot to a **new** isolated path; run `PRAGMA integrity_check` with SQLite tools; invalidate restored sessions (`DELETE FROM sessions`) before exposing the restored copy; check records and permissions with synthetic data; then follow an approved cutover plan. Preserve both the old database and snapshot until validation and sign-off. Restoring a snapshot loses changes since that snapshot. No recovery point/time objective has been established or tested.
