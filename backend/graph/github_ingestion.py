from .neo4j_service import Neo4jService


class GitHubNeo4jIngestion:

    def __init__(self, neo4j: Neo4jService):
        self.neo4j = neo4j

    def ingest(self, data: dict) -> None:

        repository = data["repository"]

        # Repository
        repository_id = repository["full_name"]

        self.neo4j.create_repository(
            repository_id=repository_id,
            name=repository["name"],
            url=f"https://github.com/{repository_id}",
        )

        # Owner
        owner = repository["owner"]

        self.neo4j.create_user(
            user_id=owner,
            name=owner,
        )

        # Commits
        for commit in data.get("commits", []):

            author = commit.get("author")

            if not author:
                continue

            self.neo4j.create_user(
                user_id=author,
                name=author,
            )

            self.neo4j.create_commit(
                commit_id=commit["sha"],
                message=commit["message"],
                author_id=author,
                repository_id=repository_id,
            )

        # Issues
        for issue in data.get("issues", []):

            issue_id = f"{repository_id}#{issue['number']}"

            self.neo4j.create_issue(
                issue_id=issue_id,
                title=issue["title"],
                repository_id=repository_id,
                state=issue["state"],
            )