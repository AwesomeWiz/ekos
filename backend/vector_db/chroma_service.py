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

    def count(self, where: dict | None = None) -> int:
        if where is not None:
            return len(self.collection.get(where=where, include=[])["ids"])
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
        where: dict | None = None,
    ) -> dict:
        available = self.count(where)
        if not available:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
        return self.collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, available),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

    def delete_stale_chunks(self, current_ids: list[str], where: dict) -> None:
        """Remove obsolete chunks of an updated entity without deleting other sync pages."""
        existing = self.collection.get(where=where, include=[])["ids"]
        stale = sorted(set(existing) - set(current_ids))
        if stale:
            self.collection.delete(ids=stale)
