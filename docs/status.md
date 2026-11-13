# Project status and initial audit

## Starting point

At base commit `5b1630c9cab62b3f6238ebeb44c5aca890a7802c`, the entire tracked repository consisted of a two-line README. There was no application framework, language, backend, database, authentication, integrations, deployment configuration, dependency manifest, tests, or other features to audit. No existing data was found in the checkout. Nothing was deployed.

## Implemented in this stage

- FastAPI/Python backend; vanilla HTML/CSS/JavaScript responsive interface; SQLite single-installation storage.
- Locally provisioned accounts for all 12 requested role names; server-side permission checks; expiring server-side sessions; CSRF protection; SQLite-backed sign-in throttling shared by processes using the same database.
- Trusted local CLI account disable/enable, password reset and session revocation; reset and deactivation revoke existing sessions.
- Create, search, edit and explicitly delete member records; bounded CSV contact import with permission confirmation and duplicate checks; aggregate attendance and internal announcements; paginated list endpoints. Admin-only list of basic audit events. Online SQLite snapshot command.
- Buildable Python wheel and source distribution, hash-locked Python 3.11 dependencies, and CI configuration for lint, formatting, type checks, tests, build, dependency audit and secret scan.

## Partial and limitations

This is a pre-production prototype. Member records cannot yet be exported, merged, or isolated by zone/cell. CSV duplicate detection only checks exact phone and case-insensitive ASCII email matches; review contacts and permission before import. Deletion does not remove copies from backups. Attendance is an event headcount, not individual check-in. Announcements are internal to signed-in users and cannot be edited/deleted. Role scopes are intentionally conservative and need MCCI approval; leader roles cannot read member data. Audit is not comprehensive or tamper-proof. Backup and restore are manual and unencrypted; restore creates a new file and revokes sessions, but there is no automated offsite backup or cutover. The database is not multi-tenant or designed for scale-out. The Python 3.11 dependency tree is hash-locked; other environments and build reproducibility still require verification. UI accessibility, mobile devices, poor-network behavior, threat model, load capacity, and independent security review have not been verified. A Python source distribution and wheel can be built; there is no frontend bundle.

## Not implemented

Pastoral follow-up; communities; prayer requests; form builder, templates, public links and responses; spreadsheet editing; WhatsApp/SMS/email actions or delivery; AI assistant and API secret storage; Google Workspace; analytics; Android native app; MFA, self-service recovery/reset, admin UI for account management, automated backups, retention workflows, and operational monitoring. Connected services have not been configured or verified. Do not assume any integration exists.

## Readiness

Do not deploy or enter real personal data until the security, privacy, permissions, operational, backup/restore, testing, and scaling gaps in the roadmap are addressed and explicitly approved by MCCI. No deployment has been performed.
