# Changelog

## Unreleased

- Hardened sign-in against account-change races; added shared SQLite login throttling, bounded API bodies, redacted validation errors, and local account recovery/revocation commands.

- Established a FastAPI/SQLite foundation with local account provisioning, server-side role checks, expiring sessions, and CSRF protection.
- Added a responsive interface, member directory creation/listing, aggregate attendance, announcements, basic audit events, and a local consistent backup command.
- Added initial automated checks and project documentation. Not production-ready; see `docs/status.md`.
