import base64
from unittest.mock import Mock, patch
import httpx
import pytest

from connectors.confluence.client import ConfluenceClient
from connectors.confluence.connector import ConfluenceConnector
from connectors.confluence.html_converter import html_to_plain_text
from connectors.models import NormalizedRecord


# ---------------------------------------------------------------------------
# Sample Mock Data
# ---------------------------------------------------------------------------

SAMPLE_CONFLUENCE_USER = {
    "type": "known",
    "username": "alen.saji",
    "userKey": "402880824ff933b2014ff9345a700002",
    "displayName": "Alen Saji",
    "email": "alen@example.com",
}

SAMPLE_SPACES_PAGE_1 = {
    "results": [
        {
            "id": 1001,
            "key": "EKOS",
            "name": "AEKOS Core",
            "type": "global",
            "description": {"plain": {"value": "Autonomous Enterprise Knowledge Operating System"}},
            "_links": {"webui": "/spaces/EKOS"},
        }
    ],
    "start": 0,
    "limit": 1,
    "size": 1,
    "_links": {"next": "/rest/api/space?start=1&limit=1"},
}

SAMPLE_SPACES_PAGE_2 = {
    "results": [
        {
            "id": 1002,
            "key": "INFRA",
            "name": "DevOps & Infrastructure",
            "type": "global",
            "description": {"plain": {"value": "Cloud infrastructure and CI/CD pipelines"}},
            "_links": {"webui": "/spaces/INFRA"},
        }
    ],
    "start": 1,
    "limit": 1,
    "size": 1,
    "_links": {},
}

SAMPLE_HTML_STORAGE = """
<p>Welcome to <strong>AEKOS</strong> documentation &amp; guides.</p>
<h2>Key Capabilities</h2>
<ul>
    <li>Connector Framework for enterprise data</li>
    <li>Vector Search with ChromaDB</li>
    <li>Knowledge Graph with Neo4j</li>
</ul>
<p>For more details, contact the &quot;core team&quot;.</p>
"""

SAMPLE_PAGES_RAW = [
    {
        "id": "10021",
        "type": "page",
        "title": "System Architecture Overview",
        "space": {"key": "EKOS", "name": "AEKOS Core"},
        "version": {
            "number": 3,
            "when": "2026-09-22T14:30:00.000Z",
            "by": {"displayName": "Alice Architect", "email": "alice@example.com"},
        },
        "history": {
            "createdDate": "2026-09-20T10:00:00.000Z",
            "createdBy": {"displayName": "Alice Architect"},
        },
        "metadata": {
            "labels": {
                "results": [
                    {"name": "architecture"},
                    {"name": "knowledge-base"},
                ]
            }
        },
        "body": {
            "storage": {
                "value": SAMPLE_HTML_STORAGE,
                "representation": "storage",
            }
        },
        "_links": {"webui": "/spaces/EKOS/pages/10021"},
    },
    {
        "id": "10022",
        "type": "page",
        "title": "Empty Page Example",
        "space": {"key": "EKOS", "name": "AEKOS Core"},
        "version": {
            "number": 1,
            "when": "2026-09-23T11:00:00.000Z",
            "by": {"displayName": "Bob Builder"},
        },
        "history": {
            "createdDate": "2026-09-23T11:00:00.000Z",
            "createdBy": {"displayName": "Bob Builder"},
        },
        "metadata": {"labels": {"results": []}},
        "body": {
            "storage": {
                "value": None,
            }
        },
        "_links": {"webui": "/spaces/EKOS/pages/10022"},
    },
]


# ---------------------------------------------------------------------------
# Tests: HTML to Clean Plain Text Converter
# ---------------------------------------------------------------------------

def test_html_to_plain_text_empty_and_none():
    assert html_to_plain_text(None) == ""
    assert html_to_plain_text("") == ""
    assert html_to_plain_text("   ") == ""


def test_html_to_plain_text_storage_xhtml_conversion():
    text = html_to_plain_text(SAMPLE_HTML_STORAGE)
    # Check that HTML tags are stripped
    assert "<p>" not in text
    assert "<strong>" not in text
    assert "<ul>" not in text
    assert "<li>" not in text
    # Check that HTML entities are decoded
    assert "AEKOS documentation & guides." in text
    assert '"core team"' in text
    # Check list item formatting
    assert "- Connector Framework for enterprise data" in text
    assert "- Vector Search with ChromaDB" in text
    assert "- Knowledge Graph with Neo4j" in text


# ---------------------------------------------------------------------------
# Tests: ConfluenceClient (Mocked Network)
# ---------------------------------------------------------------------------

