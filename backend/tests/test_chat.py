from unittest.mock import MagicMock
from fastapi import HTTPException
from api.chat import set_llm_provider
from models.role import Role
from models.permission import Permission
from services.chat_service import ChatService, BaseLLMProvider
from services.retrieval_service import RetrievalService


class MockLLMProvider(BaseLLMProvider):
    def generate(self, prompt: str, context: dict) -> str:
        return "This is a mocked AI response for testing."


def _grant_admin_chat_permission(db):
    admin_role = db.query(Role).filter(Role.role_name == "Administrator").first()
    if admin_role:
        existing = db.query(Permission).filter(
            Permission.role_id == admin_role.id,
            Permission.resource == "chat",
            Permission.action == "use",
        ).first()
        if not existing:
            db.add(Permission(role_id=admin_role.id, resource="chat", action="use"))
            db.commit()


def test_chat_unauthenticated(client):
    response = client.post("/api/chat", json={"question": "What is EKOS?"})
    assert response.status_code in (401, 403)


def test_chat_rbac_permission(db, client):
    _grant_admin_chat_permission(db)

    # Log in as Developer (no chat:use permission) -> 403 Forbidden
    dev_resp = client.post("/api/login", json={"email": "arnold@aekos.com", "password": "password123"})
    dev_token = dev_resp.json()["access_token"]
    dev_headers = {"Authorization": f"Bearer {dev_token}"}
    forbidden_resp = client.post("/api/chat", json={"question": "Forbidden question?"}, headers=dev_headers)
    assert forbidden_resp.status_code == 403

    # Log in as Administrator (has chat:use permission) -> 200 OK
    admin_resp = client.post("/api/login", json={"email": "admin@aekos.com", "password": "admin123"})
    admin_token = admin_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    set_llm_provider(MockLLMProvider())

    response = client.post("/api/chat", json={"question": "How does auth work?"}, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "This is a mocked AI response for testing."
    assert "sources" in data
    assert "graph_context" in data

    set_llm_provider(None)


def test_missing_llm_provider_handling(db, client):
    _grant_admin_chat_permission(db)

    admin_resp = client.post("/api/login", json={"email": "admin@aekos.com", "password": "admin123"})
    admin_token = admin_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    set_llm_provider(None)

    response = client.post("/api/chat", json={"question": "Where is the LLM?"}, headers=admin_headers)
    assert response.status_code == 503
    assert "LLM provider is not configured" in response.json()["detail"]


def test_chat_service_with_mock_llm():
    mock_chroma = MagicMock()
    mock_bge = MagicMock()

    mock_bge.embed.return_value = [0.1, 0.2]
    mock_chroma.search.return_value = {
        "documents": [["Document content on Redis timeouts"]],
        "metadatas": [[{"title": "Redis Guide", "source": "confluence"}]],
        "distances": [[0.1]],
    }

    retrieval_service = RetrievalService(
        chroma_service=mock_chroma,
        embedding_service=mock_bge,
    )
    chat_service = ChatService(
        retrieval_service=retrieval_service,
        llm_provider=MockLLMProvider(),
    )

    result = chat_service.answer_question("Why use Redis?")
    assert result["answer"] == "This is a mocked AI response for testing."
    assert len(result["sources"]) == 1
    assert result["sources"][0]["title"] == "Redis Guide"
    assert result["sources"][0]["source"] == "confluence"
