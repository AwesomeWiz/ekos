import os

import chromadb


class ChromaService:
    def __init__(self, path: str | None = None):
        self.path = path or os.getenv(
            "CHROMA_PATH",
            "./data/chroma",
        )

        self.client = chromadb.PersistentClient(path=self.path)

        self.collection = self.client.get_or_create_collection(
            name="enterprise_documents",
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        return self.collection.count()

    def add_document(
        self,
        document_id: str,
        text: str,
        embedding: list[float],
        metadata: dict,
    ) -> None:
        self.collection.upsert(
            ids=[document_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata],
        )

    def search(
        self,
        embedding: list[float],
        top_k: int = 5,
    ) -> dict:
        return self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
        )