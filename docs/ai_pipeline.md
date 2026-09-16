Document 7

AI Pipeline Design Document

Project: Autonomous Enterprise Knowledge Operating System (AEKOS)

Version: 1.0

Authors

Abhishikth S. Mattom

Arnold Shibu

Alen Abraham Saji

Antony Jose



---

1. Purpose

This document defines the Artificial Intelligence pipeline of AEKOS, explaining how enterprise data is transformed into searchable knowledge and how natural language queries are processed to generate accurate, explainable, and secure responses.

The AI pipeline combines:

Semantic Search

Knowledge Graph Retrieval

GraphRAG

Local Large Language Models

Role-Based Access Control


to deliver enterprise-aware question answering.


---

2. AI Pipeline Overview

Enterprise Data
                      │
                      ▼
              Connector Framework
                      │
                      ▼
          Document Preprocessing
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
Generate Embeddings          Extract Entities
        │                           │
        ▼                           ▼
    ChromaDB                    Neo4j Graph
        │                           │
        └─────────────┬─────────────┘
                      ▼
               LangChain GraphRAG
                      │
                      ▼
             Prompt Construction
                      │
                      ▼
                Local LLM (Ollama)
                      │
                      ▼
              AI Generated Response


---

3. AI Technologies Used

Component	Technology

Embedding Model	BAAI bge-base-en-v1.5
Vector Database	ChromaDB
Knowledge Graph	Neo4j
AI Orchestration	LangChain
Retrieval Method	GraphRAG
Similarity Metric	Cosine Similarity
LLM	Llama 3 / Qwen (via Ollama)



---

4. Complete AI Workflow

User Query

↓

Authentication

↓

RBAC Validation

↓

Generate Query Embedding

↓

Vector Search (ChromaDB)

↓

Knowledge Graph Search (Neo4j)

↓

Merge Retrieved Context

↓

Prompt Construction

↓

Local LLM

↓

Generate Response

↓

Return Answer


---

5. Document Ingestion Pipeline

Before users can ask questions, enterprise data must be processed.

Enterprise APIs

↓

Raw Data

↓

Cleaning

↓

Chunking

↓

Embedding Generation

↓

Store in ChromaDB

+

Extract Entities

↓

Create Neo4j Graph


---

6. Data Preprocessing

Each retrieved document undergoes preprocessing.

Operations include:

Remove unsupported formatting

Normalize text encoding

Extract metadata

Split large documents into chunks

Preserve source information


Example:

README.md

↓

Split into 500-token chunks

↓

Each chunk receives metadata

↓

Generate embeddings


---

7. Embedding Generation

Model

BAAI bge-base-en-v1.5

Purpose

Convert text into dense vector representations.

Input

Project documentation

Slack messages

Jira tickets

GitHub commits

Confluence pages

Output

768-dimensional vector (model-dependent)

These vectors capture semantic meaning rather than exact keywords.


---

8. Why BAAI BGE?

Reasons for selection:

Optimized for Retrieval-Augmented Generation (RAG)

High semantic retrieval accuracy

Open source

Local deployment

Fast inference

Well supported by LangChain

Compatible with ChromaDB



---

9. ChromaDB Indexing

Each processed document is stored with:

Embedding

Text

Source

Connector

Timestamp

Owner

Role Metadata

Document ID

Collection:

enterprise_documents


---

10. Query Processing

When a user submits a question:

Who fixed the payment timeout issue?

The system:

1. Cleans the query.


2. Generates an embedding using BAAI BGE.


3. Performs semantic retrieval.




---

11. Semantic Retrieval

ChromaDB compares

Query Embedding

↓

Stored Embeddings

using Cosine Similarity.

Top-K relevant documents are returned.

Example:

Retrieved

GitHub Commit

Jira Issue

Slack Discussion

Confluence Page



---

12. Knowledge Graph Retrieval

Neo4j receives the identified entities.

