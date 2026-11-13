# Security policy

This foundation is **not approved for production or real member data**. Review [status](docs/status.md), [privacy](docs/privacy.md), and [deployment](docs/deployment.md) before considering use.

## Reporting

Do not open public issues containing vulnerabilities, credentials, or member information. Privately contact the repository owner through GitHub or an independently verified MCCI administrative channel. No dedicated security email or response SLA has been established. Include reproduction steps using synthetic data; do not access others' data. The owner should acknowledge, triage, remediate, and coordinate disclosure.

## Present controls and gaps

Passwords use salted PBKDF2-HMAC-SHA256 (600,000 iterations), sessions are random, hashed at rest, expire after eight hours, and use HTTP-only, SameSite=Strict cookies, secure by default. Mutations require a session-bound CSRF header; login requires a custom header. Server-side permissions default to restricted. SQL is parameterized and UI content is rendered as text. API responses are non-cacheable and basic browser security headers are set.

The login rate limiter is **per process and per direct peer**, not distributed, and is unsuitable as the only protection at an internet edge. There is no MFA, password reset/change UI, lockout management, centralized session revocation UI, comprehensive security audit, field encryption, or organization/row-level isolation. SQLite files and backups are sensitive and are not encrypted by the app. Audit events are incomplete and not tamper-proof. Limit request sizes and apply shared rate limits at a trusted reverse proxy; do not trust client-supplied forwarding headers. Use TLS, restricted network access, encrypted storage, monitored backups, and independent security review before any real use.
