from unittest.mock import Mock, patch
import pytest

from graph.neo4j_service import Neo4jService
from services.graph_context_service import retrieve_graph_context, permitted_github_repositories


RESULTS = [{"metadata": {"source": "github", "repository": "AwesomeWiz/ekos"}}]
EDGES = [{"source": "contributor", "relationship": "COMMITTED", "target": "abc123"},
         {"source": "abc123", "relationship": "BELONGS_TO", "target": "ekos"}]


def test_connection_defaults_use_central_settings():
    with patch("graph.neo4j_service.settings") as config, patch("graph.neo4j_service.GraphDatabase.driver") as driver:
        config.NEO4J_URI = "bolt://configured-host:7687"
        config.NEO4J_USERNAME = "configured-user"
        config.NEO4J_PASSWORD = "configured-password"
        service = Neo4jService()
        assert service.uri == config.NEO4J_URI
        assert service.username == config.NEO4J_USERNAME
        driver.assert_called_once_with(config.NEO4J_URI, auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD))


def test_explicit_connection_overrides_and_timeout_are_preserved():
    with patch("graph.neo4j_service.GraphDatabase.driver") as driver:
        service = Neo4jService(uri="bolt://test-host:7687", username="test-user", password="test-password", connection_timeout=2)
        assert service.uri == "bolt://test-host:7687"
        assert service.username == "test-user"
        driver.assert_called_once_with("bolt://test-host:7687", auth=("test-user", "test-password"),
                                       connection_timeout=2, connection_acquisition_timeout=5.0)


def test_partial_overrides_keep_settings_for_unspecified_values():
    with patch("graph.neo4j_service.settings") as config, patch("graph.neo4j_service.GraphDatabase.driver") as driver:
        config.NEO4J_URI = "bolt://configured-host:7687"
        config.NEO4J_USERNAME = "configured-user"
        config.NEO4J_PASSWORD = "configured-password"
        Neo4jService(username="override-user", password="")
        driver.assert_called_once_with(config.NEO4J_URI, auth=("override-user", ""))


def test_existing_driver_executes_a_bounded_parameterized_read_only_query():
    with patch("graph.neo4j_service.GraphDatabase.driver") as driver:
        service = Neo4jService()
        session = driver.return_value.session.return_value.__enter__.return_value
        session.run.return_value = [Mock(data=Mock(return_value=edge)) for edge in EDGES]
        assert service.get_github_relationships(["AwesomeWiz/ekos"], ["contributor"], limit=6) == EDGES
        driver.return_value.session.assert_called_once_with(default_access_mode="READ")
        query = session.run.call_args.args[0]
        parameters = session.run.call_args.kwargs
        assert "COMMITTED" in query.text and "BELONGS_TO" in query.text
        assert "MERGE" not in query.text and "CREATE" not in query.text
        assert "AwesomeWiz/ekos" not in query.text
        assert query.timeout == 5.0
        assert parameters["repository_ids"] == ["AwesomeWiz/ekos"]
        assert parameters["repository_urls"] == ["https://github.com/AwesomeWiz/ekos"]
        assert parameters["commit_limit"] == 3 and parameters["limit"] == 6
        service.close()
        driver.return_value.close.assert_called_once()


def test_empty_repository_scope_does_not_query_graph():
    with patch("graph.neo4j_service.GraphDatabase.driver") as driver:
        assert Neo4jService().get_github_relationships([], []) == []
        driver.return_value.session.assert_not_called()


def test_context_uses_only_permitted_repository_ids_and_closes_connection():
    with patch("services.graph_context_service.Neo4jService") as service:
        service.return_value.get_github_contributors.return_value = EDGES
        result = retrieve_graph_context("Who contributed to ekos?", RESULTS + RESULTS + [{"metadata": {"source": "jira", "repository": "private/repo"}}])
    assert result == EDGES
    assert service.call_args.kwargs["connection_timeout"] == 2.0
    service.return_value.get_github_contributors.assert_called_once_with(["AwesomeWiz/ekos"], limit=6)
    service.return_value.close.assert_called_once()


