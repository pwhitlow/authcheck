from .base import BaseConnector


class RadiusConnector(BaseConnector):
    """RADIUS authentication source connector."""

    async def authenticate_user(self, username: str) -> bool:
        """
        Check if user exists in RADIUS.

        TODO: Implement actual RADIUS protocol integration
        Current: Returns placeholder value
        """
        # Placeholder implementation
        # Will be replaced with actual RADIUS queries once server details/credentials are available
        return False

    def get_display_name(self) -> str:
        return "RADIUS"

    def get_connector_id(self) -> str:
        return "radius"

    def validate_config(self) -> bool:
        """Validate RADIUS configuration."""
        # TODO: Check for required config like server address, shared secret, etc.
        return True
