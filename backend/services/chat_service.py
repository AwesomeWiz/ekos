from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status
from services.retrieval_service import RetrievalService


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, context: Dict[str, Any]) -> str:
        pass


class ChatService:
    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_provider: Optional[BaseLLMProvider] = None,
    ):
        self.retrieval_service = retrieval_service
        self.llm_provider = llm_provider

    def answer_question(self, question: str) -> Dict[str, Any]:
        if not question or not question.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question cannot be empty.",
            )

        # 1. Retrieval
        retrieved_context = self.retrieval_service.retrieve(question)
        vector_results = retrieved_context.get("vector_results", [])
        graph_results = retrieved_context.get("graph_results", [])

        # 2. Extract Sources & Format Context
        sources = [
            {
                "title": item.get("metadata", {}).get("title") or "Document",
                "source": item.get("metadata", {}).get("source") or "vector_db",
                "text": item.get("text", ""),
                "score": item.get("score", 0.0),
            }
            for item in vector_results
        ]

        # 3. Call LLM Provider Boundary
        if self.llm_provider is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM provider is not configured or available. Please configure an LLM service.",
            )

        prompt = f"Question: {question}\nContext: {sources}"
        answer = self.llm_provider.generate(prompt=prompt, context=retrieved_context)

        return {
            "answer": answer,
            "sources": sources,
            "graph_context": graph_results,
        }
