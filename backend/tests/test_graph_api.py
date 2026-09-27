from unittest.mock import patch

from models.connector import Connector, ConnectorConfiguration
from models.permission import Permission
from models.user import User
from graph.neo4j_service import Neo4jService

GRAPH = {"nodes": [{"id": "Repository:team/ekos", "label": "ekos", "type": "Repository", "description": "team/ekos"},
                   {"id": "Commit:abc", "label": "abc", "type": "Commit", "description": "Add caching"}],
         "edges": [{"source": "Commit:abc", "target": "Repository:team/ekos", "relationship": "BELONGS_TO"}]}


def login(client):
    response = client.post("/api/login", json={"email": "arnold@aekos.com", "password": "password123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def connector(db, organization_id, url, kind="GitHub"):
    item = Connector(name="Repository", type=kind, organization_id=organization_id)
    db.add(item); db.flush()
    db.add(ConnectorConfiguration(connector_id=item.id, api_url=url)); db.commit()


def test_graph_requires_authentication_and_existing_permission(client, db):
    with patch("api.graph.Neo4jService") as service:
        assert client.get("/api/graph").status_code == 401
        headers = login(client)
        user = db.query(User).filter(User.email == "arnold@aekos.com").one()
        db.query(Permission).filter(Permission.role_id == user.role_id, Permission.resource == "connectors", Permission.action == "read").delete()
        db.commit()
        assert client.get("/api/graph", headers=headers).status_code == 403
        service.assert_not_called()


def test_graph_scopes_repository_reads_and_returns_contract(client, db):
    user = db.query(User).filter(User.email == "arnold@aekos.com").one()
    connector(db, user.organization_id, "https://github.com/team/ekos")
    connector(db, None, "https://github.com/private/secret")
    connector(db, user.organization_id, "https://github.com/private/jira", "Jira")
    connector(db, user.organization_id, "https://untrusted.example/team/ekos")
    with patch("api.graph.Neo4jService") as service:
        service.return_value.get_github_graph.return_value = GRAPH
        response = client.get("/api/graph", headers=login(client))
    assert response.status_code == 200
    assert response.json() == GRAPH
    service.return_value.get_github_graph.assert_called_once_with(["team/ekos"], limit=6)
    assert service.call_args.kwargs["connection_timeout"] == 2.0
    service.return_value.close.assert_called_once()


def test_no_connector_scope_returns_empty_without_connecting(client):
    with patch("api.graph.Neo4jService") as service:
        assert client.get("/api/graph", headers=login(client)).json() == {"nodes": [], "edges": []}
        service.assert_not_called()


def test_offline_graph_returns_clean_error_and_closes_service(client, db):
    user = db.query(User).filter(User.email == "arnold@aekos.com").one()
    connector(db, user.organization_id, "https://github.com/team/ekos")
    with patch("api.graph.Neo4jService") as service:
        service.return_value.get_github_graph.side_effect = RuntimeError("private diagnostic")
        response = client.get("/api/graph", headers=login(client))
        service.return_value.close.assert_called_once()
    assert response.status_code == 503
    assert "Knowledge graph is unavailable" in response.json()["detail"]
    assert "private diagnostic" not in response.text


def test_no_matching_graph_paths_returns_empty(client, db):
    user = db.query(User).filter(User.email == "arnold@aekos.com").one()
    connector(db, user.organization_id, "https://github.com/team/ekos")
    with patch("api.graph.Neo4jService") as service:
        service.return_value.get_github_graph.return_value = {"nodes": [], "edges": []}
        assert client.get("/api/graph", headers=login(client)).json() == {"nodes": [], "edges": []}


def test_graph_query_is_read_only_bounded_and_deduplicates_paths():
    record = {"repository_id": "team/ekos", "repository_name": "ekos", "commit_id": "abc",
              "message": "Add caching", "user_id": "developer", "user_name": "Developer"}
    with patch("graph.neo4j_service.GraphDatabase.driver") as driver:
        service = Neo4jService()
        session = driver.return_value.session.return_value.__enter__.return_value
        session.run.return_value = [record, record]
        graph = service.get_github_graph(["team/ekos"], limit=100)
        assert len(graph["nodes"]) == 3 and len(graph["edges"]) == 2
        assert {node["type"] for node in graph["nodes"]} == {"Repository", "Commit", "User"}
        driver.return_value.session.assert_called_once_with(default_access_mode="READ")
        query = session.run.call_args.args[0]
        assert "MERGE" not in query.text and "CREATE" not in query.text
        assert "team/ekos" not in query.text and "LIMIT $limit" in query.text
        assert query.timeout == 5.0
        assert session.run.call_args.kwargs["limit"] == 6
        assert session.run.call_args.kwargs["repository_ids"] == ["team/ekos"]
        assert session.run.call_args.kwargs["repository_urls"] == ["https://github.com/team/ekos"]


def test_graph_query_without_scope_or_contributor_is_safe():
    with patch("graph.neo4j_service.GraphDatabase.driver") as driver:
        service = Neo4jService()
        assert service.get_github_graph([]) == {"nodes": [], "edges": []}
        driver.return_value.session.assert_not_called()
        session = driver.return_value.session.return_value.__enter__.return_value
        session.run.return_value = [{"repository_id": "team/ekos", "repository_name": "ekos", "commit_id": "abc",
                                     "message": None, "user_id": None, "user_name": None}]
        result = service.get_github_graph(["team/ekos"])
        assert len(result["nodes"]) == 2 and len(result["edges"]) == 1
