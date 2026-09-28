"""Optional read-only graph context using the existing Neo4j connection service."""

import logging
import re
from urllib.parse import urlparse

from sqlalchemy import func
from models.connector import Connector, ConnectorConfiguration

from config.settings import settings
from graph.neo4j_service import Neo4jService

logger = logging.getLogger(__name__)


def is_contributor_question(question: str) -> bool:
    return bool(re.search(r"\b(contribut\w*|committers?)\b", question, re.IGNORECASE)
                and not re.search(r"\b(jira|confluence|slack)\b", question, re.IGNORECASE))


def permitted_github_repositories(db, user, question: str) -> list[str]:
    """Resolve graph scope from this user's configured GitHub connectors, not vector ranking."""
    if not user.organization_id:
        return []
    configs = db.query(ConnectorConfiguration.api_url).join(Connector).filter(
        Connector.organization_id == user.organization_id, func.lower(Connector.type) == "github"
    ).all()
    repositories = set()
    for config in configs:
        url = urlparse(config.api_url or "")
        path = url.path.strip("/")
        if url.scheme in {"http", "https"} and url.hostname == "github.com" and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", path):
            repositories.add(path)
    named = [repo for repo in sorted(repositories)
             if re.search(rf"(?<![\w.-]){re.escape(repo.split('/')[-1])}(?![\w.-])", question, re.IGNORECASE)]
    # An explicitly named unknown repository must not fall back to another repository.
    if not named and re.search(r"\b(?:to|in|for)\s+(?:the\s+)?[\w.-]+\s+repository\b", question, re.IGNORECASE):
        return []
    return (named or sorted(repositories))[:3]


def retrieve_graph_context(question: str, search_results: list[dict], *, repository_ids: list[str] | None = None) -> list[dict]:
    # These repositories have already passed the search endpoint's tenant/connector filters.
    repositories = sorted({result["metadata"]["repository"] for result in search_results
                           if result["metadata"].get("source") == "github"
                           and isinstance(result["metadata"].get("repository"), str)
                           and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", result["metadata"]["repository"])})
    if repository_ids is not None:
        repositories = repository_ids
    entity_ids = list(dict.fromkeys(result["metadata"]["knowledge_entity_id"] for result in search_results
        if result["metadata"].get("source") in {"jira", "confluence", "slack"}
        and result["metadata"].get("organization_id") and result["metadata"].get("connector_id")
        and isinstance(result["metadata"].get("knowledge_entity_id"), str)
        and result["metadata"]["knowledge_entity_id"].startswith(
            f"{result['metadata']['source']}:{result['metadata']['organization_id']}:{result['metadata']['connector_id']}:")))[:3]
    if not repositories and not entity_ids:
        return []
    stop_words = {"who", "what", "which", "the", "and", "for", "are", "was", "with", "from", "repository", "contributed", "contributors", "commits"}
    terms = list(dict.fromkeys(term.lower() for term in re.findall(r"[A-Za-z0-9_-]{3,}", question)
                               if term.lower() not in stop_words))[:8]
    service = None
    try:
        # Preserve the teammate service's defaults unless backend .env explicitly overrides them.
        config = {argument: getattr(settings, field) for argument, field in (
            ("uri", "NEO4J_URI"), ("username", "NEO4J_USERNAME"), ("password", "NEO4J_PASSWORD")
        ) if field in settings.model_fields_set}
        service = Neo4jService(**config, connection_timeout=2.0)
        if repositories and is_contributor_question(question):
            context = service.get_github_contributors(repositories, limit=6)
        else:
            context = service.get_github_relationships(repositories, terms, limit=6) if repositories else []
        if entity_ids and len(context) < 6:
            context.extend(service.get_knowledge_relationships(entity_ids, limit=6 - len(context)))
        return context
    except Exception as error:
        logger.warning("Optional Neo4j context unavailable (%s); continuing with Chroma only", type(error).__name__)
        return []
    finally:
        if service is not None:
            try:
                service.close()
            except Exception as error:
                logger.warning("Neo4j connection cleanup failed (%s)", type(error).__name__)
