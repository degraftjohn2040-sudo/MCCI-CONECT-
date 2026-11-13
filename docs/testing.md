# Testing

Run the README checks with synthetic data. Automated tests use a fresh temporary SQLite database and FastAPI TestClient, covering every role's permissions, authentication, logout, CSRF, session expiry and account deactivation, validation, pagination, audit creation, rate limiting, headers, persistence and backup overwrite protection/integrity. `node --check` checks JavaScript syntax only; it is not a browser interaction or accessibility test. `compileall` checks Python compilation, not a distributable build. `pip-audit` checks the resolved runtime and development dependencies against its advisory source; a clean result is not proof of security.

Before release add browser end-to-end tests on mobile/desktop, keyboard and screen-reader tests, concurrency and load tests, proxy/TLS tests, restore drills, accessibility tooling and independent penetration testing. CI results are only known after the hosted workflow runs.
