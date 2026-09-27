import logging
from typing import List, Dict, Any, Optional, Union
from schemas.ingestion import NormalizedRecord, SyncResult

logger = logging.getLogger(__name__)

try:
    from graph.neo4j_service import Neo4jService
except ImportError:
    Neo4jService = None

try:
    from vector_db.chroma_service import ChromaService
except ImportError:
    ChromaService = None

try:
    from embeddings.bge_embeddings import BGEEmbeddingService
except ImportError:
    BGEEmbeddingService = None


class IngestionService:
    def __init__(
        self,
        neo4j_service: Optional[Any] = None,
        chroma_service: Optional[Any] = None,
        embedding_service: Optional[Any] = None,
    ):
        self.neo4j_service = neo4j_service
        self.chroma_service = chroma_service
        self.embedding_service = embedding_service

    def process_records(
        self,
        connector_name: str,
        records: List[Union[NormalizedRecord, Dict[str, Any]]]
    ) -> SyncResult:
        records_processed = 0
        documents_indexed = 0
        graph_nodes_updated = 0

        for record_item in records:
            if isinstance(record_item, dict):
                try:
                    record = NormalizedRecord(**record_item)
                except Exception as e:
                    logger.warning(f"Failed to parse record dict: {e}")
                    continue
            else:
                record = record_item

            records_processed += 1

            # 1. Update Graph (Neo4j) using existing public methods
            if self.neo4j_service is not None:
                try:
                    graph_updated = self._ingest_to_graph(record)
                    if graph_updated:
                        graph_nodes_updated += 1
                except Exception as e:
                    logger.warning(f"Neo4j graph ingestion skipped for record {record.external_id}: {e}")

            # 2. Index Vector (ChromaDB + BGE) using existing public methods
            if self.chroma_service is not None and self.embedding_service is not None:
                text_content = record.content or record.title
                if text_content and text_content.strip():
                    try:
                        embedding = self.embedding_service.embed(text_content)
                        doc_metadata = {
                            "source": record.source,
                            "entity_type": record.entity_type,
                            "external_id": record.external_id,
                            "title": record.title,
                            "author": record.author or "",
                            "project": record.project or "",
                            "timestamp": record.timestamp or "",
                            **record.metadata,
                        }
                        self.chroma_service.add_document(
                            document_id=f"{record.source}:{record.entity_type}:{record.external_id}",
                            text=text_content,
                            embedding=embedding,
                            metadata=doc_metadata,
                        )
                        documents_indexed += 1
                    except Exception as e:
                        logger.warning(f"ChromaDB vector indexing skipped for record {record.external_id}: {e}")

        return SyncResult(
            status="success",
            connector=connector_name,
            records_processed=records_processed,
            documents_indexed=documents_indexed,
            graph_nodes_updated=graph_nodes_updated,
        )

    def _ingest_to_graph(self, record: NormalizedRecord) -> bool:
        """Process record with Neo4jService if supported by existing methods."""
        etype = record.entity_type.lower()
        if etype == "repository":
            self.neo4j_service.create_repository(
                repository_id=record.external_id,
                name=record.title,
                url=record.metadata.get("url"),
            )
            return True
        elif etype == "commit":
            self.neo4j_service.create_commit(
                commit_id=record.external_id,
                message=record.title,
                author_id=record.author or "unknown",
                repository_id=record.project or record.metadata.get("repository_id") or "unknown",
            )
            return True
        elif etype == "issue":
            self.neo4j_service.create_issue(
                issue_id=record.external_id,
                title=record.title,
                repository_id=record.project or record.metadata.get("repository_id") or "unknown",
                state=record.metadata.get("state"),
            )
            return True
        elif etype == "document":
            self.neo4j_service.create_document(
                document_id=record.external_id,
                title=record.title,
                content=record.content or "",
            )
            return True
        return False
