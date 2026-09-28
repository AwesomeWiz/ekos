"""Adapt connector records to the existing shared knowledge ingestion schemas."""

import json
import logging

from connectors.models import NormalizedRecord
from graph.neo4j_service import Neo4jService
from knowledge.chunking import chunk_text
from knowledge.ingestion import KnowledgeIngestionService
from knowledge.schemas import DocumentRecord, EntityRecord, RelationshipRecord
from services.knowledge_runtime import get_chroma_service, get_embedding_service

logger = logging.getLogger(__name__)
ENTITY_TYPES = {"Issue", "Comment", "Space", "Page", "User", "Channel", "Message", "Document"}


def scalar_metadata(metadata):
    return {key: value if isinstance(value, (str, int, float, bool)) else json.dumps(value, ensure_ascii=False)
            for key, value in metadata.items() if value is not None}


def ingest_connector_records(connector, raw_records):
    if not connector.organization_id:
        raise ValueError("An organization is required for knowledge ingestion")
    source = connector.type.strip().lower()
    records = [NormalizedRecord.model_validate(item.model_dump() if hasattr(item, "model_dump") else item)
               for item in raw_records]
    if any(record.source != source for record in records):
        raise ValueError("Record source does not match the connector")
    common = {"source": source, "organization_id": connector.organization_id,
              "connector_id": connector.id, "connector": connector.name}
    prefix = f"{source}:{connector.organization_id}:{connector.id}"
    entities, documents, relationships = [], [], []
    entity_ids = {}
    for record in records:
        entity_id = f"{prefix}:{record.entity_type}:{record.external_id}"
        metadata = {**scalar_metadata(record.metadata), "title": record.title,
                    "entity_type": record.entity_type, "entity_id": record.external_id,
                    "author": record.author or "", "project": record.project or "",
                    "timestamp": record.timestamp or "", **common,
                    "knowledge_entity_id": entity_id}
        text = f"Title: {record.title}\nType: {record.entity_type}\nProject: {record.project or ''}\nContent: {record.content}"
        documents.append(DocumentRecord(id=entity_id, text=text, metadata=metadata))
        if record.entity_type in ENTITY_TYPES:
            entities.append(EntityRecord(id=entity_id, type=record.entity_type,
                                         properties={**metadata, "name": record.title, "content": record.content}))
            entity_ids[(record.entity_type, record.external_id)] = entity_id
    for record in records:
        parent = None
        if source == "jira" and record.entity_type == "Comment":
            parent = ("Issue", record.metadata.get("issue_key"))
        elif source == "confluence" and record.entity_type == "Page":
            parent = ("Space", f"space-{record.project}")
        elif source == "slack" and record.entity_type == "Message":
            parent = ("Channel", f"channel-{record.metadata.get('channel_id')}")
        if parent in entity_ids:
            relationships.append(RelationshipRecord(
                source_id=entity_ids[(record.entity_type, record.external_id)], source_type=record.entity_type,
                relationship="BELONGS_TO", target_id=entity_ids[parent], target_type=parent[0], properties=common))

    chroma, embeddings = get_chroma_service(), get_embedding_service()
    neo4j = Neo4jService(connection_timeout=2)
    documents_indexed = graph_nodes_updated = 0
    try:
        service = KnowledgeIngestionService(neo4j=neo4j, chroma=chroma, embeddings=embeddings)
        # Vector persistence is required; a failed write must not report a successful sync.
        for document in documents:
            service.ingest_document(document)
            ids = [f"{document.id}:chunk:{index}" for index in range(1, len(chunk_text(document.text)) + 1)]
            chroma.delete_stale_chunks(ids, {"$and": [
                {"organization_id": connector.organization_id}, {"connector_id": connector.id},
                {"source": source}, {"entity_type": document.metadata["entity_type"]},
                {"entity_id": document.metadata["entity_id"]},
            ]})
            documents_indexed += len(ids)
        # Reuse the generic entity/relationship writer; Neo4j remains optional for chat.
        try:
            neo4j.verify_connection()
            for entity in entities:
                service.ingest_entity(entity)
                graph_nodes_updated += 1
            for relationship in relationships:
                service.ingest_relationship(relationship)
        except Exception as error:
            logger.warning("Optional connector graph ingestion unavailable (%s)", type(error).__name__)
    finally:
        neo4j.close()
    return {"records_processed": len(records), "documents_indexed": documents_indexed,
            "graph_nodes_updated": graph_nodes_updated,
            "indexing": {"status": "indexed", "documents_indexed": documents_indexed,
                         "chroma_total": chroma.count({"organization_id": connector.organization_id}), "error": None}}
