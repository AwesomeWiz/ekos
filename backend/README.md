# EKOS backend demo

FastAPI, SQLAlchemy, JWT auth, persisted connectors, database permissions, and the existing GitHub connector power the 30% demo. Python 3.11+ is required; the local setup was verified with Python 3.12.14.

## Fresh setup (PowerShell, from repository root)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```

Set a unique `JWT_SECRET` in `backend\.env`. The example `POSTGRES_URL=sqlite:///./aekos.db` creates a local SQLite database. For PostgreSQL, set `POSTGRES_URL` to your existing database URL. Set `GITHUB_TOKEN`, `GITHUB_OWNER`, and `GITHUB_REPO` for a repository the token can read. Keep credentials only in the server environment file; the seed does not put the GitHub token in the database. With these values empty, GitHub is seeded as **not_configured** and test/sync return 409. `CORS_ORIGINS` contains the two default Vite origins. Set `CHROMA_PATH=./data/chroma` and optionally `EMBEDDING_MODEL=BAAI/bge-base-en-v1.5`. Neo4j and LLM settings remain future-stage placeholders.

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
| POST | `/api/search` | Semantic retrieval of indexed GitHub documents; `connectors:read` |
| GET | `/api/search/status` | Accessible document count and configured embedding model; `connectors:read` |

Test returns the authenticated GitHub account. Sync returns the repository, default branch, branch/commit/issue counts, and timestamp; it updates connector status and `last_sync`. It then indexes the actual normalized data through the teammate `BGEEmbeddingService` and `ChromaService`, adding an `indexing` summary to the existing response. Indexing errors are logged and returned separately while remote sync stays successful. A partial indexing failure may leave some upserted documents; retrying Sync safely updates them. The API never returns the token. GitHub API/network failures return 502 with a safe message. Tenant ownership is checked for connector actions. Neo4j has node-writing helpers but no complete GitHub ingestion or graph-read path, so sync does not claim graph persistence.

## Semantic knowledge demo

`chromadb` and `sentence-transformers` are declared in requirements. The first indexing request loads/downloads BGE (several hundred MB); subsequent calls reuse the model in memory. Weights are cached under ignored `backend/data/models`; Chroma persists at the configured path. You can download/warm the model before starting the demo without inserting fixture documents:

```powershell
cd E:\PROJECTS\EKOS\backend
..\.venv\Scripts\python.exe scripts\prepare_embeddings.py
```

Initial setup needs network access to the public Hugging Face model. A separate Hugging Face token is not required for this public model. Cached operation works without downloading the weights again. CPU operation is supported; first sync can take several minutes. If changing the embedding model, use a fresh `CHROMA_PATH` and sync again so stored vectors and query vectors use the same model.

Indexing creates repository documents (description, default branch, fetched branch names), decoded README documents, commit-message documents, and issue-title/body documents. Pull requests already returned by GitHub's issue endpoint are identified as such. No comments or other unsupported records are invented. Long text uses approximately 2,000-character chunks with 200-character overlap. IDs are deterministic: `github:<organization_id>:<connector_id>:<repository>:<entity_type>:<entity_id>`, with `:chunk:<index>` for long text. Repository and README IDs omit the redundant entity ID suffix. Repeated sync upserts existing documents; obsolete chunks of updated entities are pruned. This is a snapshot of the records the existing connector fetches, not a new pagination or full-history ingestion pipeline.

Metadata contains primitive values: `source`, `connector`, `connector_id`, `organization_id`, `repository`, `entity_type`, `entity_id`, `title`, `url`, and `chunk_index`. Both IDs and search filters isolate organizations. Search additionally filters to existing connectors belonging to the authenticated user's organization, excluding orphaned/deleted connectors and old unscoped records. Both seeded roles can search through their existing connector-read grant; Administrator alone can sync.

`POST /api/search` accepts `{"query":"repository branches","top_k":5}`. It returns `query`, accessible `document_count`, and normalized `results` containing `document_id`, `text`, `metadata`, and cosine `distance`. It does not call an LLM or guarantee that a nearest neighbor answers the question. Empty indexes return an empty results list without loading BGE. Unavailable storage/model setup returns 503. `GET /api/search/status` returns `collection`, accessible `document_count`, and `embedding_model`.

With the backend running and GitHub configured, verify real sync, repeat-sync idempotence, Developer RBAC, index status, and search:

```powershell
..\.venv\Scripts\python.exe scripts\verify_semantic_demo.py --repeat-sync
```

The script uses documented demo accounts by default; optional `EKOS_ADMIN_EMAIL`, `EKOS_ADMIN_PASSWORD`, `EKOS_TEST_EMAIL`, and `EKOS_TEST_PASSWORD` override them. It indexes actual GitHub data and inserts no test documents. Then sign into the frontend as Developer and ask **repository branches**. Chat shows retrieved snippets and real GitHub context sources. The static Redis example and graph remain labeled sample data. No LLM, GraphRAG, reranking, or Neo4j/Chroma fusion is implemented.

To demonstrate RBAC, log in as Developer and observe GitHub in GET, then call POST test/sync and receive 403. Log in as Administrator and run test/sync. When GitHub env vars are absent, admin receives 409; with valid credentials and network, test/sync invoke GitHub. Swagger is available at `http://127.0.0.1:8000/docs`.

## Tests

```powershell
cd E:\PROJECTS\EKOS\backend
..\.venv\Scripts\python.exe -m pytest -q
```

Tests cover auth, profile permissions, seed idempotence, RBAC, GitHub adapters, indexing IDs/chunking, upsert/pruning, real temporary Chroma add/search/persistence, scoped retrieval, and indexing failures. Embedding generation and GitHub network calls are mocked in normal tests; no model downloads or production collection writes occur.
