import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth.dependencies import require_permission
from config.settings import settings
from models.base import get_db
from models.connector import Connector
from models.user import User
from schemas.search import SearchRequest, SearchResponse, SearchStatus
from services.knowledge_runtime import get_chroma_service
from services.semantic_search_service import SemanticSearchService

router = APIRouter(prefix="/search", tags=["Semantic search"])
logger = logging.getLogger(__name__)


def knowledge_scope(db: Session, user: User) -> dict | None:
    if not user.organization_id:
        return None
    connectors = db.query(Connector.id).filter(
        Connector.organization_id == user.organization_id, func.lower(Connector.type) == "github"
    ).all()
    if not connectors:
        return None
    return {"$and": [{"organization_id": user.organization_id},
                     {"connector_id": {"$in": [row.id for row in connectors]}}, {"source": "github"}]}


def search_unavailable(error: Exception):
    logger.exception("Knowledge retrieval unavailable (%s)", type(error).__name__)
    raise HTTPException(status_code=503, detail="Knowledge search is unavailable. Check the backend Chroma/model setup and try again.") from error


def retrieve_knowledge(query: str, top_k: int, db: Session, user: User) -> dict:
    """Shared retrieval path for search and chat, preserving the existing tenant scope."""
    scope = knowledge_scope(db, user)
    if scope is None:
        return {"query": query, "results": [], "document_count": 0}
    try:
        return SemanticSearchService().search(query, top_k, where=scope)
    except Exception as error:
        search_unavailable(error)


@router.post("", response_model=SearchResponse)
def semantic_search(request: SearchRequest, db: Session = Depends(get_db),
                    user: User = Depends(require_permission("connectors", "read"))):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Enter a non-empty search query.")
    return retrieve_knowledge(query, request.top_k, db, user)


@router.get("/status", response_model=SearchStatus)
def search_status(db: Session = Depends(get_db), user: User = Depends(require_permission("connectors", "read"))):
    scope = knowledge_scope(db, user)
    try:
        count = get_chroma_service().count(scope) if scope is not None else 0
    except Exception as error:
        search_unavailable(error)
    return {"collection": "enterprise_documents", "document_count": count, "embedding_model": settings.EMBEDDING_MODEL}
