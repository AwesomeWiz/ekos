from .schemas import (
    EntityRecord,
    RelationshipRecord,
    DocumentRecord,
)


def normalize_github_data(data: dict):
    entities = []
    relationships = []
    documents = []

    repository = data["repository"]
    repository_id = f"github:repository:{repository['full_name']}"

    # Repository entity
    entities.append(
        EntityRecord(
            id=repository_id,
            type="Repository",
            properties={
                "name": repository["name"],
                "full_name": repository["full_name"],
                "owner": repository["owner"],
                "default_branch": repository["default_branch"],
                "source": "github",
            },
        )
    )

    # Commit entities and relationships
    for commit in data.get("commits", []):
        commit_id = f"github:commit:{commit['sha']}"

        entities.append(
            EntityRecord(
                id=commit_id,
                type="Commit",
                properties={
                    "sha": commit["sha"],
                    "message": commit["message"],
                    "url": commit.get("url"),
                    "source": "github",
                },
            )
        )

        author = commit.get("author")

        if author:
            author_id = f"github:user:{author}"

            entities.append(
                EntityRecord(
                    id=author_id,
                    type="User",
                    properties={
                        "login": author,
                        "source": "github",
                    },
                )
            )

            relationships.append(
                RelationshipRecord(
                    source_id=author_id,
                    source_type="User",
                    relationship="COMMITTED",
                    target_id=commit_id,
                    target_type="Commit",
                )
            )

        relationships.append(
            RelationshipRecord(
                source_id=commit_id,
                source_type="Commit",
                relationship="BELONGS_TO",
                target_id=repository_id,
                target_type="Repository",
            )
        )

    # Issue entities and relationships
    for issue in data.get("issues", []):
        issue_id = (
            f"github:issue:"
            f"{repository['full_name']}#{issue['number']}"
        )

        entities.append(
            EntityRecord(
                id=issue_id,
                type="Issue",
                properties={
                    "number": issue["number"],
                    "title": issue["title"],
                    "state": issue["state"],
                    "url": issue.get("url"),
                    "source": "github",
                },
            )
        )

        relationships.append(
            RelationshipRecord(
                source_id=issue_id,
                source_type="Issue",
                relationship="BELONGS_TO",
                target_id=repository_id,
                target_type="Repository",
            )
        )

    # README document
    readme = data.get("readme")

    if readme and readme.get("content"):
        documents.append(
            DocumentRecord(
                id=f"github:readme:{repository['full_name']}",
                text=readme["content"],
                metadata={
                    "source": "github",
                    "connector": "github",
                    "repository": repository["full_name"],
                    "document_type": "README",
                },
            )
        )

    for document in data.get("docs", []):
        if not document.get("content"):
            continue

        documents.append(
            DocumentRecord(
                id=f"github:document:{repository['full_name']}:{document['path']}",
                text=document["content"],
                metadata={
                    "source": "github",
                    "connector": "github",
                    "repository": repository["full_name"],
                    "document_type": "markdown",
                    "document_name": document["name"],
                    "path": document["path"],
                },
            )
        )

    return {
        "entities": entities,
        "relationships": relationships,
        "documents": documents,
    }


def normalize_connector_data(data: dict, connector: str):
    if connector == "github":
        return normalize_github_data(data)

    raise ValueError(
        f"Unsupported connector: {connector}"
    )