Example:

Payment Service

Cypher query retrieves

Developer

↓

Commit

↓

Issue

↓

Documentation

↓

Technology

Traversal depth is limited (typically 2–3 hops) to maintain relevant context.


---

13. GraphRAG Context Fusion

GraphRAG combines two sources:

Semantic Context

Retrieved documents from ChromaDB


Relationship Context

Connected entities from Neo4j


Result

Complete enterprise context

instead of isolated documents.


---

14. Prompt Construction

LangChain builds the prompt dynamically.

Example:

System Prompt

You are an enterprise knowledge assistant.

Only answer using supplied context.

----------------------------

Retrieved Documents

GitHub Commit

Jira Issue

Slack Discussion

Graph Relationships

Developer

↓

Commit

↓

Repository

↓

Issue

Question

Who fixed the payment timeout issue?


---

15. LLM Inference

Supported models

Llama 3

Qwen

Mistral


Deployment

Ollama

Responsibilities

Understand context

Summarize

Explain

Answer naturally


The LLM does not access enterprise systems directly.


---

16. Role-Based Access Control (RBAC)

Before retrieval:

User

↓

Role Verification

↓

Allowed Sources

↓

Retrieve Only Authorized Data

↓

LLM

Unauthorized information is filtered before it reaches the model.


---

17. Example End-to-End Query

User asks

Who fixed the Payment Service bug and why was Redis introduced?

Step 1

Generate embedding for the query.

↓

Step 2

Cosine Similarity retrieves:

GitHub commit

Jira issue

Slack discussion

Confluence page


↓

Step 3

Neo4j retrieves:

Developer

↓

Commit

↓

Repository

↓

Issue

↓

Technology (Redis)

↓

Architecture Document

↓

Step 4

GraphRAG merges both contexts.

↓

Step 5

RBAC removes unauthorized information if necessary.

↓

Step 6

LLM generates:

> "John fixed the Payment Service bug in commit abc123. Redis was introduced to improve caching performance, as discussed in Jira issue PAY-42 and documented in the architecture page."




---

18. Explainability

Each response should include:

Source documents

Connected entities

Supporting references


Benefits

Improved trust

Easier verification

Enterprise compliance



---

19. Performance Optimizations

Cache frequently asked queries.

Generate embeddings only for new or modified documents.

Batch embedding generation during synchronization.

Limit graph traversal depth.

Retrieve only Top-K semantic results.



---

20. Error Handling

If no documents are found

Return:

> "No relevant information found."




---

If the LLM is unavailable

Return retrieved documents with a notification.


---

If graph retrieval fails

Continue with semantic retrieval only.


---

If vector retrieval fails

Use graph retrieval where possible.

The system should degrade gracefully rather than fail completely.


---

21. Future AI Enhancements

Query rewriting for better retrieval.

Hybrid lexical + semantic search.

Automatic entity extraction using transformer models.

Reranking retrieved documents with a cross-encoder.

Multi-modal support for images and diagrams.

Multi-language embeddings.

Agent-based reasoning and workflow automation.



---

22. Architectural Decisions

Decision	Reason

BAAI BGE	High-quality embeddings optimized for retrieval tasks
ChromaDB	Lightweight and efficient vector storage
Neo4j	Explicit modeling of organizational relationships
GraphRAG	Combines semantic and graph retrieval for richer context
LangChain	Simplifies orchestration of the AI pipeline
Ollama	Enables private, local LLM deployment
RBAC before Retrieval	Prevents unauthorized data from reaching the LLM



---

23. Summary

The AI pipeline is the intelligence core of AEKOS. It transforms enterprise data into searchable knowledge using embeddings and knowledge graphs, retrieves relevant information through GraphRAG, enforces security with RBAC, and generates accurate, explainable responses using a locally hosted LLM. This architecture provides a scalable, privacy-preserving, and domain-independent foundation for enterprise knowledge management.