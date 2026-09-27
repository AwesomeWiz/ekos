from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from models.user import User
from auth.dependencies import require_permission
from services.retrieval_service import RetrievalService
from services.chat_service import ChatService, BaseLLMProvider

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]] = []
    graph_context: List[Dict[str, Any]] = []


_retrieval_service = RetrievalService()
_llm_provider: Optional[BaseLLMProvider] = None


def get_chat_service() -> ChatService:
    return ChatService(
        retrieval_service=_retrieval_service,
        llm_provider=_llm_provider,
    )


def set_llm_provider(provider: Optional[BaseLLMProvider]) -> None:
    global _llm_provider
    _llm_provider = provider


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    current_user: User = Depends(require_permission("chat", "use")),
    chat_service: ChatService = Depends(get_chat_service),
):
    """Authenticated and RBAC permission-checked endpoint to answer user questions."""
    return chat_service.answer_question(request.question)
