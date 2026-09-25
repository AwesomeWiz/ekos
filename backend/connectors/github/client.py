import httpx


class GitHubClient:
    BASE_URL = "https://api.github.com"

    def __init__(self, token: str):
        self.token = token

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        }

    def test_connection(self):
        response = httpx.get(
            f"{self.BASE_URL}/user",
            headers=self._get_headers(),
            timeout=10.0,
        )

        response.raise_for_status()
        return response.json()

    def get_repository(self, owner: str, repo: str):
        response = httpx.get(
            f"{self.BASE_URL}/repos/{owner}/{repo}",
            headers=self._get_headers(),
            timeout=10.0,
        )

        response.raise_for_status()
        return response.json()

    def get_branches(self, owner: str, repo: str):
        response = httpx.get(
            f"{self.BASE_URL}/repos/{owner}/{repo}/branches",
            headers=self._get_headers(),
            timeout=10.0,
        )

        response.raise_for_status()
        return response.json()

    def get_commits(self, owner: str, repo: str):
        response = httpx.get(
            f"{self.BASE_URL}/repos/{owner}/{repo}/commits",
            headers=self._get_headers(),
            timeout=10.0,
        )

        response.raise_for_status()
        return response.json()

    def get_issues(self, owner: str, repo: str):
        response = httpx.get(
            f"{self.BASE_URL}/repos/{owner}/{repo}/issues",
            headers=self._get_headers(),
            params={"state": "all"},
            timeout=10.0,
        )

        response.raise_for_status()
        return response.json()

    def get_readme(self, owner: str, repo: str):
        response = httpx.get(
            f"{self.BASE_URL}/repos/{owner}/{repo}/readme",
            headers=self._get_headers(),
            timeout=10.0,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()