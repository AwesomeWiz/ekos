from unittest.mock import patch

import httpx

from config.settings import settings
from models.connector import Connector
from models.organization import Organization
from models.user import User
from services.demo_seed import seed_demo


def auth(client, email, password):
    response = client.post("/api/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def configured_seed(db, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "server-only-test-token")
    monkeypatch.setattr(settings, "GITHUB_OWNER", "ekos-team")
    monkeypatch.setattr(settings, "GITHUB_REPO", "demo-repo")
    seed_demo(db)
    return db.query(Connector).filter(Connector.name == "GitHub").one()


def test_demo_seed_is_idempotent_and_preserves_existing_accounts(db, client, monkeypatch):
    user = db.query(User).filter(User.email == "arnold@aekos.com").one()
    existing_hash = user.password_hash
    github = configured_seed(db, monkeypatch)
    connector_id = github.id
    assert github.status == "configured"
    assert github.configuration.encrypted_token is None
    seed_demo(db)
    assert db.query(Connector).filter(Connector.name == "GitHub").count() == 1
    assert db.query(Connector).filter(Connector.name == "GitHub").one().id == connector_id
    assert db.query(User).filter(User.email == "arnold@aekos.com").one().password_hash == existing_hash
    developer = auth(client, "arnold@aekos.com", "password123")
    listed = client.get("/api/connectors", headers=developer)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == connector_id
    assert "server-only-test-token" not in listed.text


def test_seed_reuses_a_registered_github_and_clears_stale_connected_status(db, monkeypatch):
    org = db.query(Organization).filter(Organization.name == "ABC Solutions").one()
    existing = Connector(name="Team repository", type="GitHub", organization_id=org.id, status="synced")
    db.add(existing)
    db.commit()
    connector_id = existing.id
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "")
    monkeypatch.setattr(settings, "GITHUB_OWNER", "")
    monkeypatch.setattr(settings, "GITHUB_REPO", "")

    seed_demo(db)
    seed_demo(db)

    connectors = db.query(Connector).filter(Connector.organization_id == org.id).all()
    assert len(connectors) == 1
    assert connectors[0].id == connector_id
    assert connectors[0].name == "Team repository"
    assert connectors[0].status == "not_configured"


def test_profile_reads_role_permissions_from_database(client):
    developer = auth(client, "arnold@aekos.com", "password123")
    administrator = auth(client, "admin@aekos.com", "admin123")
    dev_profile = client.get("/api/profile", headers=developer).json()
    admin_profile = client.get("/api/profile", headers=administrator).json()
    assert dev_profile["role"] == "Developer"
    assert dev_profile["permissions"] == [{"resource": "connectors", "action": "read"}]
    assert admin_profile["role"] == "Administrator"
    assert {item["action"] for item in admin_profile["permissions"]} == {"read", "manage", "test", "sync"}


def test_rbac_denies_developer_and_allows_admin_test_and_sync(db, client, monkeypatch):
    github = configured_seed(db, monkeypatch)
    developer = auth(client, "arnold@aekos.com", "password123")
    administrator = auth(client, "admin@aekos.com", "admin123")
    for suffix in ("test", "sync"):
        denied = client.post(f"/api/connectors/{github.id}/{suffix}", headers=developer)
        assert denied.status_code == 403
    denied_create = client.post("/api/connectors", json={"name": "Other", "type": "GitHub"}, headers=developer)
    assert denied_create.status_code == 403
    denied_update = client.put(f"/api/connectors/{github.id}", json={"status": "paused"}, headers=developer)
    assert denied_update.status_code == 403
    denied_delete = client.delete(f"/api/connectors/{github.id}", headers=developer)
    assert denied_delete.status_code == 403
    assert db.query(Connector).filter(Connector.id == github.id).one().status == "configured"

    with patch("services.github_service.GitHubConnector") as connector_class:
        instance = connector_class.return_value
        instance.test_connection.return_value = {"login": "demo-member"}
        tested = client.post(f"/api/connectors/{github.id}/test", headers=administrator)
        assert tested.status_code == 200
        assert tested.json() == {"status": "connected", "connector": "GitHub", "account": "demo-member"}
        connector_class.assert_called_with("server-only-test-token", "ekos-team", "demo-repo")
        instance.sync.return_value = {
            "repository": {"full_name": "ekos-team/demo-repo", "default_branch": "main"},
            "branches": [{"name": "main"}, {"name": "develop"}],
            "commits": [{"sha": "abc"}], "issues": [{"number": 42}, {"number": 43}],
        }
        synced = client.post(f"/api/connectors/{github.id}/sync", headers=administrator)
        assert synced.status_code == 200
        data = synced.json()
        assert data["repository"] == "ekos-team/demo-repo"
        assert data["default_branch"] == "main"
        assert (data["branches"], data["commits"], data["issues"]) == (2, 1, 2)
        instance.sync.assert_called_once()
    db.refresh(github)
    assert github.status == "synced"
    assert github.configuration.last_sync is not None
    listed = client.get("/api/connectors", headers=developer).json()
    assert listed[0]["configuration"]["last_sync"] is not None


