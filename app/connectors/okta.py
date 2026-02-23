import httpx
import os
from typing import Optional, List
import time
from .base import BaseConnector


class OktaConnector(BaseConnector):
    """Okta authentication source connector using OAuth2."""

    def __init__(self, config: dict = None):
        """Initialize Okta connector with OAuth2 configuration."""
        super().__init__(config)
        self.org_url = self.config.get("org_url") or os.getenv("OKTA_ORG_URL")
        self.client_id = self.config.get("client_id") or os.getenv("OKTA_CLIENT_ID")
        self.client_secret = (
            self.config.get("client_secret") or os.getenv("OKTA_CLIENT_SECRET")
        )
        # Fall back to API token if OAuth2 not configured
        self.api_token = self.config.get("api_token") or os.getenv("OKTA_API_TOKEN")
        self.timeout = self.config.get("timeout", 10)

        # Token cache
        self._access_token = None
        self._token_expires_at = 0

    async def _get_access_token(self, client: httpx.AsyncClient) -> str:
        """
        Get OAuth2 access token using Client Credentials flow.

        Returns cached token if still valid, otherwise requests a new one.
        """
        # Return cached token if still valid
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        # Request new token
        token_url = f"{self.org_url}/oauth2/v1/token"

        response = await client.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "scope": "okta.users.read",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )

        if response.status_code != 200:
            raise ValueError(
                f"Failed to get access token: {response.status_code} - {response.text}"
            )

        token_data = response.json()
        self._access_token = token_data["access_token"]
        # Cache token for slightly less than its actual expiration
        expires_in = token_data.get("expires_in", 3600)
        self._token_expires_at = time.time() + (expires_in - 60)

        return self._access_token

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
                # Get access token (OAuth2) or use API token
                if self.client_id and self.client_secret:
                    access_token = await self._get_access_token(client)
                    auth_header = f"Bearer {access_token}"
                else:
                    auth_header = f"Bearer {self.api_token}"

                # Search for user by login/email
                search_filter = f'profile.login eq "{username}"'
                url = f"{self.org_url}/api/v1/users"
                headers = {
                    "Authorization": auth_header,
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
                # Get access token (OAuth2) or use API token
                if self.client_id and self.client_secret:
                    access_token = await self._get_access_token(client)
                    auth_header = f"Bearer {access_token}"
                else:
                    auth_header = f"Bearer {self.api_token}"

                url = f"{self.org_url}/api/v1/users"
                headers = {
                    "Authorization": auth_header,
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
        # Basic validation of org URL format
        if not self.org_url.startswith("https://"):
            return False

        # Either OAuth2 (client_id + client_secret) or API token is required
        has_oauth2 = self.client_id and self.client_secret
        has_api_token = self.api_token

        if not (has_oauth2 or has_api_token):
            return False

        return True
