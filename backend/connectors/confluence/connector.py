from typing import Any, Dict, List, Optional
from connectors.base import BaseConnector
from connectors.models import NormalizedRecord
from .client import ConfluenceClient
from .html_converter import html_to_plain_text


class ConfluenceConnector(BaseConnector):
    """Confluence connector implementing the BaseConnector interface."""

    def __init__(
        self,
        base_url: str,
        token: str,
        email: Optional[str] = None,
        space_key: Optional[str] = None,
        page_size: int = 50,
        max_pages: Optional[int] = None,
        timeout: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.email = email
        self.space_key = space_key
        self.page_size = page_size
        self.max_pages = max_pages
        self.client = ConfluenceClient(
            base_url=self.base_url,
            token=self.token,
            email=self.email,
            timeout=timeout,
        )

    def authenticate(self) -> Dict[str, Any]:
        """Authenticate with Confluence by verifying credentials."""
        return self.client.test_connection()

    def test_connection(self) -> Dict[str, Any]:
        """Test API connection to Confluence."""
        return self.client.test_connection()

    def fetch_data(self) -> Dict[str, Any]:
        """Fetch raw spaces and pages from Confluence with pagination."""
        user_info = self.client.test_connection()
        spaces = self.client.get_spaces(limit=self.page_size)
        pages = self.client.get_pages(
            space_key=self.space_key,
            limit=self.page_size,
            max_results=self.max_pages,
        )

        return {
            "user": user_info,
            "spaces": spaces,
            "pages": pages,
        }

    def transform_data(
        self, data: Optional[Dict[str, Any]] = None
    ) -> List[NormalizedRecord]:
        """Transform raw Confluence data into canonical NormalizedRecord instances.

        - Spaces: Lightweight structural records.
        - Pages: Primary searchable knowledge content with clean plain-text bodies.
        """
        if data is None:
            data = self.fetch_data()

        records: List[NormalizedRecord] = []

        # 1. Transform Spaces into lightweight structural records
        spaces = data.get("spaces", [])
        for space in spaces:
            space_k = space.get("key")
            space_name = space.get("name") or space_k or "Unknown Space"
            description_obj = space.get("description", {}).get("plain", {})
            description = (
                description_obj.get("value")
                or f"Confluence Space: {space_name}"
            )
            webui = space.get("_links", {}).get("webui", "")
            space_url = f"{self.base_url}{webui}" if webui else None

            space_record = NormalizedRecord(
                source="confluence",
                entity_type="Space",
                external_id=f"space-{space_k}",
                title=space_name,
                content=description,
                author=None,
                project=space_k,
                timestamp=None,
                metadata={
                    "space_key": space_k,
                    "space_name": space_name,
                    "space_type": space.get("type", "global"),
                    "url": space_url,
                },
            )
            records.append(space_record)

        # 2. Transform Pages into primary knowledge records
        pages = data.get("pages", [])
        for page in pages:
            page_id = str(page.get("id", "UNKNOWN"))
            title = page.get("title") or f"Page {page_id}"

            # Space reference
            space_info = page.get("space") or {}
            page_space_key = space_info.get("key") or self.space_key
            page_space_name = space_info.get("name")

            # Extract body: safe against missing body/empty body
            storage_body = (
                page.get("body", {})
                .get("storage", {})
                .get("value")
            )
            content = html_to_plain_text(storage_body)

            # Author determination: version modifier or creator
            version_info = page.get("version") or {}
            by_user = version_info.get("by") or {}
            history_info = page.get("history") or {}
            created_by = history_info.get("createdBy") or {}

            author = (
                by_user.get("displayName")
                or by_user.get("publicName")
                or by_user.get("username")
                or created_by.get("displayName")
                or created_by.get("publicName")
            )

            # Timestamps
            modified_at = version_info.get("when")
            created_at = history_info.get("createdDate")
            timestamp = modified_at or created_at

            # Labels
            labels_data = page.get("metadata", {}).get("labels", {}).get("results", [])
            labels = [
                lbl.get("name")
                for lbl in labels_data
                if isinstance(lbl, dict) and lbl.get("name")
            ]

            # URL
            webui = page.get("_links", {}).get("webui", "")
            page_url = f"{self.base_url}{webui}" if webui else None

            # Confluence-specific metadata
            metadata: Dict[str, Any] = {
                "space_key": page_space_key,
                "space_name": page_space_name,
                "version_number": version_info.get("number", 1),
                "labels": labels,
                "created_at": created_at,
                "modified_at": modified_at,
                "url": page_url,
            }

            page_record = NormalizedRecord(
                source="confluence",
                entity_type="Page",
                external_id=page_id,
                title=title,
                content=content,
                author=author,
                project=page_space_key,
                timestamp=timestamp,
                metadata=metadata,
            )
            records.append(page_record)

        return records

    def sync(self) -> List[Dict[str, Any]]:
        """Fetch all data and return a list of serialized canonical NormalizedRecord dicts."""
        raw_data = self.fetch_data()
        records = self.transform_data(raw_data)
        return [record.to_dict() for record in records]

    def disconnect(self) -> None:
        """Release client resources."""
        pass
