from connectors.base import BaseConnector
from connectors.github.client import GitHubClient


class GitHubConnector(BaseConnector):

    def __init__(self, token: str):
        self.client = GitHubClient(token)

    def authenticate(self):
        return self.test_connection()

    def test_connection(self):
        return self.client.test_connection()

    def fetch_data(self):
        pass

    def transform_data(self):
        pass

    def sync(self):
        pass

    def disconnect(self):
        pass