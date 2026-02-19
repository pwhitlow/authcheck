import httpx
import os
from typing import Optional, List
from .base import BaseConnector


class OktaConnector(BaseConnector):
    """Okta authentication source connector."""

    def __init__(self, config: dict = None):
        """Initialize Okta connector with configuration."""
        super().__init__(config)
        self.org_url = self.config.get("org_url") or os.getenv("OKTA_ORG_URL")
        self.api_token = self.config.get("api_token") or os.getenv("OKTA_API_TOKEN")
        self.timeout = self.config.get("timeout", 10)

    async def authenticate_user(self, username: str) -> bool:
        """
        Check if user exists in Okta by querying the Users API.

        Args:
            username: Username to search for (email, login, or username)

        Returns:
            True if user exists and is active, False otherwise

        Raises:
            Exception: On authentication or network errors
        """
        if not self.validate_config():
            raise ValueError("Okta configuration is invalid or incomplete")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Search for user by login/email
                search_filter = f'profile.login eq "{username}"'
                url = f"{self.org_url}/api/v1/users"
                headers = {
                    "Authorization": f"Bearer {self.api_token}",
                    "Accept": "application/json",
                }

                response = await client.get(
                    url,
                    params={"filter": search_filter},
                    headers=headers,
                )

                # 200 = found, 401 = auth error, 403 = forbidden, 404 = not found
                if response.status_code == 200:
                    users = response.json()
                    # Check if any active user was found
                    if users:
                        for user in users:
                            if user.get("status") == "ACTIVE":
                                return True
                    return False

                elif response.status_code == 401:
                    raise ValueError("Okta authentication failed: Invalid API token")
                elif response.status_code == 403:
                    raise ValueError("Okta authentication failed: Insufficient permissions")
                elif response.status_code == 404:
                    return False
                else:
                    raise Exception(
                        f"Okta API error: {response.status_code} - {response.text}"
                    )

        except httpx.TimeoutException:
            raise TimeoutError("Okta API request timed out")
        except httpx.ConnectError:
            raise ConnectionError(f"Failed to connect to Okta at {self.org_url}")

    async def get_all_users(self) -> List[str]:
        """
        Get list of all active users from Okta.

        Returns:
            List of usernames (profile.login values)

        Raises:
            Exception: On authentication or network errors
        """
        if not self.validate_config():
            raise ValueError("Okta configuration is invalid or incomplete")

        all_users = []
        after = None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.org_url}/api/v1/users"
                headers = {
                    "Authorization": f"Bearer {self.api_token}",
                    "Accept": "application/json",
                }

                while True:
                    params = {
                        "filter": 'status eq "ACTIVE"',
                        "limit": 200,  # Max page size
                    }
                    if after:
                        params["after"] = after

                    response = await client.get(url, params=params, headers=headers)

                    if response.status_code != 200:
                        if response.status_code == 401:
                            raise ValueError(
                                "Okta authentication failed: Invalid API token"
                            )
                        elif response.status_code == 403:
                            raise ValueError(
                                "Okta authentication failed: Insufficient permissions"
                            )
                        else:
                            raise Exception(
                                f"Okta API error: {response.status_code} - {response.text}"
                            )

                    users = response.json()
                    if not users:
                        break

                    # Extract login (username) from each user
                    for user in users:
                        login = user.get("profile", {}).get("login")
                        if login:
                            all_users.append(login)

                    # Check for pagination (Okta uses Link header)
                    link_header = response.headers.get("Link", "")
                    if 'rel="next"' not in link_header:
                        break

                    # Extract 'after' cursor from Link header
                    for link in link_header.split(","):
                        if 'rel="next"' in link:
                            # Extract URL and get 'after' parameter
                            import re

                            match = re.search(r'after=([^&>]+)', link)
                            if match:
                                after = match.group(1)
                            break

                return all_users

        except httpx.TimeoutException:
            raise TimeoutError("Okta API request timed out")
        except httpx.ConnectError:
            raise ConnectionError(f"Failed to connect to Okta at {self.org_url}")

    def get_display_name(self) -> str:
        """Get human-readable name for this connector."""
        return "Okta"

    def get_connector_id(self) -> str:
        """Get unique identifier for this connector."""
        return "okta"

    def validate_config(self) -> bool:
        """Validate that required Okta configuration is present."""
        if not self.org_url:
            return False
        if not self.api_token:
            return False
        # Basic validation of org URL format
        if not self.org_url.startswith("https://"):
            return False
        return True
