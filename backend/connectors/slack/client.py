from typing import Any, Dict, List, Optional
import httpx


class SlackClient:
    """Lightweight REST API client for the Slack Web API."""

    def __init__(
        self,
        token: str,
        base_url: str = "https://slack.com/api",
        timeout: float = 10.0,
    ):
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        }

    def _check_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Check HTTP status and Slack application-level 'ok' flag."""
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            error_code = data.get("error", "unknown_error")
            raise RuntimeError(f"Slack API error: {error_code}")
        return data

    def test_connection(self) -> Dict[str, Any]:
        """Verify authentication and token validity using auth.test."""
        url = f"{self.base_url}/auth.test"
        response = httpx.post(url, headers=self._get_headers(), timeout=self.timeout)
        return self._check_response(response)

    def get_channels(
        self,
        types: str = "public_channel,private_channel",
        limit: int = 100,
        max_results: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve channels with cursor-based pagination."""
        all_channels: List[Dict[str, Any]] = []
        cursor: Optional[str] = None

        while True:
            current_limit = limit
            if max_results is not None:
                remaining = max_results - len(all_channels)
                if remaining <= 0:
                    break
                current_limit = min(limit, remaining)

            params: Dict[str, Any] = {
                "types": types,
                "limit": current_limit,
            }
            if cursor:
                params["cursor"] = cursor

            url = f"{self.base_url}/conversations.list"
            response = httpx.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=self.timeout,
            )
            data = self._check_response(response)
            channels = data.get("channels", [])
            all_channels.extend(channels)

            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor or not channels:
                break

        return all_channels

    def get_users(
        self,
        limit: int = 100,
        max_results: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve workspace users with cursor-based pagination."""
        all_users: List[Dict[str, Any]] = []
        cursor: Optional[str] = None

        while True:
            current_limit = limit
            if max_results is not None:
                remaining = max_results - len(all_users)
                if remaining <= 0:
                    break
                current_limit = min(limit, remaining)

            params: Dict[str, Any] = {"limit": current_limit}
            if cursor:
                params["cursor"] = cursor

            url = f"{self.base_url}/users.list"
            response = httpx.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=self.timeout,
            )
            data = self._check_response(response)
            members = data.get("members", [])
            all_users.extend(members)

            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor or not members:
                break

        return all_users

    def get_messages(
        self,
        channel_id: str,
        limit: int = 100,
        max_results: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve message history for a channel with cursor-based pagination."""
        all_messages: List[Dict[str, Any]] = []
        cursor: Optional[str] = None

        while True:
            current_limit = limit
            if max_results is not None:
                remaining = max_results - len(all_messages)
                if remaining <= 0:
                    break
                current_limit = min(limit, remaining)

            params: Dict[str, Any] = {
                "channel": channel_id,
                "limit": current_limit,
            }
            if cursor:
                params["cursor"] = cursor

            url = f"{self.base_url}/conversations.history"
            response = httpx.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=self.timeout,
            )
            data = self._check_response(response)
            messages = data.get("messages", [])
            all_messages.extend(messages)

            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor or not messages:
                break

        return all_messages

    def get_thread_replies(
        self,
        channel_id: str,
        thread_ts: str,
        limit: int = 100,
        max_results: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve replies in a message thread with cursor-based pagination."""
        all_replies: List[Dict[str, Any]] = []
        cursor: Optional[str] = None

        while True:
            current_limit = limit
            if max_results is not None:
                remaining = max_results - len(all_replies)
                if remaining <= 0:
                    break
                current_limit = min(limit, remaining)

            params: Dict[str, Any] = {
                "channel": channel_id,
                "ts": thread_ts,
                "limit": current_limit,
            }
            if cursor:
                params["cursor"] = cursor

            url = f"{self.base_url}/conversations.replies"
            response = httpx.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=self.timeout,
            )
            data = self._check_response(response)
            messages = data.get("messages", [])
            all_replies.extend(messages)

            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor or not messages:
                break

        return all_replies
