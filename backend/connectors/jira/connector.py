from typing import Any, Dict, List, Optional
from connectors.base import BaseConnector
from connectors.models import NormalizedRecord
from .client import JiraClient


def extract_plain_text(content: Any) -> str:
    """Recursively convert ADF (Atlassian Document Format) or raw string to plain text."""
    if not content:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        items = [extract_plain_text(item) for item in content]
        return "\n".join(filter(None, items)).strip()
    if isinstance(content, dict):
        node_type = content.get("type")
        if node_type == "text":
            return content.get("text", "")
        if "content" in content:
            child_texts = [extract_plain_text(child) for child in content["content"]]
            if node_type in {"paragraph", "heading", "blockquote"}:
                return " ".join(filter(None, child_texts)).strip()
            elif node_type == "listItem":
                return "- " + " ".join(filter(None, child_texts)).strip()
            return "\n".join(filter(None, child_texts)).strip()
        if "text" in content:
            return str(content["text"]).strip()
    return ""


class JiraConnector(BaseConnector):
    """Jira connector implementing the BaseConnector interface."""

    def __init__(
        self,
        base_url: str,
        token: str,
        email: Optional[str] = None,
        project_key: Optional[str] = None,
        timeout: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.email = email
        self.project_key = project_key
        self.client = JiraClient(
            base_url=self.base_url,
            token=self.token,
            email=self.email,
            timeout=timeout,
        )

    def authenticate(self) -> Dict[str, Any]:
        """Authenticate with Jira by verifying user credentials."""
        return self.client.test_connection()

    def test_connection(self) -> Dict[str, Any]:
        """Test API connection to Jira."""
        return self.client.test_connection()

    def fetch_data(self) -> Dict[str, Any]:
        """Fetch raw Jira projects, issues, and comments."""
        user_info = self.client.test_connection()
        projects = self.client.get_projects()
        issues = self.client.get_issues(project_key=self.project_key)

        # For issues that might not embed full comments, ensure comments are available
        for issue in issues:
            fields = issue.get("fields", {})
            if "comment" not in fields or "comments" not in fields.get("comment", {}):
                issue_key = issue.get("key")
                if issue_key:
                    comments = self.client.get_issue_comments(issue_key)
                    if "comment" not in fields:
                        fields["comment"] = {}
                    fields["comment"]["comments"] = comments

        return {
            "user": user_info,
            "projects": projects,
            "issues": issues,
        }

    def transform_data(
        self, data: Optional[Dict[str, Any]] = None
    ) -> List[NormalizedRecord]:
        """Transform raw Jira payload into canonical NormalizedRecord instances.

        - Issues: reporter/creator as author, status/priority/assignee in metadata,
          comment_count in metadata.
        - Comments: separate NormalizedRecord entities.
        - Plain text extracted from rich text/ADF.
        """
        if data is None:
            data = self.fetch_data()

        records: List[NormalizedRecord] = []
        issues = data.get("issues", [])

        for issue in issues:
            issue_key = issue.get("key", "UNKNOWN")
            fields = issue.get("fields", {})

            # Author determination: reporter or creator (not assignee)
            reporter_info = fields.get("reporter") or {}
            reporter = (
                reporter_info.get("displayName")
                or reporter_info.get("name")
                or reporter_info.get("emailAddress")
            )
            creator_info = fields.get("creator") or {}
            creator = (
                creator_info.get("displayName")
                or creator_info.get("name")
                or creator_info.get("emailAddress")
            )
            author = reporter or creator

            # Assignee belongs in metadata
            assignee_info = fields.get("assignee") or {}
            assignee = (
                assignee_info.get("displayName")
                or assignee_info.get("name")
                or assignee_info.get("emailAddress")
            )

            # Project key
            project_info = fields.get("project") or {}
            project = project_info.get("key") or self.project_key

            # Status and Priority
            status_info = fields.get("status") or {}
            status_name = status_info.get("name")
            priority_info = fields.get("priority") or {}
            priority_name = priority_info.get("name")

            # Timestamps
            created_at = fields.get("created")
            updated_at = fields.get("updated")

            # Title and Content (converted from ADF/plain text)
            title = fields.get("summary") or issue_key
            content = extract_plain_text(fields.get("description"))

            # Process comments
            comments = fields.get("comment", {}).get("comments", [])
            comment_count = len(comments)

            # Metadata (Jira-specific properties)
            metadata: Dict[str, Any] = {
                "status": status_name,
                "priority": priority_name,
                "assignee": assignee,
                "reporter": reporter,
                "labels": fields.get("labels", []),
                "comment_count": comment_count,
                "created": created_at,
                "updated": updated_at,
                "url": f"{self.base_url}/browse/{issue_key}",
            }

            # Create Issue NormalizedRecord
            issue_record = NormalizedRecord(
                source="jira",
                entity_type="Issue",
                external_id=issue_key,
                title=title,
                content=content,
                author=author,
                project=project,
                timestamp=created_at or updated_at,
                metadata=metadata,
            )
            records.append(issue_record)

            # Create separate Comment NormalizedRecord entries (no full content duplication in Issue)
            for comment in comments:
                comment_id = str(comment.get("id", ""))
                comment_author_info = comment.get("author") or {}
                comment_author = (
                    comment_author_info.get("displayName")
                    or comment_author_info.get("name")
                    or comment_author_info.get("emailAddress")
                )
                comment_content = extract_plain_text(comment.get("body"))
                comment_created = comment.get("created")
                comment_updated = comment.get("updated")

                comment_external_id = (
                    f"{issue_key}-comment-{comment_id}" if comment_id else f"{issue_key}-comment"
                )
                comment_record = NormalizedRecord(
                    source="jira",
                    entity_type="Comment",
                    external_id=comment_external_id,
                    title=f"Comment on {issue_key}",
                    content=comment_content,
                    author=comment_author,
                    project=project,
                    timestamp=comment_created or comment_updated,
                    metadata={
                        "issue_key": issue_key,
                        "issue_title": title,
                        "created": comment_created,
                        "updated": comment_updated,
                        "url": (
                            f"{self.base_url}/browse/{issue_key}?focusedCommentId={comment_id}"
                            if comment_id
                            else None
                        ),
                    },
                )
                records.append(comment_record)

        return records

    def sync(self) -> List[Dict[str, Any]]:
        """Fetch all data and return a list of serialized canonical NormalizedRecord dicts."""
        raw_data = self.fetch_data()
        records = self.transform_data(raw_data)
        return [record.to_dict() for record in records]

    def disconnect(self) -> None:
        """Release any client connections or resources."""
        pass
