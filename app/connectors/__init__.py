from typing import Dict, List
from .base import BaseConnector
from .okta import OktaConnector
from .radius import RadiusConnector
from .active_directory import ActiveDirectoryConnector


class ConnectorRegistry:
    """Registry for managing available authentication source connectors."""

    def __init__(self):
        self._connectors: Dict[str, type[BaseConnector]] = {}
        self._instances: Dict[str, BaseConnector] = {}
        self._register_default_connectors()

    def _register_default_connectors(self):
        """Register built-in connectors."""
        self.register("okta", OktaConnector)
        self.register("radius", RadiusConnector)
        self.register("active_directory", ActiveDirectoryConnector)

    def register(self, connector_id: str, connector_class: type[BaseConnector]):
        """
        Register a connector class.

        Args:
            connector_id: Unique identifier for the connector
            connector_class: Class inheriting from BaseConnector
        """
        self._connectors[connector_id] = connector_class

    def get_connector(self, connector_id: str, config: Dict = None) -> BaseConnector:
        """
        Get an instance of a connector.

        Args:
            connector_id: Identifier of the connector to instantiate
            config: Configuration dictionary for the connector

        Returns:
            Instance of the requested connector

        Raises:
            ValueError: If connector_id is not registered
        """
        if connector_id not in self._connectors:
            raise ValueError(f"Connector '{connector_id}' not registered")

        # Create new instance with given config
        connector_class = self._connectors[connector_id]
        return connector_class(config or {})

    def get_all_connectors(self, config: Dict = None) -> List[BaseConnector]:
        """
        Get instances of all registered connectors.

        Args:
            config: Configuration dictionary (can contain per-connector settings)

        Returns:
            List of instantiated connectors
        """
        connectors = []
        for connector_id in self._connectors:
            connector_config = (config or {}).get(connector_id, {})
            connectors.append(self.get_connector(connector_id, connector_config))
        return connectors

    def list_connector_ids(self) -> List[str]:
        """Get list of registered connector IDs."""
        return list(self._connectors.keys())


# Global registry instance
_registry = ConnectorRegistry()


def get_registry() -> ConnectorRegistry:
    """Get the global connector registry."""
    return _registry
