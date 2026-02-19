import asyncio
import os
from typing import Optional
from ldap3 import Server, Connection, ALL, Tls
import ssl
from .base import BaseConnector


class ActiveDirectoryConnector(BaseConnector):
    """Active Directory authentication source connector via LDAP."""

    def __init__(self, config: dict = None):
        """Initialize Active Directory connector with configuration."""
        super().__init__(config)
        self.server_address = (
            self.config.get("server") or os.getenv("AD_SERVER")
        )
        self.port = int(
            self.config.get("port") or os.getenv("AD_PORT", "389")
        )
        self.use_ssl = (
            self.config.get("use_ssl", False) or
            os.getenv("AD_USE_SSL", "false").lower() == "true"
        )
        self.base_dn = self.config.get("base_dn") or os.getenv("AD_BASE_DN")
        self.bind_dn = self.config.get("bind_dn") or os.getenv("AD_BIND_DN")
        self.bind_password = (
            self.config.get("bind_password") or os.getenv("AD_BIND_PASSWORD")
        )
        self.timeout = int(
            self.config.get("timeout") or os.getenv("AD_TIMEOUT", "10")
        )
        # Search attributes to try (in order)
        self.search_attributes = [
            "sAMAccountName",      # Windows username (john.doe)
            "userPrincipalName",   # Email format (john.doe@example.com)
            "mail",                # Email address
            "cn",                  # Common name
        ]

    async def authenticate_user(self, username: str) -> bool:
        """
        Check if user exists in Active Directory via LDAP.

        Args:
            username: Username to search for (supports sAMAccountName, UPN, email, CN)

        Returns:
            True if user exists and is enabled, False otherwise

        Raises:
            Exception: On LDAP connection or search errors
        """
        if not self.validate_config():
            raise ValueError(
                "Active Directory configuration is invalid or incomplete"
            )

        try:
            # Run LDAP operations in thread pool (ldap3 is synchronous)
            return await asyncio.to_thread(
                self._check_user_exists, username
            )
        except Exception as e:
            raise Exception(f"Active Directory error: {e}")

    def _check_user_exists(self, username: str) -> bool:
        """
        Synchronous method to check if user exists in Active Directory.

        Searches LDAP directory for user and checks if account is enabled.
        """
        try:
            # Create TLS configuration if SSL is enabled
            tls = None
            if self.use_ssl:
                tls = Tls(validate=ssl.CERT_NONE)

            # Create LDAP server connection
            server = Server(
                self.server_address,
                port=self.port,
                use_ssl=self.use_ssl,
                tls=tls,
                get_info=ALL,
                connect_timeout=self.timeout,
            )

            # Connect and bind with service account
            conn = Connection(
                server,
                user=self.bind_dn,
                password=self.bind_password,
                auto_bind=True,
            )

            try:
                # Try each search attribute
                user_found = False
                for attr in self.search_attributes:
                    search_filter = f"({attr}={username})"

                    # Search for the user
                    conn.search(
                        search_base=self.base_dn,
                        search_filter=search_filter,
                        attributes=["userAccountControl", "cn", "mail"],
                    )

                    if conn.entries:
                        entry = conn.entries[0]
                        user_found = True

                        # Check if user account is enabled
                        # userAccountControl bit 1 (0x0002) = ACCOUNTDISABLE
                        user_account_control = int(
                            entry.userAccountControl.value
                        )
                        is_enabled = not (user_account_control & 0x0002)

                        if is_enabled:
                            return True
                        else:
                            # User exists but is disabled
                            return False

                # If no search found the user, try case-insensitive search
                if not user_found:
                    search_filter = f"(|(sAMAccountName=*{username}*)(userPrincipalName=*{username}*))"
                    conn.search(
                        search_base=self.base_dn,
                        search_filter=search_filter,
                        attributes=["userAccountControl", "sAMAccountName"],
                    )

                    if conn.entries:
                        for entry in conn.entries:
                            user_account_control = int(
                                entry.userAccountControl.value
                            )
                            is_enabled = not (user_account_control & 0x0002)
                            if is_enabled:
                                return True

                return False

            finally:
                conn.unbind()

        except Exception as e:
            raise

    def get_display_name(self) -> str:
        """Get human-readable name for this connector."""
        return "Active Directory"

    def get_connector_id(self) -> str:
        """Get unique identifier for this connector."""
        return "active_directory"

    def validate_config(self) -> bool:
        """Validate that required Active Directory configuration is present."""
        if not self.server_address:
            return False
        if not self.base_dn:
            return False
        if not self.bind_dn:
            return False
        if not self.bind_password:
            return False
        if not self.port or self.port < 1 or self.port > 65535:
            return False
        return True
