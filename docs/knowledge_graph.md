Document 6

Knowledge Graph Design Document

Project: Autonomous Enterprise Knowledge Operating System (AEKOS)

Version: 1.0

Authors

Abhishikth S. Mattom

Arnold Shibu

Alen Abraham Saji

Antony Jose



---

1. Purpose

This document defines the design and implementation of the Knowledge Graph used in AEKOS.

The Knowledge Graph is responsible for representing organizational knowledge as nodes and relationships, enabling GraphRAG to understand not only documents but also how people, projects, repositories, issues, services, and documentation are connected.

Unlike a relational database, the Knowledge Graph emphasizes relationships, allowing the system to answer contextual questions that traditional search cannot.


---

2. Why a Knowledge Graph?

Enterprise knowledge is inherently connected.

For example,

Developers work on repositories.

Repositories contain services.

Services are linked to Jira issues.

Jira issues are discussed in Slack.

Solutions are documented in Confluence.


A Knowledge Graph models these relationships explicitly.

Example:

John
 │
WORKED_ON
 │
Payment Service
 │
RELATED_TO
 │
Jira Issue PAY-42
 │
DISCUSSED_IN
 │
Slack Thread
 │
DOCUMENTED_IN
 │
Confluence Page

This enables the AI to reason over connected information instead of isolated documents.


---

3. Why Neo4j?

Neo4j was selected because it provides:

Native graph storage

Fast graph traversal

Cypher query language

Excellent visualization

Efficient handling of highly connected data

Easy integration with Python and LangChain


Alternative databases considered:

Database	Reason Not Selected

PostgreSQL	Poor graph traversal performance
MongoDB	Document-oriented, not relationship-oriented
ArangoDB	Smaller ecosystem
JanusGraph	More complex deployment



---

4. Knowledge Graph Architecture

Enterprise APIs
(GitHub, Jira, Slack, Confluence)
            │
            ▼
     Connector Framework
            │
            ▼
    Data Transformation
            │
            ▼
   Entity Extraction Layer
            │
            ▼
 Relationship Extraction
            │
            ▼
        Neo4j Graph
            │
            ▼
      GraphRAG Retrieval


---

5. Node Types

The Knowledge Graph contains the following node labels.

Organization

Represents an organization using AEKOS.

Properties

id
name
domain


---

User

Represents employees.

Properties

id
name
email
role
department


---

Department

Examples

Engineering

HR

Finance

Marketing


---

Repository

Properties

id
name
description
url
language


---

Project

Examples

Payment System

Customer Portal

HRMS


---

Service

Examples

Authentication Service

Payment Service

Notification Service


---

Issue

Represents

Bug

Task

Story

Epic


Properties

id
title
status
priority


---

Commit

Properties

hash
message
timestamp


---

Pull Request

Properties

number
title
status


---

Document

Represents

Confluence pages

PDFs

SOPs

README

Wiki


Properties

title
source
created


---

Technology

Examples

Redis

Docker

Neo4j

React


---

Meeting

Represents

Meeting notes

Minutes

Discussions



---

Incident

Examples

Payment Timeout

Server Crash

Authentication Failure


---

6. Relationship Types

Relationship	Description

WORKS_ON	User works on Project
OWNS	User owns Repository/Service
COMMITTED	User created Commit
BELONGS_TO	Commit belongs to Repository
ASSIGNED_TO	Issue assigned to User
RELATED_TO	Generic relationship between entities
USES	Service uses Technology
DEPENDS_ON	Service dependency
AUTHORED	User authored Document
CREATED	User created Issue/PR
DOCUMENTED_IN	Service described in Document
DISCUSSED_IN	Issue discussed in Slack
PART_OF	Entity belongs to larger entity



---

7. Example Graph

John
 │
COMMITTED
 │
Commit abc123
 │
BELONGS_TO
 │
Payment Repository
 │
CONTAINS
 │
Payment Service
 │
USES
 │
Redis
 │
RELATED_TO
 │
PAY-42
 │
DOCUMENTED_IN
 │
Architecture Document


---

8. Graph Construction Pipeline

Connector

↓

Fetch API Data

↓

Transform

↓

Extract Entities

↓

Extract Relationships

↓

Merge Duplicate Nodes

↓

Create Neo4j Nodes

↓

Create Relationships


---

9. Entity Extraction

During ingestion, connectors identify entities such as:

Example GitHub Commit

Author

Repository

Branch

Commit

Issue Number

Technology Mentioned

Example Jira Ticket

Reporter

Assignee

Project

Issue

Sprint

Labels

Example Slack Message

User

Channel

Mentioned Service

Mentioned Technology

These become graph nodes.


---

10. Relationship Extraction

Example GitHub Commit

John fixed Redis timeout in Payment Service.

Extracted relationships:

John
COMMITTED
Commit

Commit
RELATED_TO
Payment Service

Payment Service
USES
Redis


---

11. Graph Normalization

To avoid duplicates:

Merge identical users by email.

Merge repositories by repository ID.

Merge issues by issue key.

Merge documents by source ID.


Neo4j MERGE will be used instead of CREATE where appropriate.


---

12. Sample Cypher Queries

Find developers working on a project

MATCH (u:User)-[:WORKS_ON]->(p:Project {name:"Payment System"})
RETURN u.name;


---

Find all issues related to a service

MATCH (s:Service {name:"Payment Service"})-[:RELATED_TO]->(i:Issue)
RETURN i.title;


---

Find technologies used by a service

MATCH (s:Service)-[:USES]->(t:Technology)
WHERE s.name="Payment Service"
RETURN t.name;


---

Find documentation for a service

MATCH (s:Service)-[:DOCUMENTED_IN]->(d:Document)
RETURN d.title;


---

13. Graph Traversal Strategy

GraphRAG retrieves not only the starting node but also its connected entities.

Traversal depth is typically limited (e.g., 2–3 hops) to avoid retrieving unrelated information.

Example:

Payment Service

↓

Issue

↓

Developer

↓

Commit

↓

Repository

↓

Documentation

This provides richer context without exploring the entire graph.


---

14. Integration with GraphRAG

When a user submits a query:

Who fixed the Payment Service bug?

GraphRAG performs:

1. Semantic retrieval from ChromaDB.


2. Entity identification (Payment Service).


3. Cypher query to retrieve connected nodes.


4. Graph traversal for related developers, commits, issues, and documents.


5. Merge graph context with retrieved documents.


6. Pass combined context to the LLM.




---

15. Example Query Flow

User Query

Why was Redis introduced?

Retrieved graph:

Redis

↓

USED_BY

↓

Payment Service

↓

RELATED_TO

↓

Issue PAY-42

↓

COMMIT abc123

↓

Developer John

↓

Architecture Document

The LLM receives both the graph relationships and the document contents, enabling a complete answer.


---

16. Performance Considerations

Create indexes on frequently queried properties (id, name, email).

Use MERGE to avoid duplicate nodes.

Batch node and relationship creation during synchronization.

Limit traversal depth for interactive queries.

Cache frequently used graph queries where appropriate.



---

17. Future Enhancements

Automatic relationship extraction using NLP.

Confidence scores for inferred relationships.

Graph visualization dashboard.

Temporal relationships for historical analysis.

Cross-organization knowledge graphs (multi-tenant mode).

Event-based graph updates using webhooks.



---

18. Summary

The Knowledge Graph is the structural backbone of AEKOS. It models enterprise entities and their relationships, enabling GraphRAG to retrieve context that extends beyond individual documents. Combined with ChromaDB's semantic search, Neo4j allows the system to generate accurate, explainable, and relationship-aware responses while remaining scalable and adaptable to different organizational domains.