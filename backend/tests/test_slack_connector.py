from unittest.mock import Mock, patch
import pytest

from connectors.models import NormalizedRecord
from connectors.slack.client import SlackClient
from connectors.slack.connector import SlackConnector, slack_ts_to_iso


# ---------------------------------------------------------------------------
# Sample Mock Data
# ---------------------------------------------------------------------------

SAMPLE_AUTH_RESPONSE = {
    "ok": True,
    "url": "https://aekos-workspace.slack.com/",
    "team": "AEKOS Engineering",
    "user": "aekos_bot",
    "team_id": "T012345678",
    "user_id": "U_BOT_999",
}

SAMPLE_USERS_PAGE_1 = {
    "ok": True,
    "members": [
        {
            "id": "U101",
            "name": "alice",
            "real_name": "Alice Developer",
            "profile": {
                "display_name": "Alice",
                "real_name": "Alice Developer",
                "title": "Core Engineer",
                "email": "alice@aekos.com",
            },
            "is_bot": False,
        }
    ],
    "response_metadata": {"next_cursor": "cursor_users_p2"},
}

SAMPLE_USERS_PAGE_2 = {
    "ok": True,
    "members": [
        {
            "id": "U102",
            "name": "bob",
            "real_name": "Bob Reviewer",
            "profile": {
                "display_name": "Bob",
                "real_name": "Bob Reviewer",
                "title": "Lead Reviewer",
                "email": "bob@aekos.com",
            },
            "is_bot": False,
        }
    ],
    "response_metadata": {"next_cursor": ""},
}

SAMPLE_CHANNELS_PAGE_1 = {
    "ok": True,
    "channels": [
        {
            "id": "C001",
            "name": "general",
            "is_private": False,
            "topic": {"value": "Company-wide announcements"},
            "purpose": {"value": "General workspace chat"},
            "num_members": 25,
        }
    ],
    "response_metadata": {"next_cursor": "cursor_ch_p2"},
}

SAMPLE_CHANNELS_PAGE_2 = {
    "ok": True,
    "channels": [
        {
            "id": "C002",
            "name": "backend",
            "is_private": True,
            "topic": {"value": "Backend architecture"},
            "purpose": {"value": "Engineering discussions"},
            "num_members": 10,
        }
    ],
    "response_metadata": {"next_cursor": ""},
}

SAMPLE_MESSAGES_PAGE_1 = {
    "ok": True,
    "messages": [
        {
            "type": "message",
            "user": "U101",
            "text": "Starting work on Slack connector prototype.",
            "ts": "1710000000.000100",
            "thread_ts": "1710000000.000100",
            "reply_count": 1,
        }
    ],
    "response_metadata": {"next_cursor": "cursor_msg_p2"},
}

SAMPLE_MESSAGES_PAGE_2 = {
    "ok": True,
    "messages": [
        {
            "type": "message",
            "user": "U102",
            "text": "Confluence connector unit tests passed.",
            "ts": "1710000050.000150",
            "reply_count": 0,
        }
    ],
    "response_metadata": {"next_cursor": ""},
}

# Note: Slack's conversations.replies includes the root message as the first item!
SAMPLE_THREAD_REPLIES = {
    "ok": True,
    "messages": [
        {
            "type": "message",
            "user": "U101",
            "text": "Starting work on Slack connector prototype.",
            "ts": "1710000000.000100",
            "thread_ts": "1710000000.000100",
            "reply_count": 1,
        },
        {
            "type": "message",
            "user": "U102",
            "text": "Looks good! Ping me when PR is ready.",
            "ts": "1710000080.000200",
            "thread_ts": "1710000000.000100",
            "reply_count": 0,
        },
    ],
    "response_metadata": {"next_cursor": ""},
}


# ---------------------------------------------------------------------------
# Tests: Helpers & Utilities
# ---------------------------------------------------------------------------

def test_slack_ts_to_iso():
    assert slack_ts_to_iso(None) is None
    assert slack_ts_to_iso("") is None
    # 1710000000 -> 2024-03-09T16:00:00+00:00
    iso_val = slack_ts_to_iso("1710000000.000100")
    assert iso_val is not None
    assert "2024" in iso_val
    assert "T" in iso_val


# ---------------------------------------------------------------------------
# Tests: SlackClient (Mocked Network)
# ---------------------------------------------------------------------------

