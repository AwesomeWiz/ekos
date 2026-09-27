import os

from connectors.github.connector import GitHubConnector
from graph.neo4j_service import Neo4jService
from graph.github_ingestion import GitHubNeo4jIngestion


def main():

    token = os.getenv("GITHUB_TOKEN")
    owner = os.getenv("GITHUB_OWNER")
    repo = os.getenv("GITHUB_REPO")

    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set")

    connector = GitHubConnector(
        token=token,
        owner=owner,
        repo=repo,
    )

    print("Fetching GitHub data...")

    data = connector.sync()

    print(
        f"Repository: {data['repository']['full_name']}"
    )

    print(
        f"Commits: {len(data.get('commits', []))}"
    )

    print(
        f"Issues: {len(data.get('issues', []))}"
    )

    neo4j = Neo4jService()

    print("Connected to Neo4j.")

    ingestion = GitHubNeo4jIngestion(neo4j)

    ingestion.ingest(data)

    print("GitHub data successfully stored in Neo4j.")

    neo4j.close()


if __name__ == "__main__":
    main()