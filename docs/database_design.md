Document 8

Database Design Document

Project: Autonomous Enterprise Knowledge Operating System (AEKOS)

Version: 1.0

Authors

Abhishikth S. Mattom

Arnold Shibu

Alen Abraham Saji

Antony Jose



---

1. Purpose

This document describes the complete data storage architecture of AEKOS.

Unlike traditional applications that use only relational databases, AEKOS uses a polyglot persistence architecture, where different databases are chosen for different types of data.

The system uses:

PostgreSQL – Application data

Neo4j – Knowledge Graph

ChromaDB – Vector Embeddings


Each database has a specific responsibility.


---

2. Database Architecture

Enterprise APIs
                            │
                            ▼
                   Connector Framework
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
     PostgreSQL         Neo4j           ChromaDB
(Application Data) (Relationships) (Semantic Search)
          │                 │                 │
          └─────────────────┼─────────────────┘
                            ▼
                    LangChain GraphRAG
                            │
                            ▼
                         Local LLM


---

3. Why Multiple Databases?

Database	Purpose

PostgreSQL	Stores users, authentication, RBAC, connector configurations, audit logs
Neo4j	Stores relationships between enterprise entities
ChromaDB	Stores vector embeddings for semantic search



---

4. PostgreSQL Design

PostgreSQL stores all application-related structured data.

Main Tables

Users
Roles
Permissions
Organizations
Connectors
ConnectorConfigurations
SyncJobs
AuditLogs
ChatHistory
Settings


---

5. Users Table

Column	Type

id	UUID
full_name	VARCHAR
email	VARCHAR
password_hash	TEXT
role_id	UUID
organization_id	UUID
status	BOOLEAN
created_at	TIMESTAMP


Purpose:

Stores authenticated users.


---

6. Roles Table

Column	Type

id	UUID
role_name	VARCHAR
description	TEXT


Examples

Administrator

Manager

Developer

HR

Guest


---

7. Permissions Table

Column	Type

id	UUID
role_id	UUID
resource	VARCHAR
action	VARCHAR


Example

Developer

↓

GitHub

↓

READ


---

8. Organizations Table

Stores organization metadata.

Columns

id

name

domain

created_at


---

9. Connectors Table

Stores registered connectors.

Columns

id

name

type

status

organization_id

Examples

GitHub

Jira

Slack

Confluence


---

10. Connector Configuration Table

Stores connector settings.

Columns

connector_id

api_url

encrypted_token

sync_interval

last_sync

Sensitive fields should be encrypted.


---

11. Sync Jobs Table

Tracks synchronization.

Columns

id

connector

status

started_at

completed_at

records_processed

error_message


---

12. Audit Logs

Stores system activities.

Examples

Login

Logout

Failed Login

Connector Added

Connector Updated

Synchronization

User Query

Permission Denied



---

13. Chat History

Stores user conversations.

Columns

id

user_id

query

response

timestamp

Future enhancement:

Conversation memory.


---

14. PostgreSQL Relationships

Organization

↓

Users

↓

Roles

↓

Permissions

↓

Chat History


---

15. Neo4j Database Design

Neo4j stores enterprise relationships.

Node Labels

Organization

User

Department

Project

Repository

Commit

Issue

Document

Technology

Service

Incident


---

16. Neo4j Relationships

WORKS_ON

COMMITTED

ASSIGNED_TO

USES

RELATED_TO

AUTHORED

OWNS

BELONGS_TO

DOCUMENTED_IN

DEPENDS_ON


---

17. Example Knowledge Graph

John

↓

WORKS_ON

↓

Payment Service

↓

USES

↓

Redis

↓

RELATED_TO

↓

Issue PAY-42

↓

DOCUMENTED_IN

↓

Architecture Document


---

18. ChromaDB Design

Collection Name

enterprise_documents

Purpose

Stores vector embeddings of textual enterprise knowledge.


---

19. Stored Document Structure

Each record contains:

Document ID

Text Chunk

Embedding

Metadata

Metadata

Source

Connector

Repository

Project

Owner

Role

Timestamp

Chunk Number


---

20. Chunking Strategy

Large documents are divided into smaller chunks before embedding.

Example

Confluence Page

↓

Chunk 1

Chunk 2

Chunk 3

↓

Generate Embeddings

Recommended chunk size:

500–800 tokens

50–100 token overlap


This improves retrieval accuracy.


---

21. Embedding Storage

Model

BAAI bge-base-en-v1.5

Each chunk is converted into a dense vector and stored in ChromaDB.

Example

Chunk

↓

Embedding

↓

Metadata

↓

ChromaDB


---

22. Indexing Strategy

PostgreSQL

Indexes

email

organization_id

role_id

connector_id



---

Neo4j

Indexes

User.email

Project.name

Repository.name

Issue.id

Service.name



---

ChromaDB

Indexed automatically using vector indexes for efficient similarity search.


---

23. Data Flow

Enterprise API

↓

Connector

↓

Transform

↓

Application Metadata → PostgreSQL

↓

Relationships → Neo4j

↓

Text → Chunking

↓

Embeddings

↓

ChromaDB


---

24. Query Flow

User Query

↓

JWT Authentication

↓

RBAC Check (PostgreSQL)

↓

Embedding Generation

↓

ChromaDB Retrieval

↓

Neo4j Retrieval

↓

Merge Context

↓

LLM

↓

Response


---

25. Backup Strategy

PostgreSQL

Daily logical backups

Point-in-time recovery (future)


Neo4j

Scheduled database dumps

Export graph snapshots


ChromaDB

Periodic collection backups

Rebuild from source data if required



---

26. Data Consistency

To ensure consistency across databases:

PostgreSQL is the source of truth for users, roles, and connector configurations.

Neo4j is updated after successful data transformation.

ChromaDB embeddings are regenerated only for new or modified documents.

Failed synchronization jobs are retried without duplicating existing data.



---

27. Security Considerations

Passwords stored using secure hashing (e.g., bcrypt).

Connector credentials encrypted at rest.

Database connections secured using TLS where applicable.

RBAC enforced before any retrieval.

Audit logs maintained for all sensitive operations.



---

28. Performance Optimizations

Batch insert operations during synchronization.

Incremental updates instead of full re-indexing.

Cache frequently executed graph queries.

Generate embeddings only for changed content.

Limit graph traversal depth to improve response times.



---

29. Future Database Enhancements

Redis for caching frequently accessed queries.

Multi-tenant database isolation.

Distributed Neo4j cluster.

Distributed vector database deployment.

Time-series database for monitoring and analytics.



---

30. Summary

The AEKOS database architecture adopts a polyglot persistence approach, selecting the most suitable database for each type of data. PostgreSQL manages application and security data, Neo4j models organizational relationships, and ChromaDB enables semantic retrieval through vector embeddings. Together, these databases provide a scalable, secure, and efficient foundation for the GraphRAG-based enterprise knowledge management .