def test_slack_client_auth_headers():
    client = SlackClient(token="xoxb-test-token-12345")
    headers = client._get_headers()
    assert headers["Authorization"] == "Bearer xoxb-test-token-12345"
    assert headers["Accept"] == "application/json"


@patch("httpx.post")
def test_slack_client_test_connection_success(mock_post):
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_AUTH_RESPONSE
    mock_post.return_value = mock_resp

    client = SlackClient("xoxb-test-token")
    result = client.test_connection()

    assert result["ok"] is True
    assert result["user"] == "aekos_bot"
    assert result["team"] == "AEKOS Engineering"
    mock_post.assert_called_once()
    assert "/auth.test" in mock_post.call_args[0][0]


@patch("httpx.post")
def test_slack_client_test_connection_failure(mock_post):
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"ok": False, "error": "invalid_auth"}
    mock_post.return_value = mock_resp

    client = SlackClient("xoxb-bad-token")
    with pytest.raises(RuntimeError, match="Slack API error: invalid_auth"):
        client.test_connection()


@patch("httpx.get")
def test_slack_client_get_channels_cursor_pagination(mock_get):
    resp_p1 = Mock(status_code=200, json=lambda: SAMPLE_CHANNELS_PAGE_1)
    resp_p2 = Mock(status_code=200, json=lambda: SAMPLE_CHANNELS_PAGE_2)
    mock_get.side_effect = [resp_p1, resp_p2]

    client = SlackClient("xoxb-test-token")
    channels = client.get_channels(limit=1)

    assert len(channels) == 2
    assert channels[0]["name"] == "general"
    assert channels[1]["name"] == "backend"
    assert mock_get.call_count == 2
    # Verify cursor was passed to 2nd request
    assert mock_get.call_args_list[1][1]["params"]["cursor"] == "cursor_ch_p2"


@patch("httpx.get")
def test_slack_client_get_users_cursor_pagination(mock_get):
    resp_p1 = Mock(status_code=200, json=lambda: SAMPLE_USERS_PAGE_1)
    resp_p2 = Mock(status_code=200, json=lambda: SAMPLE_USERS_PAGE_2)
    mock_get.side_effect = [resp_p1, resp_p2]

    client = SlackClient("xoxb-test-token")
    users = client.get_users(limit=1)

    assert len(users) == 2
    assert users[0]["id"] == "U101"
    assert users[1]["id"] == "U102"
    assert mock_get.call_count == 2
    assert mock_get.call_args_list[1][1]["params"]["cursor"] == "cursor_users_p2"


@patch("httpx.get")
def test_slack_client_get_messages_cursor_pagination(mock_get):
    resp_p1 = Mock(status_code=200, json=lambda: SAMPLE_MESSAGES_PAGE_1)
    resp_p2 = Mock(status_code=200, json=lambda: SAMPLE_MESSAGES_PAGE_2)
    mock_get.side_effect = [resp_p1, resp_p2]

    client = SlackClient("xoxb-test-token")
    messages = client.get_messages(channel_id="C001", limit=1)

    assert len(messages) == 2
    assert messages[0]["ts"] == "1710000000.000100"
    assert messages[1]["ts"] == "1710000050.000150"
    assert mock_get.call_count == 2
    assert mock_get.call_args_list[1][1]["params"]["cursor"] == "cursor_msg_p2"


@patch("httpx.get")
def test_slack_client_get_thread_replies(mock_get):
    resp = Mock(status_code=200, json=lambda: SAMPLE_THREAD_REPLIES)
    mock_get.return_value = resp

    client = SlackClient("xoxb-test-token")
    replies = client.get_thread_replies(channel_id="C001", thread_ts="1710000000.000100")

    assert len(replies) == 2
    assert mock_get.call_args[1]["params"]["ts"] == "1710000000.000100"


# ---------------------------------------------------------------------------
# Tests: SlackConnector Normalization & Deduplication
# ---------------------------------------------------------------------------

