import httpx
import os
from typing import Optional, List
import time
import json
import jwt
from datetime import datetime, timedelta
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

        # Private key for private_key_jwt authentication (supports both PEM and JWK formats)
        private_key_input = self.config.get("private_key") or os.getenv("OKTA_PRIVATE_KEY")
        self.private_key_pem = None
        self.private_key_jwk = None
        self.private_key_kid = None

        if private_key_input:
            # Try PEM format first
            if isinstance(private_key_input, str) and "-----BEGIN" in private_key_input:
                # Handle escaped newlines (\n as literal backslash-n)
                private_key_input = private_key_input.replace("\\n", "\n")
                self.private_key_pem = private_key_input
                # Try to extract kid from environment or config if available
                kid_input = self.config.get("private_key_kid") or os.getenv("OKTA_PRIVATE_KEY_KID")
                if kid_input:
                    self.private_key_kid = kid_input
            else:
                # Try JWK format
                try:
                    key_data = json.loads(private_key_input) if isinstance(private_key_input, str) else private_key_input
                    self.private_key_jwk = key_data
                    self.private_key_kid = key_data.get("kid")
                except (json.JSONDecodeError, TypeError):
                    pass

        # Token cache
        self._access_token = None
        self._token_expires_at = 0

    def _create_jwt_assertion(self, token_url: str) -> str:
        """
        Create a signed JWT assertion for private_key_jwt authentication.

        Supports both PEM and JWK format private keys.

        Args:
            token_url: The token endpoint URL

        Returns:
            Signed JWT string
        """
        now = datetime.utcnow()
        exp = now + timedelta(seconds=1)

        # JWT Header
        header = {
            "alg": "RS256",
            "typ": "JWT",
        }
        if self.private_key_kid:
            header["kid"] = self.private_key_kid

        # JWT Claims
        # Okta requires: iss (client_id), sub (client_id), aud (token endpoint), iat, exp
        payload = {
            "iss": self.client_id,
            "sub": self.client_id,
            "aud": token_url,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }

        try:
            # If we have PEM format, use it directly
            if self.private_key_pem:
                token = jwt.encode(
                    payload, self.private_key_pem, algorithm="RS256", headers=header
                )
                return token

            # Otherwise, convert JWK to PEM
            if self.private_key_jwk:
                from cryptography.hazmat.primitives import serialization
                from cryptography.hazmat.backends import default_backend
                from cryptography.hazmat.primitives.asymmetric import rsa

                # Convert JWK RSA key to PEM
                n = int.from_bytes(
                    __import__("base64").urlsafe_b64decode(
                        self.private_key_jwk["n"]
                        + "=" * (4 - len(self.private_key_jwk["n"]) % 4)
                    ),
                    "big",
                )
                e = int.from_bytes(
                    __import__("base64").urlsafe_b64decode(
                        self.private_key_jwk["e"]
                        + "=" * (4 - len(self.private_key_jwk["e"]) % 4)
                    ),
                    "big",
                )
                d = int.from_bytes(
                    __import__("base64").urlsafe_b64decode(
                        self.private_key_jwk["d"]
                        + "=" * (4 - len(self.private_key_jwk["d"]) % 4)
                    ),
                    "big",
                )
                p = int.from_bytes(
                    __import__("base64").urlsafe_b64decode(
                        self.private_key_jwk["p"]
                        + "=" * (4 - len(self.private_key_jwk["p"]) % 4)
                    ),
                    "big",
                )
                q = int.from_bytes(
                    __import__("base64").urlsafe_b64decode(
                        self.private_key_jwk["q"]
                        + "=" * (4 - len(self.private_key_jwk["q"]) % 4)
                    ),
                    "big",
                )
                dmp1 = int.from_bytes(
                    __import__("base64").urlsafe_b64decode(
                        self.private_key_jwk["dp"]
                        + "=" * (4 - len(self.private_key_jwk["dp"]) % 4)
                    ),
                    "big",
                )
                dmq1 = int.from_bytes(
                    __import__("base64").urlsafe_b64decode(
                        self.private_key_jwk["dq"]
                        + "=" * (4 - len(self.private_key_jwk["dq"]) % 4)
                    ),
                    "big",
                )
                iqmp = int.from_bytes(
                    __import__("base64").urlsafe_b64decode(
                        self.private_key_jwk["qi"]
                        + "=" * (4 - len(self.private_key_jwk["qi"]) % 4)
                    ),
                    "big",
                )

                # Create RSA key
                rsa_key = rsa.RSAPrivateNumbers(
                    p=p,
                    q=q,
                    d=d,
                    dmp1=dmp1,
                    dmq1=dmq1,
                    iqmp=iqmp,
                    public_numbers=rsa.RSAPublicNumbers(e=e, n=n),
                )

                private_key_pem = rsa_key.private_key(
                    backend=default_backend()
                ).private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )

                token = jwt.encode(
                    payload, private_key_pem, algorithm="RS256", headers=header
                )
                return token

            raise ValueError("No private key configured (PEM or JWK)")

        except Exception as e:
            raise ValueError(f"Failed to create JWT assertion: {e}")

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

        # Prepare token request data
        data = {
            "grant_type": "client_credentials",
            "scope": "okta.users.read",
        }

        # Use private_key_jwt if private key is available, otherwise use client_secret
        if self.private_key_pem or self.private_key_jwk:
            jwt_assertion = self._create_jwt_assertion(token_url)
            data["client_assertion_type"] = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
            data["client_assertion"] = jwt_assertion
        else:
            data["client_id"] = self.client_id
            data["client_secret"] = self.client_secret

        response = await client.post(token_url, data=data)

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
                if self.client_id and (self.client_secret or self.private_key_pem or self.private_key_jwk):
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
                if self.client_id and (self.client_secret or self.private_key_pem or self.private_key_jwk):
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

        # Check for valid authentication method:
        # 1. OAuth2 with private_key_jwt (client_id + private_key in PEM or JWK format)
        # 2. OAuth2 with client_secret (client_id + client_secret)
        # 3. API token
        has_oauth2_private_key = self.client_id and (self.private_key_pem or self.private_key_jwk)
        has_oauth2_client_secret = self.client_id and self.client_secret
        has_api_token = self.api_token

        if not (has_oauth2_private_key or has_oauth2_client_secret or has_api_token):
            return False

        return True
