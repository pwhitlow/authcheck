import asyncio
import os
from typing import Optional
import socket
from pyradius import Client, Packet
from pyradius.packet import AccessRequest
from .base import BaseConnector


class RadiusConnector(BaseConnector):
    """RADIUS authentication source connector."""

    def __init__(self, config: dict = None):
        """Initialize RADIUS connector with configuration."""
        super().__init__(config)
        self.server = self.config.get("server") or os.getenv("RADIUS_SERVER")
        self.port = int(
            self.config.get("port") or os.getenv("RADIUS_PORT", "1812")
        )
        self.secret = self.config.get("secret") or os.getenv("RADIUS_SECRET")
        self.nas_identifier = (
            self.config.get("nas_identifier") or os.getenv("RADIUS_NAS_ID", "authcheck")
        )
        self.timeout = int(
            self.config.get("timeout") or os.getenv("RADIUS_TIMEOUT", "10")
        )
        self.test_password = (
            self.config.get("test_password") or "__TEST_PASSWORD__"
        )

    async def authenticate_user(self, username: str) -> bool:
        """
        Check if user exists in RADIUS by attempting authentication.

        Uses a test password to check if user exists. If we receive:
        - Access-Reject: User exists (password was wrong)
        - Access-Accept: User exists (test password happened to work)
        - Timeout/No response: User doesn't exist

        Args:
            username: Username to authenticate

        Returns:
            True if user exists, False otherwise

        Raises:
            Exception: On configuration or connection errors
        """
        if not self.validate_config():
            raise ValueError("RADIUS configuration is invalid or incomplete")

        try:
            # Run RADIUS authentication in thread pool (RADIUS library is synchronous)
            return await asyncio.to_thread(
                self._check_user_exists, username
            )
        except socket.timeout:
            raise TimeoutError("RADIUS server did not respond (timeout)")
        except socket.error as e:
            raise ConnectionError(f"Failed to connect to RADIUS server: {e}")
        except Exception as e:
            raise Exception(f"RADIUS error: {e}")

    def _check_user_exists(self, username: str) -> bool:
        """
        Synchronous method to check if user exists in RADIUS.

        Attempts authentication with a test password. The response indicates:
        - Access-Accept (code 2): User found, credentials accepted
        - Access-Reject (code 3): User found, credentials rejected (password wrong)
        - Access-Challenge (code 11): User found, needs additional info
        - No response or error: User not found
        """
        try:
            # Create RADIUS client
            client = Client(
                server=(self.server, self.port),
                secret=self.secret.encode("utf-8"),
                timeout=self.timeout,
            )

            # Create Access-Request packet
            request = client.CreatePacket(
                code=AccessRequest,
                User_Name=username,
                User_Password=self.test_password,
                NAS_Identifier=self.nas_identifier,
            )

            # Send request and get response
            reply = client.SendPacket(request)

            if reply is None:
                # No response = user likely doesn't exist
                return False

            # Access-Accept (code 2) or Access-Reject (code 3) = user exists
            # Access-Challenge (code 11) = user exists but needs more info
            if reply.code in (2, 3, 11):
                return True

            # Any other response = user doesn't exist
            return False

        except socket.timeout:
            raise
        except socket.error:
            raise
        except Exception as e:
            raise

    def get_display_name(self) -> str:
        """Get human-readable name for this connector."""
        return "RADIUS"

    def get_connector_id(self) -> str:
        """Get unique identifier for this connector."""
        return "radius"

    def validate_config(self) -> bool:
        """Validate that required RADIUS configuration is present."""
        if not self.server:
            return False
        if not self.secret:
            return False
        if not self.port or self.port < 1 or self.port > 65535:
            return False
        return True
