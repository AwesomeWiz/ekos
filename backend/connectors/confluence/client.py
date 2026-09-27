import base64
from typing import Any, Dict, List, Optional
import httpx


class ConfluenceClient:
    """REST API client for Confluence Cloud and Confluence Server / Data Center."""

    def __init__(
        self,
        base_url: str,
        token: str,
        email: Optional[str] = None,
        timeout: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.email = email
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.email:
            credentials = f"{self.email}:{self.token}"
            encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
            headers["Authorization"] = f"Basic {encoded}"
        else:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def test_connection(self) -> Dict[str, Any]:
        """Verify authentication and connectivity."""
        url = f"{self.base_url}/rest/api/user/current"
        response = httpx.get(url, headers=self._get_headers(), timeout=self.timeout)
        if response.status_code == 404:
            # Fallback if current user endpoint is restricted/different on server
            url = f"{self.base_url}/rest/api/space?limit=1"
            response = httpx.get(url, headers=self._get_headers(), timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_spaces(
        self,
        limit: int = 50,
        max_results: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve Confluence spaces with pagination support."""
        all_spaces: List[Dict[str, Any]] = []
        start = 0

        while True:
            current_limit = limit
            if max_results is not None:
                remaining = max_results - len(all_spaces)
                if remaining <= 0:
                    break
                current_limit = min(limit, remaining)

            url = f"{self.base_url}/rest/api/space"
            params = {"start": start, "limit": current_limit, "status": "current"}
            response = httpx.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            batch = data.get("results", [])
            all_spaces.extend(batch)

            # Pagination stop conditions
            if not batch or len(batch) < current_limit:
                break
            if "_links" in data and "next" not in data["_links"]:
                break
            start += len(batch)

        return all_spaces

    def get_pages(
        self,
        space_key: Optional[str] = None,
        limit: int = 50,
        max_results: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve Confluence pages with expanded body, metadata, and pagination support."""
        all_pages: List[Dict[str, Any]] = []
        start = 0

        expand = "body.storage,version,metadata.labels,history,space"

        while True:
            current_limit = limit
            if max_results is not None:
                remaining = max_results - len(all_pages)
                if remaining <= 0:
                    break
                current_limit = min(limit, remaining)

            url = f"{self.base_url}/rest/api/content"
            params: Dict[str, Any] = {
                "type": "page",
                "expand": expand,
                "start": start,
                "limit": current_limit,
            }
            if space_key:
                params["spaceKey"] = space_key

            response = httpx.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            batch = data.get("results", [])
            all_pages.extend(batch)

            if not batch or len(batch) < current_limit:
                break
            if "_links" in data and "next" not in data["_links"]:
                break
            start += len(batch)

        return all_pages

    def get_page_by_id(self, page_id: str) -> Dict[str, Any]:
        """Fetch a single page with all necessary expansions."""
        url = f"{self.base_url}/rest/api/content/{page_id}"
        expand = "body.storage,version,metadata.labels,history,space"
        response = httpx.get(
            url,
            headers=self._get_headers(),
            params={"expand": expand},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
