"""Idempotent, explicit demo bootstrap over the existing models."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from config.settings import settings
from models.connector import Connector, ConnectorConfiguration
from models.organization import Organization
from models.permission import Permission
from models.role import Role


ROLE_PERMISSIONS = {
    "Administrator": {
        ("connectors", "read"),
        ("connectors", "manage"),
        ("connectors", "test"),
        ("connectors", "sync"),
    },
    "Developer": {("connectors", "read")},
}


def seed_demo(db: Session, include_connector: bool = True) -> None:
    """Add missing permissions and one registered GitHub source, preserving rows and secrets."""
    for role_name, grants in ROLE_PERMISSIONS.items():
        role = db.query(Role).filter(Role.role_name == role_name).one()
        existing = {(item.resource, item.action) for item in role.permissions}
        for resource, action in grants - existing:
            db.add(Permission(role_id=role.id, resource=resource, action=action))

    if include_connector:
        org = db.query(Organization).filter(Organization.name == "ABC Solutions").one()
        configured = bool(settings.GITHUB_TOKEN and settings.GITHUB_OWNER and settings.GITHUB_REPO)
        connector = db.query(Connector).filter(
            Connector.organization_id == org.id, func.lower(Connector.type) == "github"
        ).first()
        if connector is None:
            connector = Connector(
                name="GitHub", type="GitHub", organization_id=org.id,
                status="configured" if configured else "not_configured",
            )
            db.add(connector)
            db.flush()
        elif not configured:
            connector.status = "not_configured"
        elif connector.status == "not_configured":
            connector.status = "configured"

        if connector.configuration is None:
            db.add(ConnectorConfiguration(
                connector_id=connector.id,
                api_url=f"https://github.com/{settings.GITHUB_OWNER}/{settings.GITHUB_REPO}" if configured else None,
            ))
        elif configured and not connector.configuration.api_url:
            connector.configuration.api_url = f"https://github.com/{settings.GITHUB_OWNER}/{settings.GITHUB_REPO}"

    db.commit()
