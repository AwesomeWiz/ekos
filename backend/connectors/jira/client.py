import base64
from typing import Any, Dict, List, Optional
import httpx


class JiraClient:
    """REST API client for Atlassian Jira Cloud and Jira Server / Data Center."""

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
        """Verify authentication by fetching the current user profile."""
        url = f"{self.base_url}/rest/api/2/myself"
        response = httpx.get(url, headers=self._get_headers(), timeout=self.timeout)
        if response.status_code == 404:
            # Fallback to Jira REST API v3
            url = f"{self.base_url}/rest/api/3/myself"
            response = httpx.get(url, headers=self._get_headers(), timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_projects(self) -> List[Dict[str, Any]]:
        """Retrieve accessible projects."""
        url = f"{self.base_url}/rest/api/2/project"
        response = httpx.get(url, headers=self._get_headers(), timeout=self.timeout)
        if response.status_code == 404:
            url = f"{self.base_url}/rest/api/3/project"
            response = httpx.get(url, headers=self._get_headers(), timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_issues(
        self,
        project_key: Optional[str] = None,
        jql: Optional[str] = None,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search and retrieve issues with standard fields and embedded comments."""
        if jql is None:
            if project_key:
                jql = f'project = "{project_key}" ORDER BY created DESC'
            else:
                jql = "ORDER BY created DESC"

        fields = (
            "summary,description,status,priority,assignee,reporter,"
            "creator,created,updated,comment,labels,project"
        )
        params = {
            "jql": jql,
            "maxResults": max_results,
            "fields": fields,
        }

        url = f"{self.base_url}/rest/api/3/search/jql"
        response = httpx.get(
            url,
            headers=self._get_headers(),
            params=params,
            timeout=self.timeout,
        )
        if response.status_code in {404, 410}:
            # Fallback to /rest/api/2/search/jql or legacy /rest/api/2/search (for Server/Data Center)
            url = f"{self.base_url}/rest/api/2/search/jql"
            response = httpx.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=self.timeout,
            )
            if response.status_code in {404, 410}:
                url = f"{self.base_url}/rest/api/2/search"
                response = httpx.get(
                    url,
                    headers=self._get_headers(),
                    params=params,
                    timeout=self.timeout,
                )
        response.raise_for_status()
        return response.json().get("issues", [])

    def get_issue_comments(self, issue_key: str) -> List[Dict[str, Any]]:
        """Retrieve comments for a specific issue if not included in the issue payload."""
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}/comment"
        response = httpx.get(url, headers=self._get_headers(), timeout=self.timeout)
        if response.status_code == 404:
            url = f"{self.base_url}/rest/api/3/issue/{issue_key}/comment"
            response = httpx.get(url, headers=self._get_headers(), timeout=self.timeout)
        response.raise_for_status()
        return response.json().get("comments", [])
