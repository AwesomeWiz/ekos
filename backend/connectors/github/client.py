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