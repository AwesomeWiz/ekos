from unittest.mock import Mock, patch

from graph.neo4j_service import Neo4jService
from services.graph_context_service import retrieve_graph_context


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
        service.return_value.get_github_relationships.return_value = EDGES
        result = retrieve_graph_context("Who contributed to ekos?", RESULTS + RESULTS + [{"metadata": {"source": "jira", "repository": "private/repo"}}])
    assert result == EDGES
    assert service.call_args.kwargs["connection_timeout"] == 2.0
    service.return_value.get_github_relationships.assert_called_once_with(["AwesomeWiz/ekos"], ["ekos"], limit=6)
    service.return_value.close.assert_called_once()


def test_graph_errors_are_optional_and_close_the_driver():
    with patch("services.graph_context_service.Neo4jService") as service:
        service.return_value.get_github_relationships.side_effect = RuntimeError("graph offline")
        assert retrieve_graph_context("Contributors?", RESULTS) == []
        service.return_value.close.assert_called_once()


def test_no_graph_matches_returns_empty_context():
    with patch("services.graph_context_service.Neo4jService") as service:
        service.return_value.get_github_relationships.return_value = []
        assert retrieve_graph_context("Contributors?", RESULTS) == []


def test_unscoped_or_invalid_repository_names_never_open_neo4j():
    with patch("services.graph_context_service.Neo4jService") as service:
        assert retrieve_graph_context("Contributors?", []) == []
        assert retrieve_graph_context("Contributors?", [{"metadata": {"source": "github", "repository": "ekos"}}]) == []
        assert retrieve_graph_context("Contributors?", [{"metadata": {"source": "github", "repository": "owner/repo' MATCH (n)"}}]) == []
        service.assert_not_called()
