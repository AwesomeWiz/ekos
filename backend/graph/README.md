Put this in backend/graph/README.md:

# EKOS Neo4j
This module contains the Neo4j knowledge-graph service for EKOS.
## Local Setup
### 1. Create the environment file
Copy `.env.example` to `.env` and configure the Neo4j credentials.
The `.env` file is local and must not be committed to Git.
### 2. Start Neo4j
From the repository root:
```bash
docker compose --env-file .env -f docker/docker-compose.yml up -d
```
Check that the container is running:
```bash
docker ps
```

3. Neo4j Browser

Open:
http://localhost:7474

The Bolt connection used by the backend is:
bolt://localhost:7687

Python Environment

Create the project’s virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```
Install the Neo4j Python driver:
```bash
python -m pip install neo4j
```

Neo4j Service

The Neo4jService class in neo4j_service.py currently supports:

* Verifying the Neo4j connection
* Creating User nodes
* Creating Repository nodes
* Creating Commit nodes
* Creating Issue nodes
* Creating PullRequest nodes
* Creating Document nodes

Current Graph Structure

The current GitHub graph supports:

User ──COMMITTED──> Commit
                       │
                       │ BELONGS_TO
                       ▼
                   Repository
Issue ──BELONGS_TO──> Repository
PullRequest ──BELONGS_TO──> Repository

Documents are currently stored as Document nodes.

Testing the Connection

From the repository root:

python -c "from backend.graph.neo4j_service import Neo4jService; db = Neo4jService(); print(db.verify_connection()); db.close()"

Expected output:

True

Development Notes

* Neo4j database data is stored in Docker volumes.
* .env contains local credentials and must not be committed.
* .venv contains the local Python environment and must not be committed.
* Generated Python cache files such as __pycache__ must not be committed.
* Graph nodes use MERGE to avoid duplicate entities.