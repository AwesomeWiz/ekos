from unittest.mock import MagicMock
import pytest
from connectors.base import BaseConnector
from connectors.registry import registry, UnrecognizedConnectorTypeError
from schemas.ingestion import NormalizedRecord, SyncResult
from services.ingestion_service import IngestionService


class DummyCustomConnector(BaseConnector):
    def authenticate(self): pass
    def test_connection(self): return {"status": "ok"}
    def fetch_data(self): return []
    def transform_data(self, data): return []
    def sync(self):
        return [
            NormalizedRecord(
                source="custom",
                entity_type="Issue",
                external_id="ISSUE-101",
                title="Custom Issue Title",
                content="Custom issue content description",
                author="alice",
                project="PROJ-A",
            )
        ]
    def disconnect(self): pass


def test_connector_registry_resolution():
    # Verify built-in github registration
    assert registry.is_registered("github")
    cls = registry.get_connector_class("GitHub")
    assert cls.__name__ == "GitHubConnector"

    # Verify custom registration and unregistration
    registry.register("custom", DummyCustomConnector)
    assert registry.is_registered("custom")
    assert registry.get_connector_class("CUSTOM") == DummyCustomConnector
    registry.unregister("custom")
    assert not registry.is_registered("custom")


def test_unregistered_connector_type():
    with pytest.raises(UnrecognizedConnectorTypeError):
        registry.get_connector_class("non_existent_type")


def test_ingestion_service_with_mocks():
    mock_neo4j = MagicMock()
    mock_chroma = MagicMock()
    mock_bge = MagicMock()
    mock_bge.embed.return_value = [0.1, 0.2, 0.3]

    service = IngestionService(
        neo4j_service=mock_neo4j,
        chroma_service=mock_chroma,
        embedding_service=mock_bge,
    )

    records = [
        NormalizedRecord(
            source="jira",
            entity_type="Issue",
            external_id="JIRA-123",
            title="Fix login bug",
            content="Detailed description of login issue",
            project="AUTH",
            metadata={"state": "open"},
        ),
        NormalizedRecord(
            source="confluence",
            entity_type="Document",
            external_id="DOC-99",
            title="Architecture Specs",
            content="System architecture overview documentation",
        ),
        NormalizedRecord(
            source="slack",
            entity_type="Message",
            external_id="MSG-555",
            title="Slack message",
            content="Discussion on deployment timeline",
        ),
    ]

    result = service.process_records("JiraConnector", records)

    assert result.status == "success"
    assert result.connector == "JiraConnector"
    assert result.records_processed == 3
    assert result.documents_indexed == 3  # All 3 records have text content indexed in Chroma
    assert result.graph_nodes_updated == 2  # Issue & Document supported in Neo4j; Message skipped cleanly

    # Verify Neo4j calls
    mock_neo4j.create_issue.assert_called_once_with(
        issue_id="JIRA-123",
        title="Fix login bug",
        repository_id="AUTH",
        state="open",
    )
    mock_neo4j.create_document.assert_called_once_with(
        document_id="DOC-99",
        title="Architecture Specs",
        content="System architecture overview documentation",
    )

    # Verify Chroma calls
    assert mock_chroma.add_document.call_count == 3
    assert mock_bge.embed.call_count == 3


def test_ingestion_counts():
    service = IngestionService()
    records = [
        {"source": "test", "entity_type": "Issue", "external_id": "1", "title": "T1"},
        {"source": "test", "entity_type": "Commit", "external_id": "2", "title": "T2"},
    ]
    result = service.process_records("TestConnector", records)
    assert result.records_processed == 2
    assert result.documents_indexed == 0
    assert result.graph_nodes_updated == 0


def test_connector_api_rbac(client):
    # Unauthenticated request should be rejected
    response = client.post("/api/connectors/dummy-id/sync")
    assert response.status_code in (401, 403)


def test_org_isolation_retained(client):
    # Authenticate as admin
    login_resp = client.post("/api/login", json={"email": "admin@aekos.com", "password": "admin123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Request non-existent or other org's connector
    resp = client.post("/api/connectors/00000000-0000-0000-0000-000000000000/sync", headers=headers)
    assert resp.status_code == 404
