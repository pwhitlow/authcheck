from .base import BaseConnector


class ActiveDirectoryConnector(BaseConnector):
    """Active Directory authentication source connector."""

    async def authenticate_user(self, username: str) -> bool:
        """
        Check if user exists in Active Directory.

        TODO: Implement actual AD LDAP/ADSI integration
        Current: Returns placeholder value
        """
        # Placeholder implementation
        # Will be replaced with actual AD queries once LDAP server details/credentials are available
        return True

    def get_display_name(self) -> str:
        return "Active Directory"

    def get_connector_id(self) -> str:
        return "active_directory"

    def validate_config(self) -> bool:
        """Validate Active Directory configuration."""
        # TODO: Check for required config like LDAP server, bind DN, credentials, etc.
        return True
