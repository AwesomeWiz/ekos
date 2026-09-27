import base64
from unittest.mock import Mock, patch
import httpx
import pytest

from connectors.jira.client import JiraClient
from connectors.jira.connector import JiraConnector, extract_plain_text
from connectors.models import NormalizedRecord


# ---------------------------------------------------------------------------
# Fixtures & Sample Mock Data
# ---------------------------------------------------------------------------

SAMPLE_USER = {
    "accountId": "5b10ac8d82e05b22cc7d4ef5",
    "displayName": "Alen Saji",
    "emailAddress": "alen@example.com",
    "active": True,
}

SAMPLE_PROJECTS = [
    {"id": "10000", "key": "EKOS", "name": "AEKOS Core", "projectTypeKey": "software"},
    {"id": "10001", "key": "INFRA", "name": "Infrastructure", "projectTypeKey": "business"},
]

SAMPLE_ADF_DESCRIPTION = {
    "version": 1,
    "type": "doc",
    "content": [
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "Encountered a connection timeout with Redis cache."}
            ],
        },
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "Need to adjust retry backoff policy."}
            ],
        },
    ],
}

SAMPLE_ADF_COMMENT = {
    "version": 1,
    "type": "doc",
    "content": [
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "Identified root cause in socket timeout settings."}
            ],
        }
    ],
}

SAMPLE_ISSUES_RAW = [
    {
        "id": "10050",
        "key": "EKOS-42",
        "fields": {
            "summary": "Authentication timeout in Redis",
            "description": SAMPLE_ADF_DESCRIPTION,
            "status": {"name": "In Progress", "id": "3"},
            "priority": {"name": "High", "id": "2"},
            "reporter": {"displayName": "Alice Reporter", "emailAddress": "alice@example.com"},
            "creator": {"displayName": "Alice Reporter", "emailAddress": "alice@example.com"},
            "assignee": {"displayName": "Bob Assignee", "emailAddress": "bob@example.com"},
            "project": {"key": "EKOS", "name": "AEKOS Core"},
            "labels": ["backend", "performance"],
            "created": "2026-09-20T10:00:00.000Z",
            "updated": "2026-09-21T14:30:00.000Z",
            "comment": {
                "comments": [
                    {
                        "id": "101",
                        "author": {"displayName": "Charlie Contributor"},
                        "body": SAMPLE_ADF_COMMENT,
                        "created": "2026-09-20T11:00:00.000Z",
                        "updated": "2026-09-20T11:05:00.000Z",
                    }
                ]
            },
        },
    },
    {
        "id": "10051",
        "key": "EKOS-43",
        "fields": {
            "summary": "Update API documentation",
            "description": "Ensure Swagger docs include new connector routes.",
            "status": {"name": "To Do"},
            "priority": {"name": "Medium"},
            "reporter": {"displayName": "Dave Lead"},
            "creator": None,
            "assignee": None,
            "project": {"key": "EKOS"},
            "labels": ["docs"],
            "created": "2026-09-22T09:00:00.000Z",
            "updated": "2026-09-22T09:00:00.000Z",
            "comment": {"comments": []},
        },
    },
]


# ---------------------------------------------------------------------------
# Tests: Plain Text & ADF Extraction
# ---------------------------------------------------------------------------

def test_extract_plain_text_empty_and_string():
    assert extract_plain_text(None) == ""
    assert extract_plain_text("") == ""
    assert extract_plain_text("Simple plain description") == "Simple plain description"


def test_extract_plain_text_from_adf_structure():
    extracted = extract_plain_text(SAMPLE_ADF_DESCRIPTION)
    assert "Encountered a connection timeout with Redis cache." in extracted
    assert "Need to adjust retry backoff policy." in extracted
    assert "\n" in extracted


# ---------------------------------------------------------------------------
# Tests: JiraClient (Mocked Network)
# ---------------------------------------------------------------------------

def test_jira_client_cloud_basic_auth_headers():
    client = JiraClient(
        base_url="https://aekos.atlassian.net",
        email="alen@example.com",
        token="my-api-token",
    )
    headers = client._get_headers()
    expected_creds = base64.b64encode(b"alen@example.com:my-api-token").decode("utf-8")
    assert headers["Authorization"] == f"Basic {expected_creds}"
    assert headers["Accept"] == "application/json"


def test_jira_client_server_bearer_auth_headers():
    client = JiraClient(
        base_url="https://jira.internal-corp.com",
        token="pat-token-12345",
    )
    headers = client._get_headers()
    assert headers["Authorization"] == "Bearer pat-token-12345"


@patch("httpx.get")
def test_jira_client_test_connection_success(mock_get):
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_USER
    mock_get.return_value = mock_resp

    client = JiraClient("https://aekos.atlassian.net", "token", "alen@example.com")
    result = client.test_connection()

    assert result["displayName"] == "Alen Saji"
    assert result["emailAddress"] == "alen@example.com"
    mock_get.assert_called_once()
    assert "/rest/api/2/myself" in mock_get.call_args[0][0]


@patch("httpx.get")
def test_jira_client_test_connection_auth_failure(mock_get):
    mock_resp = Mock()
    mock_resp.status_code = 401
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="401 Unauthorized", request=Mock(), response=mock_resp
    )
    mock_get.return_value = mock_resp

    client = JiraClient("https://aekos.atlassian.net", "wrong-token", "alen@example.com")
    with pytest.raises(httpx.HTTPStatusError):
        client.test_connection()


