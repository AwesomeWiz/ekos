# EKOS 30% demo

The React frontend uses the FastAPI login, profile, connector, and semantic-search APIs. GitHub sync indexes actual repository knowledge through the existing BGE/Chroma classes. Signed-in chat displays retrieved snippets and real GitHub sources without generating an AI answer. The static Redis example and graph entities remain labeled sample data.

## Fresh local database (PowerShell)

From `E:\PROJECTS\EKOS`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```

Edit `backend\.env`: set a unique `JWT_SECRET`. SQLite works with the example `POSTGRES_URL=sqlite:///./aekos.db`. To enable real GitHub actions, set `GITHUB_TOKEN`, `GITHUB_OWNER`, and `GITHUB_REPO` to a token with access to that repository and its owner/name. Leave them empty to demonstrate the honest **Not configured** state. Set `CHROMA_PATH=./data/chroma`; `EMBEDDING_MODEL` defaults to `BAAI/bge-base-en-v1.5`. The token stays on the server and is never returned by the connector API. Neo4j variables are placeholders for later graph work and are not required for this demo.

Then seed and start the backend from `backend/`:

```powershell
cd E:\PROJECTS\EKOS\backend
..\.venv\Scripts\python.exe scripts\seed_demo.py
..\.venv\Scripts\python.exe scripts\prepare_embeddings.py
..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

The seed is explicit and idempotent. It creates missing roles, hashed-password demo users, database permissions, and one GitHub connector for ABC Solutions without overwriting existing accounts or secrets. Run it again after changing GitHub configuration, then restart the backend. The optional model preparation command downloads/warm-loads BGE into ignored `backend/data/models` without inserting test documents. It needs network access on first use; CPU indexing may take several minutes.

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
4. Confirm the sync result shows indexed document counts. Sign in as Developer, open New chat, and ask **repository branches** or a query related to the synced README/issues/commits. Chat calls `POST /api/search`, shows loading, renders **Retrieved knowledge**, and fills Context with real GitHub sources. No sample PAY-42/Architecture.md sources are substituted. Empty indexes show a link to Connectors; no matches and API failures have explicit messages. Anonymous new chats prompt sign-in.
5. Visit `/chat/redis` or `/knowledge-graph` for the preserved labeled examples. Their graph data and original sample answers are not live GitHub or Neo4j data; follow-up questions use real search when signed in.

The backend routes also include protected `POST /api/search` and `GET /api/search/status`. JWTs are kept in tab-scoped `sessionStorage`; the backend checks database permissions and filters retrieval to the user's organization and current GitHub connectors. Results are nearest-neighbor snippets, not LLM answers. Chat history and retrieved snippets stay in this browser tab under separate per-user keys. Sync adds a separate indexing result, so a Chroma error does not disguise successful GitHub sync. Neo4j ingestion is not implemented. Jira, Slack, and Confluence remain planned.

## Verification

```powershell
cd E:\PROJECTS\EKOS\backend
..\.venv\Scripts\python.exe -m pytest -q
cd E:\PROJECTS\EKOS\frontend
npm.cmd test
npm.cmd run build
```

For the optional live frontend-to-FastAPI check, run the seeded backend and set test-process-only `EKOS_TEST_EMAIL` and `EKOS_TEST_PASSWORD`, then use `npm.cmd test -- src/liveBackend.test.tsx`. Set `EKOS_TEST_LIVE_SEARCH=1` after a successful GitHub sync to additionally verify actual retrieval and GitHub source rendering. Normal automated tests mock embeddings and GitHub HTTP and do not download BGE. See `backend/scripts/verify_semantic_demo.py --repeat-sync` for the real API flow. No LLM, GraphRAG, reranking, or new connector modules are added.
