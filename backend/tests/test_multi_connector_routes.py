from unittest.mock import Mock, MagicMock

import pytest

from config.settings import settings
from connectors.registry import registry
from models.connector import Connector, ConnectorConfiguration
from models.user import User


@pytest.mark.parametrize("kind", ["jira", "confluence", "slack"])
def test_generic_routes_use_existing_clients(client, db, monkeypatch, kind):
    assert registry.is_registered(kind)
    cls = registry.get_connector_class(kind)
    account = Mock(return_value={"login": "employee"})
    sync = Mock(return_value=[{"source": kind, "entity_type": "Issue", "external_id": "1", "title": "Example", "content": "Content"}])
    monkeypatch.setattr(cls, "test_connection", account)
    monkeypatch.setattr(cls, "sync", sync)
    graph = MagicMock()
    monkeypatch.setattr("services.normalized_ingestion.Neo4jService", lambda **kwargs: graph)
    monkeypatch.setattr("api.chat.retrieve_graph_context", lambda *args: [])
    admin = db.query(User).filter_by(email="admin@aekos.com").one()
    record = Connector(name=f"Team {kind}", type=kind, organization_id=admin.organization_id)
    record.configuration = ConnectorConfiguration(api_url="https://example.invalid", encrypted_token="test-token")
    db.add(record)
    db.commit()
    token = client.post("/api/login", json={"email": "admin@aekos.com", "password": "admin123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    developer_token = client.post("/api/login", json={"email": "arnold@aekos.com", "password": "password123"}).json()["access_token"]
    for action in ("test", "sync"):
        denied = client.post(f"/api/connectors/{record.id}/{action}", headers={"Authorization": f"Bearer {developer_token}"})
        assert denied.status_code == 403
    tested = client.post(f"/api/connectors/{record.id}/test", headers=headers)
    assert tested.status_code == 200
    assert tested.json()["status"] == "connected"
    assert record.status == "connected"
    synced = client.post(f"/api/connectors/{record.id}/sync", headers=headers)
    assert synced.status_code == 200
    assert synced.json()["records_processed"] == 1
    assert synced.json()["documents_indexed"] == 1
    assert synced.json()["graph_nodes_updated"] == 1
    graph.driver.session.assert_called_once()
    from services.knowledge_runtime import get_chroma_service
    stored = get_chroma_service().collection.get(where={"connector_id": record.id})
    assert len(stored["ids"]) == 1
    assert stored["metadatas"][0]["source"] == kind
    assert stored["metadatas"][0]["organization_id"] == admin.organization_id
    monkeypatch.setattr("api.chat.OllamaService.generate", lambda self, prompt: "Example: Content")
    chat_response = client.post("/api/chat", json={"message": "What is Example?"}, headers=headers)
    assert chat_response.status_code == 200
    assert chat_response.json()["sources"][0]["source"] == kind
    assert record.status == "synced"
    assert record.configuration.last_sync is not None
    account.assert_called_once()
    sync.assert_called_once()
    sync.side_effect = RuntimeError("secret-token must not reach browser")
    failed = client.post(f"/api/connectors/{record.id}/sync", headers=headers)
    assert failed.status_code == 502
    assert "secret-token" not in failed.text
    assert record.status == "error"
    account.side_effect = RuntimeError("secret-token must not reach browser")
    failed_test = client.post(f"/api/connectors/{record.id}/test", headers=headers)
    assert failed_test.status_code == 502
    assert "secret-token" not in failed_test.text


@pytest.mark.parametrize("kind", ["jira", "confluence", "slack"])
def test_missing_credentials_cleanly_rejected(db, monkeypatch, kind):
    from fastapi import HTTPException
    from services.connector_orchestration_service import test_connector_connection

    key = f"{kind.upper()}_BOT_TOKEN" if kind == "slack" else f"{kind.upper()}_API_TOKEN"
    monkeypatch.setattr(settings, key, "")
    record = Connector(name=kind, type=kind)
    db.add(record)
    db.commit()
    with pytest.raises(HTTPException) as error:
        test_connector_connection(db, record)
    assert error.value.status_code == 409
    assert record.status == "not_configured"


@pytest.mark.parametrize("kind", ["jira", "confluence", "slack"])
def test_environment_configuration_maps_to_constructor(monkeypatch, kind):
    from services.connector_orchestration_service import _instantiate_registered_connector

    prefix = kind.upper()
    monkeypatch.setattr(settings, f"{prefix}_BOT_TOKEN" if kind == "slack" else f"{prefix}_API_TOKEN", "env-token")
    monkeypatch.setattr(settings, f"{prefix}_API_URL" if kind == "slack" else f"{prefix}_URL", "https://example.invalid")
    instance = _instantiate_registered_connector(Connector(name=kind, type=kind))
    assert instance.token == "env-token"
    assert instance.base_url == "https://example.invalid"