@patch("httpx.get")
def test_jira_client_get_projects(mock_get):
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_PROJECTS
    mock_get.return_value = mock_resp

    client = JiraClient("https://aekos.atlassian.net", "token", "alen@example.com")
    projects = client.get_projects()

    assert len(projects) == 2
    assert projects[0]["key"] == "EKOS"


@patch("httpx.get")
def test_jira_client_get_issues(mock_get):
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"issues": SAMPLE_ISSUES_RAW}
    mock_get.return_value = mock_resp

    client = JiraClient("https://aekos.atlassian.net", "token", "alen@example.com")
    issues = client.get_issues(project_key="EKOS")

    assert len(issues) == 2
    assert issues[0]["key"] == "EKOS-42"
    assert "/rest/api/3/search/jql" in mock_get.call_args[0][0]
    params = mock_get.call_args[1]["params"]
    assert 'project = "EKOS"' in params["jql"]


@patch("httpx.get")
def test_jira_client_get_issues_legacy_fallback_on_410(mock_get):
    resp_410 = Mock(status_code=410)
    resp_200 = Mock(status_code=200, json=lambda: {"issues": SAMPLE_ISSUES_RAW})
    mock_get.side_effect = [resp_410, resp_200]

    client = JiraClient("https://aekos.atlassian.net", "token", "alen@example.com")
    issues = client.get_issues(project_key="EKOS")

    assert len(issues) == 2
    assert mock_get.call_count == 2
    assert "/rest/api/2/search/jql" in mock_get.call_args_list[1][0][0]



# ---------------------------------------------------------------------------
# Tests: JiraConnector & Normalization
# ---------------------------------------------------------------------------

def test_jira_connector_transform_data_normalization():
    connector = JiraConnector(
        base_url="https://aekos.atlassian.net",
        token="test-token",
        email="alen@example.com",
        project_key="EKOS",
    )

    raw_data = {
        "user": SAMPLE_USER,
        "projects": SAMPLE_PROJECTS,
        "issues": SAMPLE_ISSUES_RAW,
    }

    records = connector.transform_data(raw_data)

    # 2 issues: EKOS-42 has 1 comment, EKOS-43 has 0 comments -> Total 3 records
    assert len(records) == 3

    # Validate Issue Record (EKOS-42)
    issue_42 = next(r for r in records if r.external_id == "EKOS-42")
    assert issue_42.source == "jira"
    assert issue_42.entity_type == "Issue"
    assert issue_42.title == "Authentication timeout in Redis"
    assert "Encountered a connection timeout with Redis cache." in issue_42.content
    # Per rule: author must be reporter/creator, NOT assignee
    assert issue_42.author == "Alice Reporter"
    assert issue_42.project == "EKOS"
    assert issue_42.timestamp == "2026-09-20T10:00:00.000Z"

    # Jira-specific metadata
    assert issue_42.metadata["assignee"] == "Bob Assignee"
    assert issue_42.metadata["reporter"] == "Alice Reporter"
    assert issue_42.metadata["status"] == "In Progress"
    assert issue_42.metadata["priority"] == "High"
    assert issue_42.metadata["labels"] == ["backend", "performance"]
    assert issue_42.metadata["comment_count"] == 1
    assert issue_42.metadata["url"] == "https://aekos.atlassian.net/browse/EKOS-42"

    # Validate Comment Record (separate entity, not duplicated in Issue content)
    comment_rec = next(r for r in records if r.entity_type == "Comment")
    assert comment_rec.source == "jira"
    assert comment_rec.external_id == "EKOS-42-comment-101"
    assert comment_rec.title == "Comment on EKOS-42"
    assert comment_rec.content == "Identified root cause in socket timeout settings."
    assert comment_rec.author == "Charlie Contributor"
    assert comment_rec.project == "EKOS"
    assert comment_rec.timestamp == "2026-09-20T11:00:00.000Z"
    assert comment_rec.metadata["issue_key"] == "EKOS-42"

    # Validate Issue Record (EKOS-43)
    issue_43 = next(r for r in records if r.external_id == "EKOS-43")
    assert issue_43.author == "Dave Lead"
    assert issue_43.metadata["assignee"] is None
    assert issue_43.metadata["comment_count"] == 0


@patch.object(JiraClient, "test_connection", return_value=SAMPLE_USER)
@patch.object(JiraClient, "get_projects", return_value=SAMPLE_PROJECTS)
@patch.object(JiraClient, "get_issues", return_value=SAMPLE_ISSUES_RAW)
def test_jira_connector_sync_e2e(mock_issues, mock_projects, mock_auth):
    connector = JiraConnector(
        base_url="https://aekos.atlassian.net",
        token="test-token",
        email="alen@example.com",
        project_key="EKOS",
    )

    results = connector.sync()

    # Results should be serialized dictionaries matching NormalizedRecord structure
    assert isinstance(results, list)
    assert len(results) == 3

    for item in results:
        assert isinstance(item, dict)
        assert "source" in item
        assert "entity_type" in item
        assert "external_id" in item
        assert "title" in item
        assert "content" in item
        assert "author" in item
        assert "project" in item
        assert "timestamp" in item
        assert "metadata" in item
        assert item["source"] == "jira"
