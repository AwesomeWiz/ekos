from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from connectors.models import NormalizedRecord
from services.normalized_ingestion import ingest_connector_records
from services.knowledge_runtime import get_chroma_service


@pytest.mark.parametrize("source,parent_type,parent_id,child_type,extra", [
    ("jira", "Issue", "EK-1", "Comment", {"issue_key": "EK-1"}),
    ("confluence", "Space", "space-EK", "Page", {}),
    ("slack", "Channel", "channel-C1", "Message", {"channel_id": "C1"}),
])
def test_shared_ingestion_adapts_records_preserves_scope_and_writes_relationships(monkeypatch, source, parent_type, parent_id, child_type, extra):
    graph = MagicMock()
    monkeypatch.setattr("services.normalized_ingestion.Neo4jService", lambda **kwargs: graph)
    connector = SimpleNamespace(id="connector", organization_id="org", name="Team knowledge", type=source)
    records = [NormalizedRecord(source=source, entity_type=parent_type, external_id=parent_id, title="Parent", content="Parent content"),
               NormalizedRecord(source=source, entity_type=child_type, external_id="child", title="Child", content="Useful knowledge",
                   project="EK", metadata={**extra, "labels": ["architecture"], "url": None, "organization_id": "spoof", "connector_id": "spoof", "source": "spoof"})]
    result = ingest_connector_records(connector, records)
    assert result["documents_indexed"] == 2
    assert result["graph_nodes_updated"] == 2
    queries = graph.driver.session.return_value.__enter__.return_value.run.call_args_list
    assert len(queries) == 3
    assert queries[-1].kwargs["source_id"].startswith(f"{source}:org:connector:")
    assert queries[-1].kwargs["target_id"].startswith(f"{source}:org:connector:")
    stored = get_chroma_service().collection.get(where={"connector_id": "connector"})
    assert len(stored["ids"]) == 2
    for metadata in stored["metadatas"]:
        assert metadata["organization_id"] == "org"
        assert metadata["source"] == source
    # Upserts remain idempotent; a second tenant cannot overwrite these records.
    ingest_connector_records(connector, records)
    connector.organization_id = "other-org"
    ingest_connector_records(connector, records)
    assert get_chroma_service().count({"organization_id": "org"}) == 2
    assert get_chroma_service().count({"organization_id": "other-org"}) == 2


def test_graph_offline_does_not_prevent_vector_ingestion(monkeypatch):
    graph = MagicMock()
    graph.verify_connection.side_effect = RuntimeError("offline")
    monkeypatch.setattr("services.normalized_ingestion.Neo4jService", lambda **kwargs: graph)
    connector = SimpleNamespace(id="connector", organization_id="org", name="Jira", type="jira")
    records = [{"source": "jira", "entity_type": "Issue", "external_id": "1", "title": "Title", "content": "Content"}]
    result = ingest_connector_records(connector, records)
    assert result["documents_indexed"] == 1
    assert result["graph_nodes_updated"] == 0
    graph.close.assert_called_once()
