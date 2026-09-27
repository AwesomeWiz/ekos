import os

from connectors.github.connector import GitHubConnector
from graph.neo4j_service import Neo4jService
from knowledge.ingestion import KnowledgeIngestionService
from knowledge.normalizers import normalize_connector_data


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

    print(f"Repository: {data['repository']['full_name']}")
    print(f"Commits: {len(data.get('commits', []))}")
    print(f"Issues: {len(data.get('issues', []))}")

    records = normalize_connector_data(
        data,
        connector="github",
    )

    print(
        f"Normalized: {len(records['entities'])} entities, "
        f"{len(records['relationships'])} relationships, "
        f"{len(records['documents'])} documents"
    )

    neo4j = Neo4jService()
    ingestion = KnowledgeIngestionService(neo4j=neo4j)

    print("Ingesting knowledge...")
    ingestion.ingest(records)

    print("Knowledge ingestion completed.")

    ingestion.close()


if __name__ == "__main__":
    main()