from typing import List, Optional, Dict, Any
import aiohttp
import ssl
import certifi
from pathlib import Path
from .base import BaseConnector


class SlackConnector(BaseConnector):
    """Slack workspace connector using Slack Web API."""

    def __init__(self, config: dict = None):
        """
        Initialize Slack connector.

        Expected config structure:
        {
            "token": "xoxb-your-slack-token"
        }

        If no token provided in config, will attempt to read from apitoken.txt
        """
        super().__init__(config)
        self.token = None
        self._users_cache = None
        self._user_details_cache = None

        # Get token from config or file
        if self.config and "token" in self.config:
            self.token = self.config["token"]
        else:
            # Try to read from apitoken.txt
            token_file = Path("apitoken.txt")
            if token_file.exists():
                try:
                    self.token = token_file.read_text().strip()
                except Exception:
                    pass

    def _get_account_type(self, user: dict) -> str:
        """
        Determine the account type for a Slack user.

        Args:
            user: User object from Slack API

        Returns:
            Human-readable account type
        """
        # Check for bots first
        if user.get("is_bot", False):
            return "Bot"

        # Check for ownership/admin levels
        if user.get("is_primary_owner", False):
            return "Primary Owner"
        if user.get("is_owner", False):
            return "Owner"
        if user.get("is_admin", False):
            return "Admin"

        # Check for guest types
        if user.get("is_ultra_restricted", False):
            return "Single-Channel Guest"
        if user.get("is_restricted", False):
            return "Multi-Channel Guest"

        # Default to regular member
        return "Member"

    async def _fetch_all_users(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch all users from Slack API and cache them.

        Returns:
            Dictionary mapping email addresses to user details
        """
        if self._user_details_cache is not None:
            return self._user_details_cache

        if not self.token:
            return {}

        user_details_map = {}

        try:
            # Create SSL context with certifi certificates for macOS compatibility
            ssl_context = ssl.create_default_context(cafile=certifi.where())

            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
                cursor = None
                while True:
                    # Build request URL with pagination
                    url = "https://slack.com/api/users.list"
                    params = {"limit": 200}
                    if cursor:
                        params["cursor"] = cursor

                    headers = {"Authorization": f"Bearer {self.token}"}

                    async with session.get(url, params=params, headers=headers) as response:
                        data = await response.json()

                        if not data.get("ok", False):
                            error = data.get("error", "Unknown error")
                            print(f"Slack API error: {error}")
                            break

                        members = data.get("members", [])

                        for user in members:
                            # Skip deleted users
                            if user.get("deleted", False):
                                continue

                            # Get email from profile
                            profile = user.get("profile", {})
                            email = profile.get("email", "")

                            # Skip users without email
                            if not email:
                                continue

                            # Build user details
                            details = {
                                "username": email,
                                "email": email,
                                "source": "Slack",
                                "slack_id": user.get("id", ""),
                                "account_type": self._get_account_type(user),
                                "status": "active" if not user.get("deleted", False) else "deleted",
                            }

                            # Add profile information
                            if profile.get("real_name"):
                                details["full_name"] = profile["real_name"]
                            if profile.get("first_name"):
                                details["first_name"] = profile["first_name"]
                            if profile.get("last_name"):
                                details["last_name"] = profile["last_name"]
                            if profile.get("display_name"):
                                details["display_name"] = profile["display_name"]
                            if profile.get("title"):
                                details["title"] = profile["title"]
                            if profile.get("phone"):
                                details["phone"] = profile["phone"]

                            user_details_map[email.lower()] = details

                        # Check for pagination
                        cursor = data.get("response_metadata", {}).get("next_cursor")
                        if not cursor:
                            break

        except Exception as e:
            print(f"Error fetching Slack users: {e}")
            return {}

        self._user_details_cache = user_details_map
        return user_details_map

    async def authenticate_user(self, username: str) -> bool:
        """
        Check if user exists in Slack.

        Args:
            username: Email address to search for

        Returns:
            True if user exists and is active, False otherwise
        """
        users = await self._fetch_all_users()
        return username.lower() in users

    async def get_user_details(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a user from Slack.

        Args:
            username: Email address to search for

        Returns:
            Dictionary with user details including account type
        """
        users = await self._fetch_all_users()
        return users.get(username.lower())

    async def get_all_users(self) -> List[str]:
        """
        Get list of all active users from Slack.

        Returns:
            List of email addresses
        """
        users = await self._fetch_all_users()
        return sorted(list(users.keys()), key=str.lower)

    def get_display_name(self) -> str:
        """Get human-readable name for this connector."""
        return "Slack"

    def get_connector_id(self) -> str:
        """Get unique identifier for this connector."""
        return "slack"

    def validate_config(self) -> bool:
        """Validate that Slack token is present."""
        return self.token is not None and len(self.token) > 0
