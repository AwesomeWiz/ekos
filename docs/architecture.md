Document 2

System Architecture Document

Project: Autonomous Enterprise Knowledge Operating System (AEKOS)

Version: 1.0

Authors

Abhishikth S. Mattom

Arnold Shibu

Alen Abraham Saji

Antony Jose



---

1. Purpose

This document describes the complete system architecture of AEKOS, including all major components, data flow, AI pipeline, connector framework, security mechanisms, and deployment architecture.

The objective is to provide a scalable, modular, and domain-independent architecture that enables organizations to integrate knowledge from multiple enterprise systems and retrieve it through AI-powered natural language queries.


---

2. High-Level Architecture

Users
                        │
                        ▼
               React Frontend (UI)
                        │
                        ▼
                 FastAPI Backend
                        │
      ┌─────────────────┼─────────────────┐
      │                 │                 │
      ▼                 ▼                 ▼
 Authentication      RBAC Engine     Connector Manager
      │                 │                 │
      └─────────────────┼─────────────────┘
                        ▼
                LangChain Orchestrator
                        │
      ┌─────────────────┼─────────────────┐
      │                 │                 │
      ▼                 ▼                 ▼
Embedding Model      ChromaDB         Neo4j
 (BAAI BGE)       Vector Search    Knowledge Graph
      │                 │                 │
      └─────────────────┼─────────────────┘
                        ▼
                 Context Builder
                        ▼
                 Local LLM (Llama/Qwen)
                        ▼
                  Generated Response
                        ▼
                     Frontend


---

3. System Components

The architecture consists of seven major layers:

1. Presentation Layer


2. Application Layer


3. Security Layer


4. Connector Layer


5. Data Layer


6. AI Layer


7. Infrastructure Layer




---

4. Presentation Layer

Technology:

React

TypeScript

Tailwind CSS


Responsibilities:

User Login

Dashboard

Chat Interface

Connector Management

User Management

Search Interface

Administration Panel


The frontend communicates with the backend exclusively through REST APIs.

No AI processing occurs on the client.


---

5. Backend Layer

Technology

FastAPI


Responsibilities

API Gateway

Authentication

Authorization

Connector Management

Query Processing

LangChain Integration

Database Communication

Logging

Error Handling


The backend acts as the central controller of the entire platform.


---

6. Authentication Layer

Purpose

Verify user identity before any request is processed.

Technology

JWT

OAuth (future)

LDAP / Microsoft Entra ID (future)


Flow

Login

↓

Verify Credentials

↓

Generate JWT

↓

Return Token

Example JWT

{
  "userId":"101",
  "role":"Developer",
  "department":"Engineering"
}


---

7. Authorization Layer (RBAC)

Purpose

Restrict enterprise knowledge according to organizational permissions.

Example

Developer

↓

Can Access

GitHub
Jira
Confluence

Cannot Access

HR Records
Finance Documents

RBAC is always enforced before retrieval.

The LLM never receives unauthorized information.


---

8. Connector Framework

Purpose

Collect organizational knowledge from external systems.

Supported Connectors

GitHub

Jira

Slack

Confluence

Notion

GitLab

ERP

CRM

Custom Connectors


Every connector implements a common interface.

connect()

authenticate()

fetch()

transform()

sync()

disconnect()


---

9. Connector Workflow

Administrator

↓

Configure Connector

↓

Authentication

↓

Fetch Data

↓

Transform Data

↓

Unified Data Model

↓

Knowledge Graph

+

Vector Database


---

10. Data Synchronization

Synchronization Modes

Manual

Scheduled

Incremental


Future

Webhooks

Event Streaming


Synchronization updates only modified records.


---

11. Unified Data Model

Every connector converts its data into a common representation.

Example

Employee

Project

Repository

Issue

Document

Service

Meeting

Department

Relationships

WORKS_ON

ASSIGNED_TO

CREATED

RELATED_TO

USES

DEPENDS_ON

OWNS

AUTHORED

This abstraction allows GraphRAG to remain independent of the original data source.


---

12. Knowledge Graph (Neo4j)

Purpose

Store relationships.

Example

John

↓

WORKED_ON

↓

Payment Service

↓

RELATED_TO

↓

Issue-45

↓

DOCUMENTED_IN

↓

Architecture Page

Benefits

Relationship discovery

Dependency analysis

Organizational memory

Explainability



---

13. Vector Database (ChromaDB)

Purpose

Store semantic embeddings.

