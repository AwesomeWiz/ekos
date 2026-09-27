"""Normalize scoped Chroma retrieval without generating an LLM answer."""

from services.knowledge_runtime import get_chroma_service, get_embedding_service


class SemanticSearchService:
    def __init__(self, chroma=None, embeddings=None):
        self.chroma = chroma if chroma is not None else get_chroma_service()
        self.embeddings = embeddings

    def search(self, query: str, top_k: int = 5, *, where: dict) -> dict:
        count = self.chroma.count(where)
        if count == 0:
            return {"query": query, "results": [], "document_count": 0}
        embeddings = self.embeddings if self.embeddings is not None else get_embedding_service()
        raw = self.chroma.search(embeddings.embed(query), top_k=top_k, where=where)
        results = []
        for index, document_id in enumerate(raw["ids"][0]):
            results.append({"document_id": document_id, "text": raw["documents"][0][index],
                            "metadata": raw["metadatas"][0][index] or {}, "distance": raw["distances"][0][index]})
        return {"query": query, "results": results, "document_count": count}
