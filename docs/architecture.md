# Architecture

The browser uses same-origin static HTML/CSS/JS and calls `/api/*`. FastAPI handles validation, sessions, CSRF and authorization. SQLite stores one church installation on a persistent local filesystem; connection-per-operation and transactions make each write and its audit event atomic. No cloud service, background worker, external identity provider, or Android native client exists.

Cookie tokens are random, hashed in SQLite and checked against active accounts and expiry for every authenticated request; a separate session CSRF token protects state changes. Unknown roles are denied. No CORS is enabled. Login throttling is local to one process and does not trust proxy-supplied IP headers. An HTTPS reverse proxy with shared rate limits and request-size limits is a prerequisite, not included.

This design has no tenant ID, per-zone policy, fine-grained member visibility, distributed sessions/rate limiter, queue, high availability or horizontal scale. Do not run multiple churches or concurrent server replicas against a shared SQLite filesystem. Use a reviewed migration to a managed relational database with enforced tenant/scope boundaries before scaling. Keep future external credentials exclusively server-side in a secrets manager, never in browser code or Git.
