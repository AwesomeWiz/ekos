# EKOS 30% demo

The React frontend uses the FastAPI login, profile, and connector APIs. GitHub connection checks and syncs call the existing backend `GitHubConnector`. Chat answers, references, and graph entities remain labeled sample data.

## Fresh local database (PowerShell)

From `E:\PROJECTS\EKOS`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```

Edit `backend\.env`: set a unique `JWT_SECRET`. SQLite works with the example `POSTGRES_URL=sqlite:///./aekos.db`. To enable real GitHub actions, set `GITHUB_TOKEN`, `GITHUB_OWNER`, and `GITHUB_REPO` to a token with access to that repository and its owner/name. Leave them empty to demonstrate the honest **Not configured** state. The token stays on the server and is never returned by the connector API. Neo4j variables are placeholders for later graph work and are not required for this demo.

Then seed and start the backend from `backend/`:

```powershell
cd E:\PROJECTS\EKOS\backend
..\.venv\Scripts\python.exe scripts\seed_demo.py
..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

The seed is explicit and idempotent. It creates missing roles, hashed-password demo users, database permissions, and one GitHub connector for ABC Solutions without overwriting existing accounts or secrets. Run it again after changing GitHub configuration, then restart the backend.

In another terminal:

```powershell
cd E:\PROJECTS\EKOS\frontend
npm.cmd install
npm.cmd run dev -- --port 5173 --strictPort
```

Open `http://127.0.0.1:5173`. Node.js 24 LTS or 22.13+ is supported. `npm.cmd` avoids PowerShell's `npm.ps1` restriction. The frontend defaults to `http://127.0.0.1:8000/api`; `frontend/.env.example` documents optional `VITE_API_BASE_URL` and `VITE_API_PREFIX`. Restart Vite after changing those. Never put the GitHub token or JWT secret in a `VITE_*` variable.

## Demo accounts and sequence

| Role | Email | Password | Connector access |
| --- | --- | --- | --- |
| Developer | `arnold@aekos.com` | `password123` | Read only |
| Administrator | `admin@aekos.com` | `admin123` | Read, manage, test, sync |

1. Sign in as Developer. The sidebar and `/account` show the role and database permissions. `/connectors` shows the seeded GitHub status, with admin actions hidden.
2. A direct Developer `POST /api/connectors/{id}/sync` or `/test` returns 403. Connector create, update, and delete also require Administrator permission.
3. Sign out and sign in as Administrator. With all three GitHub settings configured, use **Test connection** and **Sync** on `/connectors`. The UI shows loading, account/repository results or a concrete error, refreshes status, and shows last sync and counts. Without settings, controls are disabled and the server returns 409 if called directly.
4. Visit `/chat` and `/knowledge-graph` for the existing labeled sample interactions. Their answers and graph are not live GitHub or Neo4j data.

The backend routes are `POST /api/login`, `POST /api/logout`, `GET /api/profile`, `GET/POST /api/connectors`, `PUT/DELETE /api/connectors/{id}`, and `POST /api/connectors/{id}/test` and `/sync`. JWTs are kept in tab-scoped `sessionStorage`; the backend checks permissions against its database. GitHub sync fetches and transforms repository, branch, commit, issue, and README data through the teammate connector. The API returns repository name, default branch, item counts, sync time, and status; it does not persist those fetched items to Neo4j because no complete ingestion/read pipeline exists. Jira, Slack, and Confluence are marked planned, without simulated connections.

## Verification

```powershell
cd E:\PROJECTS\EKOS\backend
..\.venv\Scripts\python.exe -m pytest -q
cd E:\PROJECTS\EKOS\frontend
npm.cmd test
npm.cmd run build
```

For the optional live frontend-to-FastAPI check, run the seeded backend and set test-process-only `EKOS_TEST_EMAIL` and `EKOS_TEST_PASSWORD`, then use `npm.cmd test -- src/liveBackend.test.tsx`. Normal automated tests mock GitHub HTTP and need no real token. A live GitHub check requires your own configured token and network access.