def test_slack_connector_transform_data_normalization_and_deduplication():
    connector = SlackConnector(
        token="xoxb-test-token",
        channel_id="C001",
    )

    all_users = SAMPLE_USERS_PAGE_1["members"] + SAMPLE_USERS_PAGE_2["members"]
    all_channels = SAMPLE_CHANNELS_PAGE_1["channels"]
    all_messages = SAMPLE_MESSAGES_PAGE_1["messages"] + SAMPLE_MESSAGES_PAGE_2["messages"]

    raw_data = {
        "auth": SAMPLE_AUTH_RESPONSE,
        "users": all_users,
        "channels": all_channels,
        "messages": {"C001": all_messages},
        "thread_replies": {"C001:1710000000.000100": SAMPLE_THREAD_REPLIES["messages"]},
    }

    records = connector.transform_data(raw_data)

    # Expected count breakdown:
    # 2 users -> 2 User records
    # 1 channel -> 1 Channel record
    # 2 messages from channel history (ts: 1710000000.000100, 1710000050.000150)
    # Thread replies has 2 items:
    #   item 0: root message (ts: 1710000000.000100) -> MUST BE DEDUPLICATED!
    #   item 1: reply message (ts: 1710000080.000200) -> 1 new record
    # Total expected records = 2 + 1 + 2 + 1 = 6 records
    assert len(records) == 6

    # 1. Verify User Record
    user_rec = next(r for r in records if r.entity_type == "User" and r.external_id == "user-U101")
    assert user_rec.source == "slack"
    assert user_rec.title == "Alice"
    assert user_rec.author == "Alice"
    assert user_rec.metadata["email"] == "alice@aekos.com"
    assert user_rec.metadata["title"] == "Core Engineer"

    # 2. Verify Channel Record
    channel_rec = next(r for r in records if r.entity_type == "Channel")
    assert channel_rec.source == "slack"
    assert channel_rec.external_id == "channel-C001"
    assert channel_rec.title == "#general"
    assert "Company-wide announcements" in channel_rec.content
    assert channel_rec.project == "#general"
    assert channel_rec.metadata["num_members"] == 25

    # 3. Verify Root Message Record
    root_msg = next(r for r in records if r.external_id == "C001-1710000000.000100")
    assert root_msg.source == "slack"
    assert root_msg.entity_type == "Message"
    assert root_msg.title == "Starting work on Slack connector prototype."
    assert root_msg.content == "Starting work on Slack connector prototype."
    # Author should be resolved from user map
    assert root_msg.author == "Alice"
    assert root_msg.project == "#general"
    assert root_msg.timestamp is not None
    assert root_msg.metadata["channel_id"] == "C001"
    assert root_msg.metadata["reply_count"] == 1
    assert root_msg.metadata["is_thread_reply"] is False

    # 4. Verify Thread Reply Record
    reply_msg = next(r for r in records if r.external_id == "C001-1710000080.000200")
    assert reply_msg.source == "slack"
    assert reply_msg.entity_type == "Message"
    assert reply_msg.author == "Bob"
    assert reply_msg.content == "Looks good! Ping me when PR is ready."
    assert reply_msg.project == "#general"
    assert reply_msg.metadata["is_thread_reply"] is True
    assert reply_msg.metadata["thread_ts"] == "1710000000.000100"

    # 5. Verify Deduplication: Exactly ONE record exists for the root message id
    matching_root_records = [r for r in records if r.external_id == "C001-1710000000.000100"]
    assert len(matching_root_records) == 1


@patch.object(SlackClient, "test_connection", return_value=SAMPLE_AUTH_RESPONSE)
@patch.object(SlackClient, "get_users", return_value=SAMPLE_USERS_PAGE_1["members"])
@patch.object(SlackClient, "get_channels", return_value=SAMPLE_CHANNELS_PAGE_1["channels"])
@patch.object(SlackClient, "get_messages", return_value=SAMPLE_MESSAGES_PAGE_1["messages"])
@patch.object(SlackClient, "get_thread_replies", return_value=SAMPLE_THREAD_REPLIES["messages"])
def test_slack_connector_sync_e2e(mock_replies, mock_msgs, mock_channels, mock_users, mock_auth):
    connector = SlackConnector(token="xoxb-test-token", channel_id="C001")
    results = connector.sync()

    assert isinstance(results, list)
    assert len(results) > 0

    for item in results:
        assert isinstance(item, dict)
        assert item["source"] == "slack"
        assert "entity_type" in item
        assert "external_id" in item
        assert "title" in item
        assert "content" in item
        assert "author" in item
        assert "project" in item
        assert "timestamp" in item
        assert "metadata" in item
