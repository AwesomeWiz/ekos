from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from connectors.base import BaseConnector
from connectors.models import NormalizedRecord
from .client import SlackClient


def slack_ts_to_iso(ts_str: Optional[str]) -> Optional[str]:
    """Convert Slack's epoch microsecond timestamp string to ISO-8601 UTC string."""
    if not ts_str:
        return None
    try:
        seconds = float(ts_str)
        return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError):
        return str(ts_str)


class SlackConnector(BaseConnector):
    """Slack prototype connector implementing the BaseConnector interface."""

    def __init__(
        self,
        token: str,
        base_url: str = "https://slack.com/api",
        channel_id: Optional[str] = None,
        page_limit: int = 100,
        max_messages_per_channel: Optional[int] = None,
        max_users: Optional[int] = None,
        timeout: float = 10.0,
    ):
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.channel_id = channel_id
        self.page_limit = page_limit
        self.max_messages_per_channel = max_messages_per_channel
        self.max_users = max_users
        self.client = SlackClient(
            token=self.token,
            base_url=self.base_url,
            timeout=timeout,
        )

    def authenticate(self) -> Dict[str, Any]:
        """Authenticate with Slack by verifying the bot token."""
        return self.client.test_connection()

    def test_connection(self) -> Dict[str, Any]:
        """Test API connection using auth.test."""
        return self.client.test_connection()

    def fetch_data(self) -> Dict[str, Any]:
        """Fetch raw channels, users, messages, and thread replies with pagination."""
        auth_info = self.client.test_connection()
        users = self.client.get_users(limit=self.page_limit, max_results=self.max_users)
        channels = self.client.get_channels(limit=self.page_limit)

        # Filter channels if a specific channel_id was requested
        if self.channel_id:
            channels = [c for c in channels if c.get("id") == self.channel_id]

        channel_messages: Dict[str, List[Dict[str, Any]]] = {}
        thread_replies: Dict[str, List[Dict[str, Any]]] = {}

        for ch in channels:
            ch_id = ch.get("id")
            if not ch_id:
                continue

            messages = self.client.get_messages(
                channel_id=ch_id,
                limit=self.page_limit,
                max_results=self.max_messages_per_channel,
            )
            channel_messages[ch_id] = messages

            # Fetch thread replies for messages that have replies
            for msg in messages:
                reply_count = msg.get("reply_count", 0)
                msg_ts = msg.get("ts")
                if reply_count > 0 and msg_ts:
                    replies = self.client.get_thread_replies(
                        channel_id=ch_id,
                        thread_ts=msg_ts,
                        limit=self.page_limit,
                    )
                    thread_replies[f"{ch_id}:{msg_ts}"] = replies

        return {
            "auth": auth_info,
            "users": users,
            "channels": channels,
            "messages": channel_messages,
            "thread_replies": thread_replies,
        }

    def transform_data(
        self, data: Optional[Dict[str, Any]] = None
    ) -> List[NormalizedRecord]:
        """Transform raw Slack data into canonical NormalizedRecord instances.

        - Channels: Lightweight structural records.
        - Users: Identity/member records.
        - Messages: Primary knowledge records.
        - Thread Replies: Message records deduplicated using (channel_id, ts).
        """
        if data is None:
            data = self.fetch_data()

        records: List[NormalizedRecord] = []

        # 1. Build User Lookup Map (user_id -> display_name / info)
        raw_users = data.get("users", [])
        user_map: Dict[str, Dict[str, Any]] = {}
        for user in raw_users:
            u_id = user.get("id")
            if u_id:
                user_map[u_id] = user

            profile = user.get("profile", {})
            display_name = (
                profile.get("display_name")
                or profile.get("real_name")
                or user.get("real_name")
                or user.get("name")
                or u_id
                or "Unknown User"
            )
            email = profile.get("email")
            title = profile.get("title")

            user_record = NormalizedRecord(
                source="slack",
                entity_type="User",
                external_id=f"user-{u_id}",
                title=display_name,
                content=f"Role: {title}" if title else f"Slack User: {display_name}",
                author=display_name,
                project=None,
                timestamp=None,
                metadata={
                    "user_id": u_id,
                    "email": email,
                    "real_name": profile.get("real_name") or user.get("real_name"),
                    "title": title,
                    "is_bot": user.get("is_bot", False),
                },
            )
            records.append(user_record)

        # 2. Transform Channels & Build Channel Name Map
        raw_channels = data.get("channels", [])
        channel_name_map: Dict[str, str] = {}
        for ch in raw_channels:
            ch_id = ch.get("id", "UNKNOWN")
            ch_name = ch.get("name", ch_id)
            channel_name_map[ch_id] = ch_name

            topic = ch.get("topic", {}).get("value", "")
            purpose = ch.get("purpose", {}).get("value", "")
            content = f"Topic: {topic}\nPurpose: {purpose}".strip()
            if not content:
                content = f"Slack Channel: #{ch_name}"

            channel_record = NormalizedRecord(
                source="slack",
                entity_type="Channel",
                external_id=f"channel-{ch_id}",
                title=f"#{ch_name}",
                content=content,
                author=None,
                project=f"#{ch_name}",
                timestamp=None,
                metadata={
                    "channel_id": ch_id,
                    "channel_name": ch_name,
                    "is_private": ch.get("is_private", False),
                    "num_members": ch.get("num_members", 0),
                },
            )
            records.append(channel_record)

        # Helper to resolve user name from user_id
        def resolve_user_name(u_id: Optional[str]) -> Optional[str]:
            if not u_id:
                return None
            u_info = user_map.get(u_id, {})
            profile = u_info.get("profile", {})
            return (
                profile.get("display_name")
                or profile.get("real_name")
                or u_info.get("real_name")
                or u_info.get("name")
                or u_id
            )

        # 3. Transform Messages and Deduplicate Root Messages & Thread Replies
        # Track seen (channel_id, ts) pairs to prevent duplicate root messages
        seen_messages: Set[Tuple[str, str]] = set()

        raw_messages_by_channel = data.get("messages", {})
        raw_thread_replies = data.get("thread_replies", {})

        for ch_id, messages in raw_messages_by_channel.items():
            ch_name = channel_name_map.get(ch_id, ch_id)

            for msg in messages:
                msg_ts = msg.get("ts")
                if not msg_ts:
                    continue

                msg_key = (ch_id, msg_ts)
                if msg_key in seen_messages:
                    continue
                seen_messages.add(msg_key)

                text = msg.get("text", "")
                user_id = msg.get("user")
                author_name = resolve_user_name(user_id)
                thread_ts = msg.get("thread_ts")
                reply_count = msg.get("reply_count", 0)
                is_reply = bool(thread_ts and thread_ts != msg_ts)

                # Generate clean preview title
                first_line = text.splitlines()[0][:60].strip() if text else ""
                title = first_line if first_line else f"Message in #{ch_name}"

                msg_record = NormalizedRecord(
                    source="slack",
                    entity_type="Message",
                    external_id=f"{ch_id}-{msg_ts}",
                    title=title,
                    content=text,
                    author=author_name,
                    project=f"#{ch_name}",
                    timestamp=slack_ts_to_iso(msg_ts),
                    metadata={
                        "channel_id": ch_id,
                        "channel_name": ch_name,
                        "user_id": user_id,
                        "ts": msg_ts,
                        "thread_ts": thread_ts,
                        "is_thread_reply": is_reply,
                        "reply_count": reply_count,
                    },
                )
                records.append(msg_record)

        # 4. Transform Thread Replies (deduplicating against seen_messages)
        for thread_key, replies in raw_thread_replies.items():
            ch_id = thread_key.split(":")[0]
            ch_name = channel_name_map.get(ch_id, ch_id)

            for reply in replies:
                reply_ts = reply.get("ts")
                if not reply_ts:
                    continue

                reply_key = (ch_id, reply_ts)
                if reply_key in seen_messages:
                    # Skip duplicate root message already emitted from channel history
                    continue
                seen_messages.add(reply_key)

                reply_text = reply.get("text", "")
                user_id = reply.get("user")
                author_name = resolve_user_name(user_id)
                parent_thread_ts = reply.get("thread_ts")

                first_line = reply_text.splitlines()[0][:60].strip() if reply_text else ""
                title = first_line if first_line else f"Reply in #{ch_name}"

                reply_record = NormalizedRecord(
                    source="slack",
                    entity_type="Message",
                    external_id=f"{ch_id}-{reply_ts}",
                    title=title,
                    content=reply_text,
                    author=author_name,
                    project=f"#{ch_name}",
                    timestamp=slack_ts_to_iso(reply_ts),
                    metadata={
                        "channel_id": ch_id,
                        "channel_name": ch_name,
                        "user_id": user_id,
                        "ts": reply_ts,
                        "thread_ts": parent_thread_ts,
                        "is_thread_reply": True,
                        "reply_count": 0,
                    },
                )
                records.append(reply_record)

        return records

    def sync(self) -> List[Dict[str, Any]]:
        """Fetch all data and return a list of serialized canonical NormalizedRecord dicts."""
        raw_data = self.fetch_data()
        records = self.transform_data(raw_data)
        return [record.to_dict() for record in records]

    def disconnect(self) -> None:
        """Release client resources."""
        pass
