import logging
import re
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth.dependencies import require_permission
from config.settings import settings
from graph.neo4j_service import Neo4jService
from models.base import get_db
from models.connector import Connector, ConnectorConfiguration
from models.user import User
from schemas.graph import GraphResponse

router = APIRouter(prefix="/graph", tags=["Knowledge graph"])
logger = logging.getLogger(__name__)


@router.get("", response_model=GraphResponse)
def read_graph(db: Session = Depends(get_db), user: User = Depends(require_permission("connectors", "read"))):
    if not user.organization_id:
        return GraphResponse()
    configs = db.query(ConnectorConfiguration.api_url).join(Connector).filter(
        Connector.organization_id == user.organization_id, func.lower(Connector.type) == "github"
    ).all()
    repositories = set()
    for config in configs:
        url = urlparse(config.api_url or "")
        path = url.path.strip("/")
        if url.scheme in {"http", "https"} and url.hostname == "github.com" and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", path):
            repositories.add(path)
    if not repositories:
        return GraphResponse()
    service = None
    try:
        config = {argument: getattr(settings, field) for argument, field in (
            ("uri", "NEO4J_URI"), ("username", "NEO4J_USERNAME"), ("password", "NEO4J_PASSWORD")
        ) if field in settings.model_fields_set}
        service = Neo4jService(**config, connection_timeout=2.0)
        return GraphResponse(**service.get_github_graph(sorted(repositories)[:3], limit=6))
    except Exception as error:
        logger.warning("Knowledge graph unavailable (%s)", type(error).__name__)
        raise HTTPException(status_code=503, detail="Knowledge graph is unavailable. Check the local Neo4j service and try again.") from error
    finally:
        if service is not None:
            try:
                service.close()
            except Exception as error:
                logger.warning("Graph connection cleanup failed (%s)", type(error).__name__)
