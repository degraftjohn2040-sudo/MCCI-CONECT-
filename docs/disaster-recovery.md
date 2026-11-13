# Backup and recovery

The manual backup command uses SQLite's online backup API for a consistent snapshot, checks `PRAGMA integrity_check`, creates the destination exclusively with owner-only file permissions, and refuses to overwrite an existing path:

```sh
# Set MCCI_DATABASE to the source if not using the default.
python -m app.backup /secure/backups/mcci-2026-11-13.sqlite3
```

The destination directory must already exist and be private. The snapshot contains personal data, password hashes and sessions; encrypt it using approved infrastructure, restrict access, store offsite, rotate and monitor according to a documented retention policy. The command does not encrypt, schedule or upload backups.

For a recovery drill: stop all application processes; preserve a separate copy of the current database and its WAL/SHM files; restore a verified snapshot to a **new**, private, isolated path:

```sh
python -m app.restore /secure/backups/mcci-2026-11-13.sqlite3 /secure/restore/mcci-restored.sqlite3
```

The restore command refuses to overwrite a file, checks the SQLite integrity and required tables, and revokes all sessions in the restored copy. It does not change the snapshot or live database. Verify records and permissions with synthetic data, rehearse migrations, then follow an approved cutover plan with application processes stopped. Preserve both the old database and snapshot until validation and sign-off. Restoring a snapshot loses changes since that snapshot. No offsite restore drill, recovery point/time objective or production cutover has been established or tested.
