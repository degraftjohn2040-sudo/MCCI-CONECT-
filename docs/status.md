# Project status and initial audit

## Starting point

At base commit `5b1630c9cab62b3f6238ebeb44c5aca890a7802c`, the entire tracked repository consisted of a two-line README. There was no application framework, language, backend, database, authentication, integrations, deployment configuration, dependency manifest, tests, or other features to audit. No existing data was found in the checkout. Nothing was deployed.

## Implemented in this stage

- FastAPI/Python backend; vanilla HTML/CSS/JavaScript responsive interface; SQLite single-installation storage.
- Locally provisioned accounts for all 12 requested role names; server-side permission checks; expiring server-side sessions; CSRF protection; SQLite-backed sign-in throttling shared by processes using the same database.
- Trusted local CLI account disable/enable, password reset and session revocation; reset and deactivation revoke existing sessions.
- Create/list member names and optional contact details, aggregate attendance counts, and internal announcements; paginated list endpoints. Admin-only list of basic audit events. Online SQLite snapshot command.
- CI configuration for lint, formatting, Python type checks, tests, compilation/JS syntax, dependency vulnerability audit and secret scan.

## Partial and limitations

This is a pre-production prototype. Member records cannot yet be edited, deleted, imported, searched, exported, merged, or isolated by zone/cell. Attendance is an event headcount, not individual check-in. Announcements are internal to signed-in users and cannot be edited/deleted. Role scopes are intentionally conservative and need MCCI approval; leader roles cannot read member data. Audit is not comprehensive or tamper-proof. Backup is manual and unencrypted with no automated restore workflow. The database is not multi-tenant or designed for scale-out. The dependency tree is not lockfile-pinned. UI accessibility, mobile devices, poor-network behavior, threat model, load capacity, and independent security review have not been verified. Python compilation is the build check; there is no frontend bundle.

## Not implemented

Contact import; pastoral follow-up; communities; prayer requests; form builder, templates, public links and responses; spreadsheet editing; WhatsApp/SMS/email actions or delivery; AI assistant and API secret storage; Google Workspace; analytics; Android native app; MFA, self-service recovery/reset, admin UI for account management, automated backups, retention/deletion workflows, and operational monitoring. Connected services have not been configured or verified. Do not assume any integration exists.

## Readiness

Do not deploy or enter real personal data until the security, privacy, permissions, operational, backup/restore, testing, and scaling gaps in the roadmap are addressed and explicitly approved by MCCI. No deployment has been performed.
