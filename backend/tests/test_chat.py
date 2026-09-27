from unittest.mock import patch

import pytest

from llm.ollama_service import OllamaError
from models.user import User
from models.connector import Connector
from models.permission import Permission
from services.demo_seed import seed_demo


RESULT = {"document_id": "github:example", "text": "Repository team/demo has branches main and develop.",
          "metadata": {"title": "team/demo", "source": "github", "connector": "GitHub", "entity_type": "repository",
                       "repository": "team/demo", "url": "https://github.com/team/demo", "organization_id": "private-org"},
          "distance": 0.1}
SOURCE = {key: value for key, value in RESULT["metadata"].items() if key != "organization_id"} | {"snippet": RESULT["text"]}


@pytest.fixture
def retrieval():
    with patch("api.chat.retrieve_knowledge", return_value={"results": [RESULT], "document_count": 1}) as search:
        yield search


def login(client, email="arnold@aekos.com", password="password123"):
    response = client.post("/api/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid-token"}])
def test_chat_requires_valid_authentication(client, headers):
    with patch("api.chat.OllamaService") as service:
        response = client.post("/api/chat", json={"message": "Hello"}, headers=headers)
    assert response.status_code == 401
    service.assert_not_called()


@pytest.mark.parametrize("email,password", [("arnold@aekos.com", "password123"), ("admin@aekos.com", "admin123")])
def test_authenticated_chat_calls_existing_service_and_returns_contract(client, email, password, retrieval):
    headers = login(client, email, password)
    with patch("api.chat.OllamaService") as service:
        service.return_value.generate.return_value = "Qwen response"
        response = client.post("/api/chat", json={"message": "  Hello  "}, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"answer": "Qwen response", "sources": [SOURCE], "graph_context": []}
    retrieval.assert_called_once()
    assert retrieval.call_args.args[:2] == ("Hello", 3)
    assert retrieval.call_args.args[3].email == email
    service.return_value.generate.assert_called_once()
    prompt = service.return_value.generate.call_args.args[0]
    assert RESULT["text"] in prompt
    assert '"Hello"' in prompt
    assert "using only the supplied retrieved context" in prompt
    assert "The information was not found in the retrieved context." in prompt
    assert "private-org" not in prompt


@pytest.mark.parametrize("body", [{}, {"message": ""}, {"message": " \n\t "}, {"message": None}, {"message": 123}, {"message": "x" * 2001}])
def test_chat_validates_message_without_calling_ollama(client, body, retrieval):
    headers = login(client)
    with patch("api.chat.OllamaService") as service:
        response = client.post("/api/chat", json=body, headers=headers)
    assert response.status_code == 422
    service.assert_not_called()
    retrieval.assert_not_called()


def test_chat_returns_clean_service_error(client, retrieval):
    headers = login(client)
    with patch("api.chat.OllamaService") as service:
        service.return_value.generate.side_effect = OllamaError("private diagnostic details")
        response = client.post("/api/chat", json={"message": "Hello"}, headers=headers)
    assert response.status_code == 503
    assert response.json() == {"detail": "Chat generation is unavailable. Check the local Ollama service and try again."}
    assert "private diagnostic" not in response.text


def test_inactive_user_cannot_generate(client, db):
    headers = login(client)
    user = db.query(User).filter(User.email == "arnold@aekos.com").one()
    user.status = False
    db.commit()
    with patch("api.chat.OllamaService") as service:
        response = client.post("/api/chat", json={"message": "Hello"}, headers=headers)
    assert response.status_code == 403
    service.assert_not_called()


def test_empty_retrieval_returns_not_found_without_calling_ollama(client, retrieval):
    headers = login(client)
    retrieval.return_value = {"results": [], "document_count": 0}
    with patch("api.chat.OllamaService") as service:
        response = client.post("/api/chat", json={"message": "Repository branches?"}, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"answer": "The information was not found in the retrieved context.", "sources": [], "graph_context": []}
    service.assert_not_called()


def test_chat_enforces_existing_search_permission(client, db, retrieval):
    headers = login(client)
    user = db.query(User).filter(User.email == "arnold@aekos.com").one()
    db.query(Permission).filter(Permission.role_id == user.role_id, Permission.resource == "connectors", Permission.action == "read").delete()
    db.commit()
    with patch("api.chat.OllamaService") as service:
        response = client.post("/api/chat", json={"message": "Repository branches?"}, headers=headers)
    assert response.status_code == 403
    retrieval.assert_not_called()
    service.assert_not_called()


def test_chat_reuses_search_with_actual_organization_and_connector_filters(client, db):
    seed_demo(db)
    own = db.query(Connector).filter(Connector.name == "GitHub").one()
    db.add(Connector(name="Other tenant", type="GitHub", organization_id=None))
    db.commit()
    with patch("api.search.SemanticSearchService") as search, patch("api.chat.OllamaService") as service:
        search.return_value.search.return_value = {"results": [RESULT], "document_count": 1}
        service.return_value.generate.return_value = "The repository has main and develop branches."
        response = client.post("/api/chat", json={"message": "Repository branches?"}, headers=login(client))
    assert response.status_code == 200
    search.return_value.search.assert_called_once_with("Repository branches?", 3, where={"$and": [
        {"organization_id": own.organization_id}, {"connector_id": {"$in": [own.id]}}, {"source": "github"},
    ]})
    assert response.json()["sources"] == [SOURCE]
    assert response.json()["graph_context"] == []


def test_retrieval_failure_returns_existing_search_error_without_calling_ollama(client, db):
    seed_demo(db)
    with patch("api.search.SemanticSearchService", side_effect=RuntimeError("private diagnostics")), patch("api.chat.OllamaService") as service:
        response = client.post("/api/chat", json={"message": "Repository branches?"}, headers=login(client))
    assert response.status_code == 503
    assert "Knowledge search is unavailable" in response.json()["detail"]
    assert "private diagnostics" not in response.text
    service.assert_not_called()
