from typing import List
from .base import BaseConnector
from okta.client import Client as OktaClient


class OktaConnector(BaseConnector):
    """Okta authentication source connector using Okta SDK."""

    def __init__(self, config: dict = None):
        """
        Initialize Okta connector.

        Expected config structure (matches Okta SDK format):
        {
            "orgUrl": "https://your-org.okta.com",
            "authorizationMode": "PrivateKey",
            "clientId": "your_client_id",
            "scopes": ["okta.users.read", "okta.users.manage"],
            "privateKey": "your_private_key_content"
        }
        """
        super().__init__(config)
        self.client = None

        # Initialize Okta client if config is provided
        if self.config:
            self.client = OktaClient(self.config)

    async def authenticate_user(self, username: str) -> bool:
        """
        Check if user exists in Okta.

        Args:
            username: Username to search for (will be used as-is in filter)

        Returns:
            True if user exists and is active, False otherwise
        """
        if not self.client:
            return False

        try:
            # Query Okta for user with matching login
            query_parameters = {'filter': f'profile.login eq "{username}"'}
            users, resp, err = await self.client.list_users(query_parameters)

            # Check if error occurred
            if err:
                return False

            # Check if any users were found
            for user in users:
                # User found - check if active
                if hasattr(user, 'status') and user.status == 'ACTIVE':
                    return True
                elif hasattr(user, 'status'):
                    # User exists but not active
                    return False
                else:
                    # No status field, assume active if found
                    return True

            # No users found
            return False

        except Exception:
            # On any error, return False (user not found)
            return False

    async def get_all_users(self) -> List[str]:
        """
        Get list of all active users from Okta.

        Returns:
            List of usernames (profile.login values)
        """
        if not self.client:
            raise NotImplementedError("Okta client not configured")

        all_users = []

        try:
            # Query for all active users
            query_parameters = {'filter': 'status eq "ACTIVE"'}
            users, resp, err = await self.client.list_users(query_parameters)

            if err:
                raise Exception(f"Error retrieving users from Okta: {err}")

            # Extract login from each user
            for user in users:
                if hasattr(user, 'profile') and hasattr(user.profile, 'login'):
                    all_users.append(user.profile.login)

            return all_users

        except Exception as e:
            raise Exception(f"Failed to get users from Okta: {str(e)}")

    def get_display_name(self) -> str:
        """Get human-readable name for this connector."""
        return "Okta"

    def get_connector_id(self) -> str:
        """Get unique identifier for this connector."""
        return "okta"

    def validate_config(self) -> bool:
        """Validate that required Okta configuration is present."""
        if not self.config:
            return False

        # Check for required fields
        required_fields = ["orgUrl", "authorizationMode", "clientId", "scopes", "privateKey"]
        for field in required_fields:
            if field not in self.config:
                return False

        # Basic validation
        if not self.config["orgUrl"].startswith("https://"):
            return False

        if not isinstance(self.config["scopes"], list) or not self.config["scopes"]:
            return False

        return True
