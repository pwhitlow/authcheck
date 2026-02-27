import asyncio
import os
import json
from typing import Optional, List, Dict, Any
from pathlib import Path
from ldap3 import Server, Connection, ALL, Tls
import ssl
from .base import BaseConnector


class ActiveDirectoryConnector(BaseConnector):
    """Active Directory authentication source connector via LDAP."""

    def __init__(self, config: dict = None):
        """Initialize Active Directory connector with configuration."""
        super().__init__(config)

        # Try to load from ~/.ad_config if no config provided
        if not config or not config.get("server"):
            ad_config_path = Path.home() / ".ad_config"
            if ad_config_path.exists():
                try:
                    with open(ad_config_path, 'r') as f:
                        file_config = json.load(f)
                        # Merge file config with provided config
                        self.config = {**file_config, **(config or {})}
                except Exception:
                    pass

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
            self.config.get("password") or self.config.get("bind_password") or os.getenv("AD_BIND_PASSWORD")
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
        """
        if not self.validate_config():
            raise ValueError(
                "Active Directory configuration is invalid or incomplete"
            )

        try:
            # Run LDAP operations in thread pool
            return await asyncio.to_thread(self._check_user_exists, username)
        except Exception as e:
            print(f"Active Directory error: {e}")
            return False

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

    async def get_all_users(self) -> List[str]:
        """
        Get list of all enabled users from Active Directory.

        Returns:
            List of usernames (sAMAccountName values)

        Raises:
            Exception: On LDAP connection or search errors
        """
        if not self.validate_config():
            raise ValueError(
                "Active Directory configuration is invalid or incomplete"
            )

        try:
            # Run LDAP operations in thread pool
            return await asyncio.to_thread(self._get_all_users_sync)
        except Exception as e:
            raise Exception(f"Active Directory error: {e}")

    def _get_all_users_sync(self) -> List[str]:
        """
        Synchronous method to get all enabled users from Active Directory.
        """
        all_users = []

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
                # Search for all enabled user objects (real users only, not computers/services)
                # Filters:
                # - objectCategory=person (more specific than objectClass=user)
                # - objectClass=user (user objects)
                # - !(userAccountControl:1.2.840.113556.1.4.803:=2) (not disabled)
                # - !(sAMAccountName=*$) (exclude computer accounts ending with $)
                # - mail=* (require email address to filter out service accounts)
                search_filter = (
                    "(&"
                    "(objectCategory=person)"
                    "(objectClass=user)"
                    "(!(userAccountControl:1.2.840.113556.1.4.803:=2))"
                    "(!(sAMAccountName=*$))"
                    "(mail=*)"
                    ")"
                )

                conn.search(
                    search_base=self.base_dn,
                    search_filter=search_filter,
                    attributes=["sAMAccountName"],
                    paged_size=500,  # Use paging for large results
                )

                # Extract sAMAccountName from each user
                for entry in conn.entries:
                    sam_account = entry.sAMAccountName.value
                    if sam_account:
                        all_users.append(sam_account)

                return all_users

            finally:
                conn.unbind()

        except Exception as e:
            raise

    async def get_user_details(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a user from Active Directory.

        Args:
            username: Username to search for

        Returns:
            Dictionary with user details or None if not found
        """
        if not self.validate_config():
            return None

        try:
            return await asyncio.to_thread(self._get_user_details_sync, username)
        except Exception:
            return None

    def _get_user_details_sync(self, username: str) -> Optional[Dict[str, Any]]:
        """Synchronous method to get user details from Active Directory."""
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
                for attr in self.search_attributes:
                    search_filter = f"({attr}={username})"

                    # Search for the user with all standard attributes
                    conn.search(
                        search_base=self.base_dn,
                        search_filter=search_filter,
                        attributes=[
                            "sAMAccountName", "userPrincipalName", "mail",
                            "cn", "givenName", "sn", "displayName",
                            "title", "department", "telephoneNumber",
                            "mobile", "userAccountControl"
                        ],
                    )

                    if conn.entries:
                        entry = conn.entries[0]

                        # Build user details dictionary
                        details = {
                            "username": username,
                            "source": "Active Directory",
                        }

                        # Add available attributes
                        if hasattr(entry, 'sAMAccountName') and entry.sAMAccountName.value:
                            details["sam_account_name"] = entry.sAMAccountName.value
                        if hasattr(entry, 'userPrincipalName') and entry.userPrincipalName.value:
                            details["email"] = entry.userPrincipalName.value
                        if hasattr(entry, 'mail') and entry.mail.value:
                            details["email"] = entry.mail.value
                        if hasattr(entry, 'cn') and entry.cn.value:
                            details["full_name"] = entry.cn.value
                        if hasattr(entry, 'givenName') and entry.givenName.value:
                            details["first_name"] = entry.givenName.value
                        if hasattr(entry, 'sn') and entry.sn.value:
                            details["last_name"] = entry.sn.value
                        if hasattr(entry, 'displayName') and entry.displayName.value:
                            details["display_name"] = entry.displayName.value
                        if hasattr(entry, 'title') and entry.title.value:
                            details["title"] = entry.title.value
                        if hasattr(entry, 'department') and entry.department.value:
                            details["department"] = entry.department.value
                        if hasattr(entry, 'telephoneNumber') and entry.telephoneNumber.value:
                            details["phone"] = entry.telephoneNumber.value
                        if hasattr(entry, 'mobile') and entry.mobile.value:
                            details["mobile_phone"] = entry.mobile.value

                        # Add account status
                        if hasattr(entry, 'userAccountControl'):
                            user_account_control = int(entry.userAccountControl.value)
                            is_enabled = not (user_account_control & 0x0002)
                            details["status"] = "active" if is_enabled else "disabled"

                        return details

                return None

            finally:
                conn.unbind()

        except Exception:
            return None

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
