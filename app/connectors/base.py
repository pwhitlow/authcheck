from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseConnector(ABC):
    """Abstract base class for authentication source connectors."""

    def __init__(self, config: Dict[str, Any] | None = None):
        """
        Initialize connector with optional configuration.

        Args:
            config: Dictionary containing connector-specific settings
        """
        self.config = config or {}

    @abstractmethod
    async def authenticate_user(self, username: str) -> bool:
        """
        Check if user exists in this authentication source.

        Args:
            username: Username to verify

        Returns:
            True if user exists, False otherwise
        """
        pass

    async def get_all_users(self) -> List[str]:
        """
        Get list of all users from this authentication source.

        Optional method - override in subclass if enumeration is supported.

        Returns:
            List of usernames

        Raises:
            NotImplementedError: If this connector doesn't support enumeration
        """
        raise NotImplementedError(
            f"{self.get_display_name()} connector does not support user enumeration"
        )

    @abstractmethod
    def get_display_name(self) -> str:
        """Get human-readable name for this connector."""
        pass

    @abstractmethod
    def get_connector_id(self) -> str:
        """Get unique identifier for this connector."""
        pass

    def validate_config(self) -> bool:
        """
        Validate that required configuration is present.

        Returns:
            True if config is valid, False otherwise
        """
        return True
