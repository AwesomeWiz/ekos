"""Optional read-only graph context using the existing Neo4j connection service."""

import logging
import re

from config.settings import settings
from graph.neo4j_service import Neo4jService

logger = logging.getLogger(__name__)


def retrieve_graph_context(question: str, search_results: list[dict]) -> list[dict]:
    # These repositories have already passed the search endpoint's tenant/connector filters.
    repositories = sorted({result["metadata"]["repository"] for result in search_results
                           if result["metadata"].get("source") == "github"
                           and isinstance(result["metadata"].get("repository"), str)
                           and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", result["metadata"]["repository"])})
    if not repositories:
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
        return service.get_github_relationships(repositories, terms, limit=6)
    except Exception as error:
        logger.warning("Optional Neo4j context unavailable (%s); continuing with Chroma only", type(error).__name__)
        return []
    finally:
        if service is not None:
            try:
                service.close()
            except Exception as error:
                logger.warning("Neo4j connection cleanup failed (%s)", type(error).__name__)
