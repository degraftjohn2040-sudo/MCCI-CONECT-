# Database design

SQLite is created on first startup via idempotent `CREATE TABLE IF NOT EXISTS`. An additive, transactionally recorded `schema_migrations` ledger applies the initial member version column and contact indexes to existing databases; newer unknown migration versions fail startup. Back up before upgrading and test each future migration and rollback. Initial table creation is idempotent, not part of the migration transaction. Foreign keys are enabled per connection; WAL mode is enabled at initialization. SQLite must be on supported persistent local storage, not an ephemeral deployment filesystem or a shared network volume.

- `users`: email (case-insensitive unique), password hash, role, active flag.
- `sessions`: SHA-256 token hash, user FK, CSRF token, expiry; expiry indexed.
- `login_limits`: hashed direct peer, fixed-window start and count; expired entries are removed during login attempts. This is an additive table for existing databases.
- `members`: name, optional phone/email, creation time, optimistic-lock version; name/id, email and phone indexes support directory ordering and duplicate checks.
- `attendance`: event name, date, nonnegative aggregate count, creation time; date/id index supports ordering.
- `announcements`: title, body, creation time; primary key supports reverse chronological listing.
- `audit_log`: actor FK (nullable for failures/CLI), action, optional resource ID, timestamp; ID orders events.

There is no row-level isolation, retention, soft deletion, full migration framework, or encryption at rest. Sessions and backups contain sensitive material. Access to the file is privileged access to all records; protect at the OS and storage layers. Do not manually alter records in a live system without an approved procedure and backup.
