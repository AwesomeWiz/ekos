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