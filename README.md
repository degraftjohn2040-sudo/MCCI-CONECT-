# MCCI CONNECT

**A mobile-first church management foundation for Miracle City Church International (MCCI), UCC Campus.**

MCCI CONNECT is intended to help church teams maintain community records and coordinate their work in one place. This repository contains the application source code, setup instructions, tests, and engineering documentation. It is publicly viewable on GitHub; the repository is **not** a deployed application.

> **Project status: pre-production.** The foundation works locally, but it is not a complete church management platform and has not been approved for production or real member data. See [project status](docs/status.md), [security](SECURITY.md), and the [roadmap](docs/roadmap.md).

## Current capabilities

| Area | Current state |
| --- | --- |
| Accounts and access | Locally provisioned accounts, server-side role checks, expiring sessions, CSRF protection, and local account recovery commands |
| Members | Create, search, edit, and explicitly delete records; bounded CSV import with permission confirmation and basic duplicate checks |
| Attendance | Record and list aggregate headcounts for gatherings |
| Announcements | Create and list internal announcements for signed-in users |
| Accountability and recovery | Basic audit events and manual SQLite backup/restore to a new file |
| Interface | Responsive browser interface with loading, error, and empty states |

All 12 requested role names are recognized. Owner, admin, and super_admin can manage the implemented records; pastor can read members and attendance; other roles can read internal announcements only. Church-specific scopes must be approved before broader access is granted.

**Not yet implemented:** individual attendance, pastoral follow-up, communities, prayer requests, forms and public responses, spreadsheet editing, messaging actions, AI, Google Workspace integrations, analytics, native Android, MFA, and automated encrypted backups. See [status](docs/status.md) for the full list and limitations.

## Technology

- **Backend:** Python 3.11, FastAPI, and SQLite for a single church installation
- **Frontend:** responsive HTML, CSS, and JavaScript served by the application
- **Quality:** pytest, Ruff, mypy, dependency auditing, and GitHub Actions checks
- **Integrations:** no external provider has been connected or verified

## Get started locally

Use synthetic data only. The example commands below are for a Unix-like shell; Windows users should use the equivalent virtual environment activation and environment variable commands.

```sh
git clone https://github.com/degraftjohn2040-sudo/MCCI-CONECT-.git
cd MCCI-CONECT-
python3 -m venv .venv
. .venv/bin/activate
pip install --require-hashes -r requirements-dev.lock
python -m app.manage create-user admin@example.test --role owner
# Local HTTP only. Secure cookies normally require HTTPS.
export MCCI_SECURE_COOKIES=0
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000** on the same machine. The account command prompts for a unique password of 12–256 characters without echo. There is no default account or self-registration. Do not expose this local setup to the public or use real personal data in it.

Data defaults to `data/mcci.sqlite3`, which is excluded from Git. Set `MCCI_DATABASE` to a private, persistent path if needed. Cookies are secure by default; set `MCCI_SECURE_COOKIES=0` only for local HTTP development. Trusted operators can run `python -m app.manage --help` for account recovery and session-revocation commands. See [deployment](docs/deployment.md) and [disaster recovery](docs/disaster-recovery.md) before considering a hosted environment.

## Run the checks

```sh
ruff check app tests tools
ruff format --check app tests tools
mypy app
python -m pytest -q
python -m compileall -q app
node --check app/static/app.js
python -m build --no-isolation
python tools/check_wheel.py
pip-audit -r requirements-dev.lock
```

CI also configures a secret scan. The Python 3.11 lock files pin resolved dependencies with hashes; re-resolve and test for other Python versions or platforms. The build uses the pinned development environment for its build tools.

## Repository guide

```text
app/                 FastAPI application, security, storage, and browser interface
tests/               Automated tests with temporary, synthetic databases
tools/               Build verification utilities
docs/                Product, architecture, operations, and project status
.github/workflows/   CI configuration
```

- [Project status](docs/status.md) · [Product requirements](docs/product-requirements.md) · [Roadmap](docs/roadmap.md)
- [Architecture](docs/architecture.md) · [Database](docs/database.md) · [API](docs/api.md) · [Engineering audit](docs/audit.md)
- [Privacy](docs/privacy.md) · [Performance](docs/performance.md) · [Testing](docs/testing.md)
- [Deployment](docs/deployment.md) · [Disaster recovery](docs/disaster-recovery.md) · [Release management](docs/release-management.md)
- [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md) · [Code of conduct](CODE_OF_CONDUCT.md) · [Changelog](CHANGELOG.md)

## Contributing and security

Contributions should be small, tested, and privacy-conscious. Follow [CONTRIBUTING.md](CONTRIBUTING.md). Never commit passwords, API keys, databases, backups, or real member information. To report a vulnerability, follow [SECURITY.md](SECURITY.md) rather than posting sensitive details in a public issue.
