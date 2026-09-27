from typing import Dict, Type, List, Optional
from connectors.base import BaseConnector


class UnrecognizedConnectorTypeError(ValueError):
    """Raised when a connector type has no registered implementation class."""
    pass


class ConnectorRegistry:
    def __init__(self):
        self._registry: Dict[str, Type[BaseConnector]] = {}

    def register(self, connector_type: str, connector_cls: Type[BaseConnector]) -> None:
        """Register a BaseConnector implementation class for a connector type."""
        self._registry[connector_type.lower().strip()] = connector_cls

    def unregister(self, connector_type: str) -> None:
        """Unregister a connector implementation."""
        self._registry.pop(connector_type.lower().strip(), None)

    def get_connector_class(self, connector_type: str) -> Type[BaseConnector]:
        """Resolve a BaseConnector implementation class by connector type."""
        key = connector_type.lower().strip()
        if key not in self._registry:
            raise UnrecognizedConnectorTypeError(
                f"No connector implementation registered for type: '{connector_type}'"
            )
        return self._registry[key]

    def is_registered(self, connector_type: str) -> bool:
        """Check if a connector type has a registered implementation."""
        return connector_type.lower().strip() in self._registry

    def list_registered_types(self) -> List[str]:
        """List all currently registered connector types."""
        return list(self._registry.keys())


# Singleton registry instance
registry = ConnectorRegistry()

# Auto-register existing GitHubConnector
try:
    from connectors.github.connector import GitHubConnector
    registry.register("github", GitHubConnector)
except ImportError:
    pass
