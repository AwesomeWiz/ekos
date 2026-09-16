Document 10

Development Guide

Project: Autonomous Enterprise Knowledge Operating System (AEKOS)

Version: 1.0

Authors

Abhishikth S. Mattom

Arnold Shibu

Alen Abraham Saji

Antony Jose



---

1. Purpose

This document provides a complete guide for developers to set up, build, run, test, and contribute to the AEKOS project.

It serves as the onboarding guide for new team members and ensures a consistent development workflow.


---

2. Development Environment

Recommended Hardware

Quad-core CPU or better

16 GB RAM (minimum 8 GB)

50 GB free storage

Stable internet connection


Operating System

Ubuntu 22.04 LTS (Recommended)

Windows 11

macOS Ventura or later



---

3. Software Requirements

Software	Version

Node.js	20+
Python	3.11+
Git	Latest
Docker	Latest
Neo4j	5.x
Ollama	Latest
PostgreSQL	16+
VS Code	Latest



---

4. Technology Stack

Frontend

React

TypeScript

Vite

Tailwind CSS

React Router

Axios


Backend

FastAPI

SQLAlchemy

Pydantic

LangChain

Sentence Transformers

JWT Authentication


Databases

PostgreSQL

Neo4j

ChromaDB


AI

Ollama

Llama 3 / Qwen

BAAI bge-base-en-v1.5



---

5. Repository Structure

AEKOS/
│
├── frontend/
├── backend/
├── docs/
├── docker/
├── scripts/
├── tests/
├── .env.example
├── docker-compose.yml
└── README.md


---

6. Backend Structure

backend/

api/
auth/
connectors/
graph/
vector_db/
llm/
embeddings/
services/
scheduler/
middleware/
models/
schemas/
utils/
config/
main.py


---

7. Frontend Structure

frontend/

src/

components/

pages/

layouts/

hooks/

services/

context/

assets/

types/

utils/


---

8. Initial Setup

Clone Repository

git clone https://github.com/<organization>/AEKOS.git

cd AEKOS


---

Backend Setup

cd backend

python -m venv venv

source venv/bin/activate

pip install -r requirements.txt


---

Frontend Setup

cd frontend

npm install


---

9. Running Services

Start Frontend

npm run dev

Runs at:

http://localhost:5173


---

Start Backend

uvicorn main:app --reload

Runs at:

http://localhost:8000


---

Start Neo4j

docker compose up neo4j

Neo4j Browser

http://localhost:7474


---

Start Ollama

ollama serve

Download model

ollama pull llama3

or

ollama pull qwen3


---

10. Environment Variables

Example .env

JWT_SECRET=your-secret-key

POSTGRES_URL=postgresql://...

NEO4J_URI=bolt://localhost:7687

NEO4J_USERNAME=neo4j

NEO4J_PASSWORD=password

CHROMA_PATH=./chroma

OLLAMA_URL=http://localhost:11434

LLM_MODEL=llama3

EMBEDDING_MODEL=BAAI/bge-base-en-v1.5

GITHUB_TOKEN=

JIRA_API_TOKEN=

Never commit the .env file to Git.


---

11. Git Workflow

Branches

main

develop

feature/*

bugfix/*

hotfix/*

Example

feature/github-connector

feature/chat-ui

feature/rbac

feature/graphrag


---

12. Development Workflow

Create Feature Branch

↓

Develop Feature

↓

Unit Testing

↓

Commit Changes

↓

Push Branch

↓

Pull Request

↓

Code Review

↓

Merge into develop

↓

Merge into main (after testing)


---

13. Commit Message Convention

Examples

feat: add GitHub connector

fix: resolve JWT authentication bug

docs: update architecture documentation

refactor: simplify graph builder

test: add RBAC unit tests


---

14. Coding Standards

Python

Follow PEP 8.

Use type hints.

Keep functions small and focused.

Add docstrings for public functions.

Prefer asynchronous endpoints for I/O-bound operations.


TypeScript

Use strict typing.

Prefer functional React components.

Keep components reusable.

Avoid duplicated logic.



---

15. API Development Guidelines

Validate all request bodies using Pydantic.

Return consistent JSON responses.

Use appropriate HTTP status codes.

Handle exceptions centrally.

Protect sensitive endpoints with JWT.



---

16. Connector Development Guide

Each connector should:

1. Authenticate with the external service.


2. Fetch data incrementally.


3. Transform data into the unified model.


4. Generate embeddings for textual content.


5. Update Neo4j and ChromaDB.


6. Log synchronization status.




---

17. Testing Strategy

Unit Tests

Test:

Authentication

RBAC

Connectors

Embedding generation

Graph builder


Integration Tests

Test:

GitHub → Neo4j

GitHub → ChromaDB

LangChain → Ollama


End-to-End Tests

Verify the full workflow:

Login
↓

Ask Question
↓

Retrieve Data
↓

Generate Response
↓

Display Answer


---

18. Logging

Application logs should include:

API requests

Authentication events

Connector synchronization

Errors and exceptions

LLM requests

Performance metrics


Recommended logging library:

logging

or

loguru


---

19. Debugging

Useful tools:

FastAPI Swagger UI (/docs)

Neo4j Browser

ChromaDB inspection

Browser Developer Tools

VS Code Debugger



---

20. Docker Deployment

Use Docker Compose to run:

Frontend

Backend

PostgreSQL

Neo4j

Ollama (optional)

ChromaDB


Benefits:

Consistent development environment

Easy setup for new contributors

Simplified deployment



---

21. Continuous Integration (Future)

Planned CI pipeline:

1. Run linting


2. Execute unit tests


3. Build frontend


4. Build backend


5. Run integration tests


6. Generate documentation


7. Deploy to staging



Potential tools:

GitHub Actions

Docker Hub

SonarQube



---

22. Deployment Strategy

Development

Local machine

Docker Compose


Staging

Cloud VM

Test data


Production

Reverse proxy (Nginx)

HTTPS

Dedicated Neo4j and PostgreSQL

Local or GPU-based LLM server



---

23. Troubleshooting

Issue	Possible Solution

Backend not starting	Check Python version and dependencies
Frontend cannot connect	Verify backend URL and CORS settings
Neo4j connection fails	Confirm Neo4j is running and credentials are correct
ChromaDB errors	Check database path and permissions
LLM not responding	Ensure Ollama service is running and the model is downloaded
Connector authentication fails	Verify API tokens and permissions



---

24. Best Practices

Pull the latest changes before starting work.

Keep feature branches small and focused.

Write clear commit messages.

Test locally before creating a pull request.

Do not hardcode secrets or API keys.

Document new modules and APIs as they are developed.



---

25. Summary

This Development Guide establishes the standard workflow for building and maintaining AEKOS. It covers environment setup, project structure, coding standards, Git practices, testing, deployment, and troubleshooting. Following these guidelines will help the team collaborate effectively and maintain a consistent, scalable, and high-quality codebase.