def test_graph_errors_are_optional_and_close_the_driver():
    with patch("services.graph_context_service.Neo4jService") as service:
        service.return_value.get_github_contributors.side_effect = RuntimeError("graph offline")
        assert retrieve_graph_context("Contributors?", RESULTS) == []
        service.return_value.close.assert_called_once()


def test_no_graph_matches_returns_empty_context():
    with patch("services.graph_context_service.Neo4jService") as service:
        service.return_value.get_github_contributors.return_value = []
        assert retrieve_graph_context("Contributors?", RESULTS) == []


def test_unscoped_or_invalid_repository_names_never_open_neo4j():
    with patch("services.graph_context_service.Neo4jService") as service:
        assert retrieve_graph_context("Contributors?", []) == []
        assert retrieve_graph_context("Contributors?", [{"metadata": {"source": "github", "repository": "ekos"}}]) == []
        assert retrieve_graph_context("Contributors?", [{"metadata": {"source": "github", "repository": "owner/repo' MATCH (n)"}}]) == []
        service.assert_not_called()


@pytest.mark.parametrize("source", ["jira", "confluence", "slack"])
def test_normalized_graph_context_uses_scoped_entity_ids(source):
    entity_id = f"{source}:org:connector:Issue:1"
    results = [{"metadata": {"source": source, "organization_id": "org", "connector_id": "connector", "knowledge_entity_id": entity_id}}]
    with patch("services.graph_context_service.Neo4jService") as service:
        service.return_value.get_knowledge_relationships.return_value = EDGES
        assert retrieve_graph_context("Related knowledge?", results) == EDGES
        service.return_value.get_knowledge_relationships.assert_called_once_with([entity_id], limit=6)
        service.return_value.get_github_relationships.assert_not_called()
        service.return_value.close.assert_called_once()


def test_normalized_graph_context_rejects_foreign_entity_ids():
    with patch("services.graph_context_service.Neo4jService") as service:
        results = [{"metadata": {"source": "jira", "organization_id": "org", "connector_id": "connector", "knowledge_entity_id": "jira:other-org:connector:Issue:1"}}]
        assert retrieve_graph_context("Related knowledge?", results) == []
        service.assert_not_called()


def test_normalized_relationship_query_is_bounded_and_read_only():
    with patch("graph.neo4j_service.GraphDatabase.driver") as driver:
        session = driver.return_value.session.return_value.__enter__.return_value
        session.run.return_value = EDGES
        service = Neo4jService()
        assert service.get_knowledge_relationships(["jira:org:connector:Issue:1"], limit=100) == EDGES
        query = session.run.call_args.args[0]
        assert query.timeout == 5
        assert "MERGE" not in query.text and "CREATE" not in query.text
        assert "source.organization_id = target.organization_id" in query.text
        assert session.run.call_args.kwargs["limit"] == 6
        driver.return_value.session.assert_called_once_with(default_access_mode="READ")


def test_contributor_query_groups_by_person_before_limit():
    with patch("graph.neo4j_service.GraphDatabase.driver") as driver:
        session = driver.return_value.session.return_value.__enter__.return_value
        session.run.return_value = [Mock(data=Mock(return_value=EDGES[0]))]
        service = Neo4jService()
        assert service.get_github_contributors(["AwesomeWiz/ekos"], limit=100) == [EDGES[0]]
        query = session.run.call_args.args[0]
        assert "min(c.id)" in query.text
        assert "COMMITTED" in query.text and "BELONGS_TO" in query.text
        assert "MERGE" not in query.text and "CREATE" not in query.text
        assert query.timeout == 5
        assert session.run.call_args.kwargs["limit"] == 6
        driver.return_value.session.assert_called_once_with(default_access_mode="READ")


def test_unknown_repository_does_not_broaden_scope(db):
    from models.connector import Connector, ConnectorConfiguration
    from models.user import User
    user = db.query(User).filter(User.email == "arnold@aekos.com").one()
    db.add(Connector(name="GitHub", type="GitHub", organization_id=user.organization_id,
                     configuration=ConnectorConfiguration(api_url="https://github.com/team/ekos")))
    db.commit()
    assert permitted_github_repositories(db, user, "Who contributed to the ekos repository?") == ["team/ekos"]
    assert permitted_github_repositories(db, user, "Who contributed to the secret repository?") == []