def test_confluence_client_cloud_basic_auth_headers():
    client = ConfluenceClient(
        base_url="https://aekos.atlassian.net/wiki",
        email="alen@example.com",
        token="my-token-xyz",
    )
    headers = client._get_headers()
    expected = base64.b64encode(b"alen@example.com:my-token-xyz").decode("utf-8")
    assert headers["Authorization"] == f"Basic {expected}"
    assert headers["Accept"] == "application/json"


def test_confluence_client_server_bearer_auth_headers():
    client = ConfluenceClient(
        base_url="https://confluence.internal.com",
        token="bearer-pat-token",
    )
    headers = client._get_headers()
    assert headers["Authorization"] == "Bearer bearer-pat-token"


@patch("httpx.get")
def test_confluence_client_test_connection_success(mock_get):
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_CONFLUENCE_USER
    mock_get.return_value = mock_resp

    client = ConfluenceClient("https://aekos.atlassian.net/wiki", "token", "alen@example.com")
    result = client.test_connection()

    assert result["displayName"] == "Alen Saji"
    mock_get.assert_called_once()
    assert "/rest/api/user/current" in mock_get.call_args[0][0]


@patch("httpx.get")
def test_confluence_client_test_connection_auth_failure(mock_get):
    mock_resp = Mock()
    mock_resp.status_code = 401
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="401 Unauthorized", request=Mock(), response=mock_resp
    )
    mock_get.return_value = mock_resp

    client = ConfluenceClient("https://aekos.atlassian.net/wiki", "bad-token", "alen@example.com")
    with pytest.raises(httpx.HTTPStatusError):
        client.test_connection()


def test_confluence_client_atlassian_cloud_url_normalization():
    # User provides domain without /wiki
    client = ConfluenceClient("https://ekos-demo.atlassian.net", "token", "alen@example.com")
    assert client.base_url == "https://ekos-demo.atlassian.net/wiki"


@patch("httpx.get")
def test_confluence_client_dynamic_wiki_fallback_on_404(mock_get):
    resp_404 = Mock(status_code=404)
    resp_200 = Mock(status_code=200, json=lambda: SAMPLE_CONFLUENCE_USER)
    mock_get.side_effect = [resp_404, resp_200]

    # Non-atlassian.net domain without /wiki
    client = ConfluenceClient("https://confluence.corp.internal", "token", "alen@example.com")
    result = client.test_connection()

    assert result["displayName"] == "Alen Saji"
    assert mock_get.call_count == 2
    assert "https://confluence.corp.internal/wiki/rest/api/user/current" in mock_get.call_args_list[1][0][0]
    assert client.base_url == "https://confluence.corp.internal/wiki"


@patch("httpx.get")
def test_confluence_client_test_connection_space_fallback(mock_get):
    resp_404 = Mock(status_code=404)
    resp_200 = Mock(status_code=200, json=lambda: SAMPLE_SPACES_PAGE_2)
    mock_get.side_effect = [resp_404, resp_200]

    client = ConfluenceClient("https://aekos.atlassian.net/wiki", "token", "alen@example.com")
    result = client.test_connection()

    assert "results" in result
    assert mock_get.call_count == 2
    assert "/rest/api/space" in mock_get.call_args_list[1][0][0]
    assert mock_get.call_args_list[1][1]["params"]["limit"] == 1


@patch("httpx.get")
def test_confluence_client_spaces_v2_fallback_on_404(mock_get):
    resp_404 = Mock(status_code=404)
    resp_200 = Mock(status_code=200, json=lambda: {"results": [{"id": 1, "key": "EKOS", "name": "AEKOS"}], "_links": {}})
    mock_get.side_effect = [resp_404, resp_200]

    client = ConfluenceClient("https://aekos.atlassian.net/wiki", "token", "alen@example.com")
    spaces = client.get_spaces(limit=1)

    assert len(spaces) == 1
    assert mock_get.call_count == 2
    assert "/api/v2/spaces" in mock_get.call_args_list[1][0][0]


@patch("httpx.get")
def test_confluence_client_get_spaces_with_pagination(mock_get):
    resp_p1 = Mock()
    resp_p1.status_code = 200
    resp_p1.json.return_value = SAMPLE_SPACES_PAGE_1

    resp_p2 = Mock()
    resp_p2.status_code = 200
    resp_p2.json.return_value = SAMPLE_SPACES_PAGE_2

    mock_get.side_effect = [resp_p1, resp_p2]

    client = ConfluenceClient("https://aekos.atlassian.net/wiki", "token", "alen@example.com")
    spaces = client.get_spaces(limit=1)

    assert len(spaces) == 2
    assert spaces[0]["key"] == "EKOS"
    assert spaces[1]["key"] == "INFRA"
    assert mock_get.call_count == 2


