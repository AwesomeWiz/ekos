import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

try:
    from vector_db.chroma_service import ChromaService
except ImportError:
    ChromaService = None

try:
    from graph.neo4j_service import Neo4jService
except ImportError:
    Neo4jService = None

try:
    from embeddings.bge_embeddings import BGEEmbeddingService
except ImportError:
    BGEEmbeddingService = None


class RetrievalService:
    def __init__(
        self,
        chroma_service: Optional[Any] = None,
        neo4j_service: Optional[Any] = None,
        embedding_service: Optional[Any] = None,
    ):
        self.chroma_service = chroma_service
        self.neo4j_service = neo4j_service
        self.embedding_service = embedding_service

    def retrieve(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        vector_results: List[Dict[str, Any]] = []
        graph_results: List[Dict[str, Any]] = []

        # 1. Vector Retrieval
        if self.chroma_service is not None and self.embedding_service is not None:
            try:
                query_embedding = self.embedding_service.embed(query)
                raw_chroma = self.chroma_service.search(query_embedding, top_k=top_k)
                if raw_chroma and "documents" in raw_chroma and raw_chroma["documents"]:
                    docs = raw_chroma["documents"][0] if raw_chroma["documents"] else []
                    metas = raw_chroma["metadatas"][0] if "metadatas" in raw_chroma and raw_chroma["metadatas"] else []
                    distances = raw_chroma["distances"][0] if "distances" in raw_chroma and raw_chroma["distances"] else []

                    for idx, doc_text in enumerate(docs):
                        dist = distances[idx] if idx < len(distances) else 0.0
                        score = round(max(0.0, 1.0 - float(dist)), 4) if dist is not None else 1.0
                        meta = metas[idx] if idx < len(metas) else {}
                        vector_results.append({
                            "text": doc_text,
                            "score": score,
                            "metadata": meta,
                        })
            except Exception as e:
                logger.warning(f"Vector retrieval failed: {e}")

        # 2. Graph Retrieval Boundary
        if self.neo4j_service is not None:
            try:
                pass
            except Exception as e:
                logger.warning(f"Graph retrieval failed: {e}")

        return {
            "vector_results": vector_results,
            "graph_results": graph_results,
        }
