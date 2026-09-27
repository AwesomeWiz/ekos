"""Convert actual normalized GitHub records into deterministic Chroma documents."""

import base64
from dataclasses import dataclass

from services.knowledge_runtime import get_chroma_service, get_embedding_service


@dataclass
class KnowledgeDocument:
    id: str
    text: str
    metadata: dict


def chunk_text(text: str, size: int = 2000, overlap: int = 200) -> list[str]:
    """About 500 tokens per chunk, with a modest overlap and no tokenizer dependency."""
    if not 0 <= overlap < size:
        raise ValueError("Chunk overlap must be smaller than chunk size")
    text = text.strip()
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + size * 3 // 4, end)
            if boundary != -1:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = end - overlap
    return chunks


def github_documents(data: dict, organization_id: str, connector_id: str, connector_name: str = "GitHub") -> list[KnowledgeDocument]:
    repository = data["repository"]
    repo = repository["full_name"]
    repo_url = repository.get("url") or f"https://github.com/{repo}"
    # Scope IDs as well as metadata: two organizations may index the same repository.
    prefix = f"github:{organization_id}:{connector_id}:{repo}"
    common = {"source": "github", "connector": connector_name, "connector_id": connector_id,
              "organization_id": organization_id, "repository": repo}
    documents = []

    def add(entity_type: str, entity_id: str, title: str, text: str, url: str):
        chunks = chunk_text(text)
        base_id = f"{prefix}:{entity_type}" + (f":{entity_id}" if entity_type not in {"repository", "readme"} else "")
        for index, chunk in enumerate(chunks):
            document_id = f"{base_id}:chunk:{index}" if len(chunks) > 1 else base_id
            metadata = {**common, "entity_type": entity_type, "entity_id": entity_id, "title": title,
                        "url": url, "chunk_index": index}
            documents.append(KnowledgeDocument(document_id, chunk, metadata))

    branches = ", ".join(branch["name"] for branch in data.get("branches", []))
    repository_text = f"Repository: {repo}\nDefault branch: {repository['default_branch']}"
    if repository.get("description"):
        repository_text += f"\nDescription: {repository['description']}"
    if branches:
        repository_text += f"\nRepository branches: {branches}"
    add("repository", repo, repo, repository_text, repo_url)

    readme = data.get("readme")
    if readme and readme.get("content"):
        content = readme["content"]
        if readme.get("encoding") == "base64":
            content = base64.b64decode(content).decode("utf-8", errors="replace")
        elif readme.get("encoding") not in {"utf-8", "utf8", "text"}:
            raise ValueError("Unsupported README encoding")
        add("readme", readme["path"], readme["name"], content,
            f"{repo_url}/blob/{repository['default_branch']}/{readme['path']}")

    for commit in data.get("commits", []):
        message = (commit.get("message") or "").strip()
        if message:
            add("commit", commit["sha"], message.splitlines()[0][:200], message,
                commit.get("url") or f"{repo_url}/commit/{commit['sha']}")

    for issue in data.get("issues", []):
        kind = "pull_request" if issue.get("is_pull_request") else "issue"
        text = f"{issue['title']}\n{issue.get('body') or ''}".strip()
        add(kind, str(issue["number"]), f"#{issue['number']} {issue['title']}", text,
            issue.get("url") or f"{repo_url}/{'pull' if kind == 'pull_request' else 'issues'}/{issue['number']}")
    return documents


def index_github_data(data: dict, organization_id: str, connector_id: str, connector_name: str = "GitHub", *, chroma=None, embeddings=None) -> dict:
    documents = github_documents(data, organization_id, connector_id, connector_name)
    chroma = chroma if chroma is not None else get_chroma_service()
    embeddings = embeddings if embeddings is not None else get_embedding_service()
    # Small batches keep long repositories from holding all embeddings in memory.
    for start in range(0, len(documents), 32):
        batch = documents[start:start + 32]
        vectors = embeddings.embed_many([document.text for document in batch])
        if len(vectors) != len(batch):
            raise ValueError("Embedding count did not match document count")
        for document, vector in zip(batch, vectors):
            chroma.add_document(document.id, document.text, vector, document.metadata)

    entities = {}
    for document in documents:
        key = (document.metadata["entity_type"], document.metadata["entity_id"])
        entities.setdefault(key, []).append(document.id)
    for (entity_type, entity_id), ids in entities.items():
        filters = [
            {"organization_id": organization_id}, {"connector_id": connector_id},
            {"repository": data["repository"]["full_name"]}, {"entity_type": entity_type},
        ]
        # There is one current README per repository even if its path has changed.
        if entity_type not in {"readme", "repository"}:
            filters.append({"entity_id": entity_id})
        chroma.delete_stale_chunks(ids, {"$and": filters})
    return {"status": "indexed", "documents_indexed": len(documents),
            "chroma_total": chroma.count({"organization_id": organization_id}), "error": None}