@patch("httpx.get")
def test_confluence_client_get_pages(mock_get):
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": SAMPLE_PAGES_RAW,
        "start": 0,
        "limit": 50,
        "size": 2,
    }
    mock_get.return_value = mock_resp

    client = ConfluenceClient("https://aekos.atlassian.net/wiki", "token", "alen@example.com")
    pages = client.get_pages(space_key="EKOS")

    assert len(pages) == 2
    assert pages[0]["id"] == "10021"
    params = mock_get.call_args[1]["params"]
    assert params["spaceKey"] == "EKOS"
    assert "body.storage" in params["expand"]


# ---------------------------------------------------------------------------
# Tests: ConfluenceConnector & Normalization
# ---------------------------------------------------------------------------

def test_confluence_connector_transform_data_normalization():
    connector = ConfluenceConnector(
        base_url="https://aekos.atlassian.net/wiki",
        token="token",
        email="alen@example.com",
        space_key="EKOS",
    )

    raw_data = {
        "user": SAMPLE_CONFLUENCE_USER,
        "spaces": SAMPLE_SPACES_PAGE_1["results"],
        "pages": SAMPLE_PAGES_RAW,
    }

    records = connector.transform_data(raw_data)

    # 1 space + 2 pages -> total 3 records
    assert len(records) == 3

    # 1. Validate Space Record (Lightweight structural record)
    space_rec = next(r for r in records if r.entity_type == "Space")
    assert space_rec.source == "confluence"
    assert space_rec.external_id == "space-EKOS"
    assert space_rec.title == "AEKOS Core"
    assert space_rec.content == "Autonomous Enterprise Knowledge Operating System"
    assert space_rec.project == "EKOS"
    assert space_rec.metadata["space_key"] == "EKOS"
    assert space_rec.metadata["space_type"] == "global"

    # 2. Validate Primary Page Record (Clean plain text suitable for ChromaDB)
    page_rec = next(r for r in records if r.external_id == "10021")
    assert page_rec.source == "confluence"
    assert page_rec.entity_type == "Page"
    assert page_rec.title == "System Architecture Overview"
    assert "<p>" not in page_rec.content
    assert "AEKOS documentation & guides." in page_rec.content
    assert "- Connector Framework for enterprise data" in page_rec.content
    assert page_rec.author == "Alice Architect"
    assert page_rec.project == "EKOS"
    assert page_rec.timestamp == "2026-09-22T14:30:00.000Z"

    # Confluence metadata verification
    assert page_rec.metadata["space_key"] == "EKOS"
    assert page_rec.metadata["version_number"] == 3
    assert page_rec.metadata["labels"] == ["architecture", "knowledge-base"]
    assert page_rec.metadata["created_at"] == "2026-09-20T10:00:00.000Z"
    assert page_rec.metadata["modified_at"] == "2026-09-22T14:30:00.000Z"
    assert page_rec.metadata["url"] == "https://aekos.atlassian.net/wiki/spaces/EKOS/pages/10021"

    # 3. Validate Empty Body Page Record (Safe empty string)
    empty_page_rec = next(r for r in records if r.external_id == "10022")
    assert empty_page_rec.content == ""
    assert empty_page_rec.author == "Bob Builder"
    assert empty_page_rec.metadata["labels"] == []


@patch.object(ConfluenceClient, "test_connection", return_value=SAMPLE_CONFLUENCE_USER)
@patch.object(ConfluenceClient, "get_spaces", return_value=SAMPLE_SPACES_PAGE_1["results"])
@patch.object(ConfluenceClient, "get_pages", return_value=SAMPLE_PAGES_RAW)
def test_confluence_connector_sync_e2e(mock_pages, mock_spaces, mock_auth):
    connector = ConfluenceConnector(
        base_url="https://aekos.atlassian.net/wiki",
        token="token",
        email="alen@example.com",
        space_key="EKOS",
    )

    results = connector.sync()

    assert isinstance(results, list)
    assert len(results) == 3

    for item in results:
        assert isinstance(item, dict)
        assert item["source"] == "confluence"
        assert "entity_type" in item
        assert "external_id" in item
        assert "title" in item
        assert "content" in item
        assert "author" in item
        assert "project" in item
        assert "timestamp" in item
        assert "metadata" in item