def test_unconfigured_and_failed_github_actions_are_honest(db, client, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "")
    monkeypatch.setattr(settings, "GITHUB_OWNER", "")
    monkeypatch.setattr(settings, "GITHUB_REPO", "")
    seed_demo(db)
    github = db.query(Connector).filter(Connector.name == "GitHub").one()
    administrator = auth(client, "admin@aekos.com", "admin123")
    assert github.status == "not_configured"
    assert client.post(f"/api/connectors/{github.id}/sync", headers=administrator).status_code == 409
    configured_seed(db, monkeypatch)
    with patch("services.github_service.GitHubConnector") as connector_class:
        connector_class.return_value.test_connection.side_effect = httpx.ConnectError("unreachable")
        failed = client.post(f"/api/connectors/{github.id}/test", headers=administrator)
    assert failed.status_code == 502
    assert failed.json()["detail"] == "GitHub could not be reached. Please try again."
    db.refresh(github)
    assert github.status == "error"
    assert github.configuration.last_sync is None


def test_cross_organization_connector_is_hidden(db, client, monkeypatch):
    github = configured_seed(db, monkeypatch)
    administrator = auth(client, "admin@aekos.com", "admin123")
    github.organization_id = None
    db.commit()
    assert client.post(f"/api/connectors/{github.id}/sync", headers=administrator).status_code == 404
    assert client.delete(f"/api/connectors/{github.id}", headers=administrator).status_code == 404


def test_actual_github_connector_adapter_with_stubbed_http(db, client, monkeypatch):
    github = configured_seed(db, monkeypatch)
    administrator = auth(client, "admin@aekos.com", "admin123")
    calls = []

    def github_response(url, headers, **kwargs):
        assert headers["Authorization"] == "Bearer server-only-test-token"
        calls.append(url)
        if url.endswith("/user"):
            data = {"login": "demo-member"}
        elif url.endswith("/repos/ekos-team/demo-repo"):
            data = {"full_name": "ekos-team/demo-repo", "name": "demo-repo", "owner": {"login": "ekos-team"}, "default_branch": "main"}
        elif url.endswith("/branches"):
            data = [{"name": "main", "protected": False}]
        elif url.endswith("/commits"):
            data = [{"sha": "abc123", "commit": {"message": "Add cache"}, "author": {"login": "demo-member"}, "html_url": "https://github.com/ekos-team/demo-repo/commit/abc123"}]
        elif url.endswith("/issues"):
            data = [{"number": 42, "title": "Caching", "state": "open", "html_url": "https://github.com/ekos-team/demo-repo/issues/42"}]
        elif url.endswith("/readme"):
            data = {"name": "README.md", "path": "README.md", "encoding": "base64", "content": ""}
        else:
            raise AssertionError(f"Unexpected GitHub route: {url}")
        return httpx.Response(200, json=data, request=httpx.Request("GET", url))

    with patch("connectors.github.client.httpx.get", side_effect=github_response):
        assert client.post(f"/api/connectors/{github.id}/test", headers=administrator).json()["account"] == "demo-member"
        result = client.post(f"/api/connectors/{github.id}/sync", headers=administrator)
    assert result.status_code == 200
    assert (result.json()["branches"], result.json()["commits"], result.json()["issues"]) == (1, 1, 1)
    assert len(calls) == 6
    db.refresh(github)
    assert github.configuration.last_sync is not None
