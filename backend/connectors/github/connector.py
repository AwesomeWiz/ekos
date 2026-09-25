from .client import GitHubClient
from connectors.base import BaseConnector


class GitHubConnector(BaseConnector):

    def __init__(self, token: str, owner: str, repo: str):
        self.client = GitHubClient(token)
        self.owner = owner
        self.repo = repo

    def authenticate(self):
        return self.client.test_connection()

    def test_connection(self):
        return self.client.test_connection()

    def fetch_data(self):
        return {
            "repository": self.client.get_repository(
                self.owner,
                self.repo,
            ),
            "branches": self.client.get_branches(
                self.owner,
                self.repo,
            ),
            "commits": self.client.get_commits(
                self.owner,
                self.repo,
            ),
            "issues": self.client.get_issues(
                self.owner,
                self.repo,
            ),
            "readme": self.client.get_readme(
                self.owner,
                self.repo,
            ),
        }

    def transform_data(self, data):
        return {
        "source": "github",
        "repository": {
            "full_name": data["repository"]["full_name"],
            "name": data["repository"]["name"],
            "owner": data["repository"]["owner"]["login"],
            "default_branch": data["repository"]["default_branch"],
        },
        "branches": [
            {
                "name": branch["name"],
                "protected": branch.get("protected", False),
            }
            for branch in data.get("branches", [])
        ],
        "commits": [
            {
                "sha": commit["sha"],
                "message": commit["commit"]["message"],
                "author": (
                    commit["author"]["login"]
                    if commit.get("author")
                    else None
                ),
                "url": commit.get("html_url"),
            }
            for commit in data.get("commits", [])
        ],
        "issues": [
            {
                "number": issue["number"],
                "title": issue["title"],
                "state": issue["state"],
                "url": issue.get("html_url"),
            }
            for issue in data.get("issues", [])
        ],
        "readme": (
            {
                "name": data["readme"]["name"],
                "path": data["readme"]["path"],
                "encoding": data["readme"]["encoding"],
                "content": data["readme"].get("content"),
            }
            if data.get("readme")
            else None
        ),
    }

    def sync(self):
        data = self.fetch_data()
        return self.transform_data(data)

    def disconnect(self):
        pass