Stores

Documents

Slack messages

Jira tickets

Confluence pages

README files

Source code documentation


Each document contains

Embedding

Metadata

Source

Timestamp

Connector

Permissions


---

14. Embedding Model

Model

BAAI bge-base-en-v1.5

Purpose

Convert enterprise text into dense vectors.

Why chosen?

Open source

Optimized for retrieval

Excellent semantic accuracy

Compatible with ChromaDB

Runs locally



---

15. AI Orchestration (LangChain)

LangChain connects all AI components.

Responsibilities

Query processing

Embedding generation

ChromaDB retrieval

Neo4j retrieval

Prompt construction

LLM invocation

Response parsing


LangChain is the orchestration layer, not the reasoning engine.


---

16. GraphRAG Pipeline

Complete Flow

User Query

↓

Authentication

↓

RBAC

↓

Generate Query Embedding

↓

Semantic Search

↓

Graph Traversal

↓

Merge Context

↓

Prompt Construction

↓

Local LLM

↓

Final Response


---

17. Example Query Flow

User asks

> Who fixed the Payment Service bug and why was Redis introduced?



Step 1

Embedding Model converts query into vectors.

↓

Step 2

Cosine Similarity retrieves

Jira Issue

GitHub Commit

Slack Discussion

Confluence Page


↓

Step 3

Neo4j retrieves

Developer

↓

Commit

↓

Project

↓

Issue

↓

Architecture

↓

Step 4

GraphRAG combines

Documents


Relationships

↓

Step 5

RBAC filters unauthorized information.

↓

Step 6

LLM generates response.


---

18. Local LLM

Supported Models

Llama 3

Qwen

Mistral


Deployment

Ollama

Responsibilities

Natural language understanding

Reasoning

Summarization

Response generation


The LLM does not access enterprise databases directly.


---

19. Prompt Construction

LangChain builds prompts using

System Prompt

+

Retrieved Documents

+

Graph Relationships

+

User Query

Example

Context

GitHub Commit

Jira Issue

Slack Discussion

Graph Relationships

Question

Who fixed the Payment Service bug?


---

20. Response Generation

Output contains

Natural language answer

Contextual explanation

Source references (where applicable)


Future enhancement

Confidence scores.


---

21. Security Architecture

Implemented

JWT Authentication

RBAC

HTTPS

Local LLM

Audit Logs

Secure Connector Credentials


Future

MFA

OAuth

LDAP

Encryption at Rest



---

22. Deployment Architecture

Client

↓

React

↓

FastAPI

↓

Neo4j

ChromaDB

Ollama

↓

Enterprise APIs

Everything can run on a single machine for development.

Production deployment can separate each service.


---

23. Scalability Strategy

Horizontal Scaling

Multiple backend instances

Multiple connector workers

Dedicated embedding workers


Vertical Scaling

Larger Neo4j instance

Larger ChromaDB

GPU-based LLM server



---

24. Fault Tolerance

Connector Failure

↓

Retry

↓

Log Error

↓

Continue Remaining Connectors

System should never stop because one connector fails.


---

25. Architectural Decisions

Decision	Reason

FastAPI	High-performance Python backend with excellent AI ecosystem support
React	Modern, component-based frontend framework
Neo4j	Efficient storage and traversal of entity relationships
ChromaDB	Lightweight vector database optimized for semantic search
LangChain	Orchestrates retrieval, prompting, and LLM interaction
BAAI BGE	High-quality open-source embedding model for RAG applications
Ollama + Local LLM	Privacy-preserving, offline AI inference
RBAC	Ensures users only access authorized organizational knowledge
Modular Connector Framework	Enables integration with both standard and custom enterprise tools
GraphRAG	Combines semantic retrieval and graph relationships for more accurate and explainable responses



---

26. Future Architectural Enhancements

Multi-tenant architecture

Distributed connector workers

Event-driven synchronization using webhooks

Agentic AI workflows

Multi-modal document processing

Kubernetes deployment

Cloud-native scaling

Hybrid cloud/local LLM support

Real-time analytics dashboard



---

27. Summary

The AEKOS architecture is designed to be modular, scalable, secure, and domain-independent. By combining Knowledge Graphs (Neo4j), Vector Databases (ChromaDB), GraphRAG, LangChain, and Local LLMs, the platform enables intelligent and secure retrieval of enterprise knowledge. The modular connector framework allows organizations to integrate both standard enterprise tools and proprietary systems without changing the core architecture.