# EKOS backend demo

FastAPI, SQLAlchemy, JWT auth, persisted connectors, database permissions, and the existing GitHub connector power the 30% demo. Python 3.11+ is required; the local setup was verified with Python 3.12.14.

## Fresh setup (PowerShell, from repository root)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```

Set a unique `JWT_SECRET` in `backend\.env`. The example `POSTGRES_URL=sqlite:///./aekos.db` creates a local SQLite database. For PostgreSQL, set `POSTGRES_URL` to your existing database URL. Set `GITHUB_TOKEN`, `GITHUB_OWNER`, and `GITHUB_REPO` for a repository the token can read. Keep credentials only in the server environment file; the seed does not put the GitHub token in the database. With these values empty, GitHub is seeded as **not_configured** and test/sync return 409. `CORS_ORIGINS` contains the two default Vite origins. Neo4j, Chroma, and LLM settings remain future-stage placeholders; no such service is needed for this demo.

```powershell
cd E:\PROJECTS\EKOS\backend
..\.venv\Scripts\python.exe scripts\seed_demo.py
..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

`scripts/seed_demo.py` can be run repeatedly. It creates missing roles and users using the existing initial-data function, then missing connector permissions and one GitHub Connector row for ABC Solutions. It preserves existing users, configuration tokens, and last-sync timestamps. Backend startup still initializes tables and the original users, but the explicit seed command is required for connector registration and permissions.

| Role | Email | Password | Connector permissions |
| --- | --- | --- | --- |
| Developer | `arnold@aekos.com` | `password123` | read |
| Administrator | `admin@aekos.com` | `admin123` | read, manage, test, sync |

These are development-only credentials. Passwords are hashed in the database.

## API

| Method | Route | Behavior |
| --- | --- | --- |
| POST | `/api/login` | Returns JWT for seeded users |
| POST | `/api/logout` | Authenticated logout acknowledgement |
| GET | `/api/profile` | Identity, organization, role, database permissions |
| GET | `/api/connectors` | Organization-scoped persisted connector records; `connectors:read` |
| POST/PUT/DELETE | `/api/connectors`, `/api/connectors/{id}` | Connector management; `connectors:manage` |
| POST | `/api/connectors/{id}/test` | Calls `GitHubConnector.test_connection()`; `connectors:test` |
| POST | `/api/connectors/{id}/sync` | Calls `GitHubConnector.sync()`; `connectors:sync` |

Test returns the authenticated GitHub account. Sync returns the repository, default branch, branch/commit/issue counts, and timestamp; it updates connector status and `last_sync`. The API never returns the token. GitHub API/network failures return 502 with a safe message. Tenant ownership is checked for connector actions. No new GitHub client was built; the existing teammate implementation is used. Neo4j has node-writing helpers but no complete GitHub ingestion or graph-read path, so sync does not claim graph persistence.

To demonstrate RBAC, log in as Developer and observe GitHub in GET, then call POST test/sync and receive 403. Log in as Administrator and run test/sync. When GitHub env vars are absent, admin receives 409; with valid credentials and network, test/sync invoke GitHub. Swagger is available at `http://127.0.0.1:8000/docs`.

## Tests

```powershell
cd E:\PROJECTS\EKOS\backend
..\.venv\Scripts\python.exe -m pytest -q
```

Tests cover auth, profile permissions, seeded connector idempotence, RBAC 403/allowed actions, GitHub service behavior with mocked HTTP, sync counts and timestamps, configuration errors, and organization scoping. They require no live GitHub token.
