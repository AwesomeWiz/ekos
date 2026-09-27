import base64
import sys
from unittest.mock import Mock, patch

import pytest

from config.settings import settings
from embeddings.bge_embeddings import BGEEmbeddingService
from models.connector import Connector
from services.demo_seed import seed_demo
from services.indexing_service import chunk_text, github_documents, index_github_data
from services.knowledge_runtime import get_chroma_service
from services.semantic_search_service import SemanticSearchService
from vector_db.chroma_service import ChromaService


def github_data(readme="Repository branches include main and develop."):
    return {"repository": {"full_name": "team/demo", "default_branch": "main", "description": "Knowledge indexing"},
            "branches": [{"name": "main"}, {"name": "develop"}],
            "commits": [{"sha": "abc123", "message": "Introduce Redis caching", "url": "https://github.com/team/demo/commit/abc123"}],
            "issues": [{"number": 42, "title": "Cache response times", "body": "Reduce database load", "state": "open"}],
            "readme": {"name": "README.md", "path": "README.md", "encoding": "base64", "content": base64.b64encode(readme.encode()).decode()}}


def login(client, email="arnold@aekos.com", password="password123"):
    response = client.post("/api/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def configured_connector(db, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "unit-test-token")
    monkeypatch.setattr(settings, "GITHUB_OWNER", "team")
    monkeypatch.setattr(settings, "GITHUB_REPO", "demo")
    seed_demo(db)
    return db.query(Connector).filter(Connector.type == "GitHub").one()


def test_bge_reuses_sentence_transformer_and_normalizes_embeddings():
    sentence_transformer = Mock()
    sentence_transformer.return_value.encode.return_value.tolist.return_value = [0.2, 0.8]
    with patch.dict(sys.modules, {"sentence_transformers": Mock(SentenceTransformer=sentence_transformer)}):
        service = BGEEmbeddingService("test/model", cache_folder="test/cache")
        assert service.embed("query") == [0.2, 0.8]
        service.embed_many(["document"])
    sentence_transformer.assert_called_once_with("test/model", cache_folder="test/cache")
    sentence_transformer.return_value.encode.assert_any_call("query", normalize_embeddings=True)
    sentence_transformer.return_value.encode.assert_any_call(["document"], normalize_embeddings=True)


def test_stable_ids_metadata_and_readme_decoding():
    data = github_data()
    documents = github_documents(data, "org", "connector")
    assert documents == github_documents(data, "org", "connector")
    assert len(documents) == 4
    assert {document.metadata["entity_type"] for document in documents} == {"repository", "readme", "commit", "issue"}
    assert any(document.id.endswith(":commit:abc123") for document in documents)
    assert "main, develop" in documents[0].text
    assert any("Reduce database load" in document.text for document in documents)
    assert all(all(isinstance(value, (str, int, float, bool)) for value in document.metadata.values()) for document in documents)
    assert {document.id for document in documents}.isdisjoint({document.id for document in github_documents(data, "other-org", "connector")})


def test_chunking_is_deterministic_and_overlaps():
    text = "architecture " * 600
    chunks = chunk_text(text)
    assert len(chunks) > 1
    assert chunks == chunk_text(text)
    assert all(len(chunk) <= 2000 for chunk in chunks)
    assert chunks[0][-100:] in chunks[1]
    documents = github_documents(github_data(text), "org", "connector")
    readme = [document for document in documents if document.metadata["entity_type"] == "readme"]
    assert [document.id for document in readme] == [f"github:org:connector:team/demo:readme:chunk:{i}" for i in range(len(readme))]


def test_real_chroma_upserts_searches_and_persists(tmp_path):
    chroma = ChromaService(str(tmp_path / "persisted"))
    assert chroma.search([1.0, 0.0], where={"organization_id": "org"})["ids"] == [[]]
    chroma.add_document("one", "initial", [1.0, 0.0], {"organization_id": "org"})
    chroma.add_document("one", "updated", [1.0, 0.0], {"organization_id": "org"})
    chroma.add_document("two", "private", [1.0, 0.0], {"organization_id": "other"})
    assert chroma.count() == 2
    result = chroma.search([1.0, 0.0], top_k=10, where={"organization_id": "org"})
    assert result["ids"] == [["one"]]
    assert result["documents"] == [["updated"]]
    assert ChromaService(str(tmp_path / "persisted")).count() == 2


def test_reindex_updates_without_duplicates_and_removes_obsolete_chunks(isolated_knowledge_runtime):
    data = github_data("README content " * 700)
    first = index_github_data(data, "org", "connector")
    assert first["documents_indexed"] > 4
    second = index_github_data(data, "org", "connector")
    assert second == first
    updated = github_data()
    updated["readme"]["path"] = "docs/README.md"
    compact = index_github_data(updated, "org", "connector")
    assert compact["documents_indexed"] == compact["chroma_total"] == 4
    assert isolated_knowledge_runtime.embed_many.called


def test_semantic_search_normalizes_chroma_and_skips_model_for_empty(isolated_knowledge_runtime):
    chroma = get_chroma_service()
    search = SemanticSearchService(chroma, isolated_knowledge_runtime)
    empty = search.search("Redis", where={"organization_id": "org"})
    assert empty == {"query": "Redis", "results": [], "document_count": 0}
    isolated_knowledge_runtime.embed.assert_not_called()
    index_github_data(github_data(), "org", "connector")
    result = search.search("Redis", top_k=2, where={"organization_id": "org"})
    assert result["document_count"] == 4
    assert len(result["results"]) == 2
    assert set(result["results"][0]) == {"document_id", "text", "metadata", "distance"}
    assert isinstance(result["results"][0]["distance"], float)


def test_search_requires_auth_and_current_database_permission(client, db, monkeypatch):
    connector = configured_connector(db, monkeypatch)
    assert client.post("/api/search", json={"query": "Redis"}).status_code == 401
    assert client.get("/api/search/status").status_code == 401
    from models.permission import Permission
    from models.user import User

    developer = db.query(User).filter(User.email == "arnold@aekos.com").one()
    db.query(Permission).filter(Permission.role_id == developer.role_id).delete()
    db.commit()
    assert client.post("/api/search", headers=login(client), json={"query": "Redis"}).status_code == 403


def test_search_api_empty_scoped_results_and_status(client, db, monkeypatch):
    connector = configured_connector(db, monkeypatch)
    headers = login(client)
    assert client.post("/api/search", headers=headers, json={"query": "repository branches"}).json()["document_count"] == 0
    index_github_data(github_data(), connector.organization_id, connector.id)
    index_github_data(github_data(), "private-org", "private-connector")
    index_github_data(github_data(), connector.organization_id, "deleted-connector")
    response = client.post("/api/search", headers=headers, json={"query": " repository branches ", "top_k": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "repository branches"
    assert body["document_count"] == len(body["results"]) == 4
    assert all(result["metadata"]["connector_id"] == connector.id for result in body["results"])
    assert client.get("/api/search/status", headers=headers).json() == {"collection": "enterprise_documents", "document_count": 4, "embedding_model": settings.EMBEDDING_MODEL}
    for payload in ({"query": "  "}, {"query": "valid", "top_k": 0}, {"query": "valid", "top_k": 21}):
        assert client.post("/api/search", headers=headers, json=payload).status_code == 422


def test_github_sync_indexes_and_developer_can_retrieve(client, db, monkeypatch):
    connector = configured_connector(db, monkeypatch)
    with patch("services.github_service.GitHubConnector") as github:
        github.return_value.sync.return_value = github_data()
        synced = client.post(f"/api/connectors/{connector.id}/sync", headers=login(client, "admin@aekos.com", "admin123"))
    assert synced.status_code == 200
    assert synced.json()["indexing"] == {"status": "indexed", "documents_indexed": 4, "chroma_total": 4, "error": None}
    result = client.post("/api/search", headers=login(client), json={"query": "Redis"})
    assert result.status_code == 200
    assert any("Redis caching" in document["text"] for document in result.json()["results"])


def test_indexing_failure_preserves_successful_github_sync(client, db, monkeypatch):
    connector = configured_connector(db, monkeypatch)
    with patch("services.github_service.GitHubConnector") as github, patch("services.github_service.index_github_data", side_effect=RuntimeError("index offline")):
        github.return_value.sync.return_value = github_data()
        response = client.post(f"/api/connectors/{connector.id}/sync", headers=login(client, "admin@aekos.com", "admin123"))
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["indexing"]["status"] == "error"
    db.refresh(connector)
    assert connector.status == "synced"
    assert connector.configuration.last_sync is not None


def test_search_failure_is_safe_and_retryable(client, db, monkeypatch):
    configured_connector(db, monkeypatch)
    with patch("services.semantic_search_service.get_chroma_service", side_effect=RuntimeError("private internals")):
        response = client.post("/api/search", headers=login(client), json={"query": "Redis"})
    assert response.status_code == 503
    assert "private internals" not in response.text
