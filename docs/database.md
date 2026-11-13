# Database design

SQLite is created on first startup via idempotent `CREATE TABLE IF NOT EXISTS`; this is initial schema setup, **not a migration system**. Back up and plan versioned migrations before evolving an existing installation. Foreign keys are enabled per connection; WAL mode is enabled at initialization. SQLite must be on supported persistent local storage, not an ephemeral deployment filesystem or a shared network volume.

- `users`: email (case-insensitive unique), password hash, role, active flag.
- `sessions`: SHA-256 token hash, user FK, CSRF token, expiry; expiry indexed.
- `members`: name, optional phone/email, creation time; case-insensitive name/id index supports directory ordering.
- `attendance`: event name, date, nonnegative aggregate count, creation time; date/id index supports ordering.
- `announcements`: title, body, creation time; primary key supports reverse chronological listing.
- `audit_log`: actor FK (nullable for failures/CLI), action, optional resource ID, timestamp; ID orders events.

There is no row-level isolation, retention, soft deletion, migration history or encryption at rest. Sessions and backups contain sensitive material. Access to the file is privileged access to all records; protect at the OS and storage layers. Do not manually alter records in a live system without an approved procedure and backup.
