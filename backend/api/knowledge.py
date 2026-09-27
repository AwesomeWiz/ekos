from fastapi import APIRouter

from knowledge.retrieval import KnowledgeRetrievalService

router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge"],
)


@router.get("/search")
def search_knowledge(
    query: str,
    top_k: int = 5,
):
    service = KnowledgeRetrievalService()

    try:
        return service.retrieve_context(
            query=query,
            top_k=top_k,
        )
    finally:
        service.close()