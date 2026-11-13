# MCCI CONNECT

Church management system for Miracle City Church International (MCCI), UCC Campus.

This repository was initially an empty project with only this README. It now contains a **pre-production foundation**, not a complete church management platform. See [project status](docs/status.md) for implemented and planned capabilities and [security](SECURITY.md) before storing real information. No existing deployment, member data, or integrations were found.

## Local setup

Requires Python 3.11+ and pip. Commands below are for a Unix-like shell; on Windows use the equivalent virtual environment activation and environment variable syntax.

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
python -m app.manage create-user admin@example.test --role owner
# HTTP on a local machine only: secure cookies normally require HTTPS.
export MCCI_SECURE_COOKIES=0
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. The command prompts for the password without echo; use a unique password of 12–256 characters. There is no default account or self-registration. Trusted operators can use `python -m app.manage reset-password`, `disable-user`, `enable-user`, or `revoke-sessions` followed by an account email. Reset and disable revoke existing sessions. The account command has privileged access to the local database and should only be used by a trusted operator. To run on a remote preview host, bind to `0.0.0.0` only in an isolated environment; never expose this development setup to the public or use real data there.

Data defaults to `data/mcci.sqlite3` (ignored by Git); set `MCCI_DATABASE` to an absolute path on persistent private storage. `MCCI_SECURE_COOKIES` defaults to `1`. Only set it to `0` for local HTTP development. No sample members or credentials are provided.

## Quality checks

```sh
ruff check app tests
ruff format --check app tests
mypy app
python -m pytest -q
python -m compileall -q app
node --check app/static/app.js
pip-audit -r requirements-dev.txt
```

CI also runs a secret scan. Direct runtime dependencies are pinned; transitive dependencies are currently resolved at installation time and are not locked. See [testing](docs/testing.md) and [deployment](docs/deployment.md).

## Documentation

- [Status and audit](docs/status.md) · [Product requirements](docs/product-requirements.md) · [Roadmap](docs/roadmap.md)
- [Architecture](docs/architecture.md) · [Database](docs/database.md) · [API](docs/api.md)
- [Privacy](docs/privacy.md) · [Performance](docs/performance.md) · [Testing](docs/testing.md)
- [Deployment](docs/deployment.md) · [Disaster recovery](docs/disaster-recovery.md) · [Release management](docs/release-management.md)
- [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md) · [Code of conduct](CODE_OF_CONDUCT.md) · [Changelog](CHANGELOG.md)
