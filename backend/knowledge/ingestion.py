from .schemas import EntityRecord, RelationshipRecord, DocumentRecord
from graph.neo4j_service import Neo4jService
from vector_db.chroma_service import ChromaService
from embeddings.bge_embeddings import BGEEmbeddingService

class KnowledgeIngestionService:
    def __init__(
        self,
        neo4j: Neo4jService | None = None,
        chroma: ChromaService | None = None,
        embeddings: BGEEmbeddingService | None = None,
    ):
        self.neo4j = neo4j or Neo4jService()
        self.chroma = chroma or ChromaService()
        self.embeddings = embeddings or BGEEmbeddingService()

    def ingest_entity(self, record: EntityRecord):
        query = f"""
        MERGE (n:{record.type} {{id: $id}})
        SET n += $properties
        """

        with self.neo4j.driver.session() as session:
            session.run(
                query,
                id=record.id,
                properties=record.properties,
            )

    def ingest_relationship(self, record: RelationshipRecord):
        query = f"""
        MATCH (source:{record.source_type} {{id: $source_id}})
        MATCH (target:{record.target_type} {{id: $target_id}})
        MERGE (source)-[r:{record.relationship}]->(target)
        SET r += $properties
        """

        with self.neo4j.driver.session() as session:
            session.run(
                query,
                source_id=record.source_id,
                target_id=record.target_id,
                properties=record.properties,
            )

    def ingest_document(self, record: DocumentRecord):
        from .chunking import chunk_text

        chunks = chunk_text(record.text)

        if not chunks:
            return

        for index, chunk in enumerate(chunks, start=1):
            embedding = self.embeddings.embed(chunk)

            chunk_id = f"{record.id}:chunk:{index}"

            metadata = {
                **record.metadata,
                "chunk_number": index,
                "total_chunks": len(chunks),
            }

            self.chroma.add_document(
                document_id=chunk_id,
                text=chunk,
                embedding=embedding,
                metadata=metadata,
            )

    def ingest(self, records: dict):
        for entity in records.get("entities", []):
            self.ingest_entity(entity)

        for relationship in records.get("relationships", []):
            self.ingest_relationship(relationship)

        for document in records.get("documents", []):
            self.ingest_document(document)

    def close(self):
        self.neo4j.close()