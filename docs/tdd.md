Document 3

Technical Design Document (TDD)

Project: Autonomous Enterprise Knowledge Operating System (AEKOS)

Version: 1.0

Authors

Abhishikth S. Mattom

Arnold Shibu

Alen Abraham Saji

Antony Jose



---

1. Purpose

This document describes the technical implementation details of AEKOS, including project structure, module design, API specifications, connector interfaces, database interactions, coding standards, and implementation guidelines.

Unlike the PRD, this document focuses on how the system will be built rather than what it does.


---

2. Technology Stack

Layer	Technology

Frontend	React + TypeScript + Tailwind CSS
Backend	FastAPI
API Communication	REST API
Authentication	JWT
Graph Database	Neo4j
Vector Database	ChromaDB
LLM Framework	LangChain
Embedding Model	BAAI bge-base-en-v1.5
Local LLM	Llama 3 / Qwen via Ollama
Scheduler	APScheduler / Celery (Future)
Version Control	Git & GitHub
Containerization	Docker



---

3. High-Level Folder Structure

AEKOS/

├── frontend/
│   ├── src/
│   ├── components/
│   ├── pages/
│   ├── hooks/
│   ├── services/
│   ├── layouts/
│   ├── assets/
│   └── App.tsx
│
├── backend/
│   ├── api/
│   ├── auth/
│   ├── connectors/
│   ├── graph/
│   ├── vector_db/
│   ├── ai/
│   ├── services/
│   ├── models/
│   ├── middleware/
│   ├── utils/
│   ├── scheduler/
│   └── main.py
│
├── docs/
│
├── docker/
│
├── scripts/
│
└── README.md


---

4. Frontend Module Design

Authentication Module

Responsibilities

Login

Logout

Session Handling

JWT Storage



---

Dashboard

Displays

Connected Connectors

Synchronization Status

Recent Queries

User Information



---

Chat Interface

Functions

Accept user queries

Display AI responses

Show source references

Display access denied messages



---

Connector Management

Administrator can

Add connector

Remove connector

Test connection

Configure sync

View connector status



---

User Management

Administrator can

Add users

Delete users

Assign roles

Reset passwords



---

5. Backend Module Design

API Module

Handles

Incoming REST requests

Request validation

Response formatting



---

Authentication Module

Responsibilities

Verify credentials

Generate JWT

Validate tokens

Password hashing


Libraries

python-jose

bcrypt

FastAPI Security


---

RBAC Module

Responsibilities

Permission checking

Role verification

Access filtering


Example

Developer

↓

Can Access

GitHub

Jira

Confluence


---

Connector Module

Responsibilities

Authentication

Fetch data

Incremental sync

Error handling


Each connector inherits from

BaseConnector


---

AI Module

Contains

Embedding generation

Vector retrieval

Graph retrieval

Prompt generation

LLM interaction



---

Logging Module

Stores

Login attempts

Connector events

Queries

Errors

Synchronization logs



---

6. Backend Package Structure

backend/

api/

auth/

connectors/

graph/

vector_db/

llm/

embeddings/

services/

middleware/

scheduler/

models/

utils/


---

7. Connector Interface

Every connector implements

class BaseConnector:

    def authenticate()

    def fetch_data()

    def transform()

    def sync()

    def disconnect()


---

8. Supported Connectors

Initial

GitHub

Jira


Future

Slack

Confluence

Notion

GitLab

ERP

CRM

Custom Connectors



---

9. API Endpoints

Authentication

POST

/api/login

POST

/api/logout

GET

/api/profile


---

Chat

POST

/api/chat

GET

/api/history


---

Connectors

GET

/api/connectors

POST

/api/connectors

PUT

/api/connectors/{id}

DELETE

/api/connectors/{id}


---

Synchronization

POST

/api/sync

GET

/api/sync/status


---

Administration

GET

/api/users

POST

/api/users

PUT

/api/users/{id}

DELETE

/api/users/{id}


---

10. Request Flow

React

↓

FastAPI

↓

Authentication

↓

RBAC

↓

LangChain

↓

Embedding

↓

ChromaDB

↓

Neo4j

↓

LLM

↓

Response

↓

Frontend


---

11. Embedding Module

Model

BAAI

bge-base-en-v1.5

Input

Document

Query

Output

Dense Vector


---

12. ChromaDB Module

Collection

enterprise_documents

Metadata

source

connector

title

owner

role

timestamp

entity

department


---

13. Neo4j Module

Stores

Nodes

User

Repository

Project

Issue

Service

Document

Department

Relationships

WORKS_ON

ASSIGNED_TO

RELATED_TO

OWNS

USES

CREATED

AUTHORED


---

14. LangChain Pipeline

Pipeline

Receive Query

↓

Generate Embedding

↓

Vector Retrieval

↓

Graph Retrieval

↓

Merge Context

↓

Prompt Builder

↓

LLM

↓

Response


---

15. Prompt Template

System Prompt

You are an enterprise AI assistant.

Only answer using the supplied context.

If the answer is unavailable, say so.

------------------------

Context

{retrieved_documents}

Graph Relationships

{graph_context}

Question

{query}


---

16. Error Handling Strategy

Connector Failure

↓

Retry

↓

Log

↓

Continue


---

Database Failure

↓

Return Friendly Error

↓

Log Exception


---

LLM Failure

↓

Retry

↓

Fallback Response


---

Authentication Failure

↓

401 Unauthorized


---

Permission Failure

↓

403 Forbidden


---

17. Logging Strategy

Store

User Login

Query

Connector Sync

Errors

Admin Actions

API Requests

Performance Metrics



---

18. Configuration Management

Environment Variables

JWT_SECRET

OLLAMA_URL

NEO4J_URI

NEO4J_USER

NEO4J_PASSWORD

CHROMA_PATH

EMBEDDING_MODEL

LLM_MODEL

GITHUB_TOKEN

JIRA_API_KEY


---

19. Coding Standards

Backend

Follow PEP 8

Type hints

Modular services

Dependency injection

Async endpoints where appropriate


Frontend

Functional components

Reusable UI

React Hooks

Strong typing with TypeScript



---

20. Git Branch Strategy

main

develop

feature/github-connector

feature/chat-ui

feature/rbac

feature/graphrag

bugfix/*


---

21. Testing Strategy

Unit Testing

Authentication

Connectors

Graph Builder

Embedding Module

RBAC


Integration Testing

GitHub → Neo4j

GitHub → ChromaDB

LangChain → Ollama


End-to-End Testing

User Login

↓

Ask Question

↓

Retrieve Documents

↓

Generate Response


---

22. Performance Considerations

Cache frequently accessed graph queries.

Perform incremental synchronization instead of full refresh.

Generate embeddings only for new or updated documents.

Paginate connector data retrieval.

Use asynchronous API calls where possible.



---

23. Security Considerations

Store credentials securely using environment variables.

Validate all API inputs.

Enforce RBAC before retrieval.

Never expose connector secrets to the frontend.

Log security-related events for auditing.



---

24. Future Technical Improvements

Background worker queues using Celery.

Redis caching layer.

WebSocket support for live updates.

Graph visualization dashboard.

Multi-tenant architecture.

Kubernetes deployment.

Automated CI/CD pipeline.



---

25. Summary

This Technical Design Document defines the implementation blueprint for AEKOS. It specifies the project structure, module responsibilities, API design, connector architecture, AI pipeline integration, testing strategy, coding practices, and security guidelines. It serves as the reference for all developers during implementation, ensuring a consistent, maintainable, and scalable codebase.