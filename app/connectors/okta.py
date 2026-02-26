from typing import List, Optional, Dict, Any
import json
import os
from pathlib import Path
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
        self.role_mapping = self._load_role_mapping()

        # Initialize Okta client if config is provided
        if self.config:
            self.client = OktaClient(self.config)

    def _load_role_mapping(self) -> Dict[str, str]:
        """
        Load role code to display name mapping from JSON file.

        Returns:
            Dictionary mapping role codes to display names
        """
        mapping_file = Path(__file__).parent.parent.parent / "okta_role_mapping.json"

        if mapping_file.exists():
            try:
                with open(mapping_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass

        # Return empty dict if file doesn't exist or can't be read
        return {}

    def _translate_role(self, role_code: str) -> str:
        """
        Translate role code to human-readable name.

        Args:
            role_code: The role code from Okta

        Returns:
            Human-readable role name, or original code if no mapping exists
        """
        if not role_code:
            return role_code

        # Return mapped value if exists, otherwise return original code
        return self.role_mapping.get(role_code.lower(), role_code)

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

    async def get_user_details(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a user from Okta.

        Args:
            username: Username to search for

        Returns:
            Dictionary with user details including profile info, status, and groups/roles
        """
        if not self.client:
            return None

        try:
            # Query Okta for user with matching login
            query_parameters = {'filter': f'profile.login eq "{username}"'}
            users, resp, err = await self.client.list_users(query_parameters)

            if err or not users:
                return None

            # Get first matching user
            user = users[0]

            # Build user details dictionary
            details = {
                "username": username,
                "email": username,
                "status": user.status if hasattr(user, 'status') else 'UNKNOWN',
                "source": "Okta"
            }

            # Extract profile information
            if hasattr(user, 'profile'):
                profile = user.profile
                if hasattr(profile, 'firstName'):
                    details["first_name"] = profile.firstName
                if hasattr(profile, 'lastName'):
                    details["last_name"] = profile.lastName
                if hasattr(profile, 'firstName') and hasattr(profile, 'lastName'):
                    details["full_name"] = f"{profile.firstName} {profile.lastName}"
                if hasattr(profile, 'email'):
                    details["email"] = profile.email
                if hasattr(profile, 'title'):
                    details["title"] = profile.title
                if hasattr(profile, 'department'):
                    details["department"] = profile.department
                if hasattr(profile, 'mobilePhone'):
                    details["mobile_phone"] = profile.mobilePhone
                if hasattr(profile, 'userRole'):
                    # Store both raw code and translated version
                    raw_role = profile.userRole
                    details["user_role"] = self._translate_role(raw_role)
                    details["user_role_code"] = raw_role  # Keep original code for reference

            # Get user's groups (which represent roles in Okta)
            try:
                groups, resp, err = await self.client.list_user_groups(user.id)
                if not err and groups:
                    group_names = []
                    for group in groups:
                        if hasattr(group, 'profile') and hasattr(group.profile, 'name'):
                            group_names.append(group.profile.name)

                    if group_names:
                        details["groups"] = ", ".join(group_names)
                        details["roles"] = ", ".join(group_names)  # Alias for groups
            except Exception:
                # If we can't get groups, just continue without them
                pass

            # Get user's assigned roles (admin roles)
            try:
                roles, resp, err = await self.client.list_assigned_roles_for_user(user.id)
                if not err and roles:
                    role_names = []
                    for role in roles:
                        if hasattr(role, 'type'):
                            role_names.append(role.type)

                    if role_names:
                        details["admin_roles"] = ", ".join(role_names)
            except Exception:
                # If we can't get admin roles, just continue without them
                pass

            return details

        except Exception:
            return None

    async def get_all_users(self) -> List[str]:
        """
        Get list of all active users from Okta.

        Handles pagination to retrieve all users.

        Returns:
            List of usernames (profile.login values)
        """
        if not self.client:
            raise NotImplementedError("Okta client not configured")

        all_users = []

        try:
            # Query for all active users with pagination
            query_parameters = {'filter': 'status eq "ACTIVE"'}

            # Get first page
            users, resp, err = await self.client.list_users(query_parameters)

            if err:
                raise Exception(f"Error retrieving users from Okta: {err}")

            # Process first page
            for user in users:
                if hasattr(user, 'profile') and hasattr(user.profile, 'login'):
                    all_users.append(user.profile.login)

            # Check for more pages and iterate through them
            while resp.has_next():
                users, err = await resp.next()
                if err:
                    raise Exception(f"Error retrieving next page from Okta: {err}")

                for user in users:
                    if hasattr(user, 'profile') and hasattr(user.profile, 'login'):
                        all_users.append(user.profile.login)

            return all_users

        except Exception as e:
            raise Exception(f"Failed to get users from Okta: {str(e)}")

    async def get_all_users_with_details(self, include_groups: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Get all active users from Okta with their full details in one batch operation.

        This is much more efficient than calling get_user_details() for each user individually
        because it processes users as they're paginated and only makes 2 API calls per user
        (groups + roles) instead of 3 (search + groups + roles).

        Args:
            include_groups: Whether to fetch group and role information (default True)

        Returns:
            Dictionary mapping usernames to their full details
        """
        if not self.client:
            raise NotImplementedError("Okta client not configured")

        user_details_map = {}

        try:
            # Query for all active users with pagination
            query_parameters = {'filter': 'status eq "ACTIVE"'}

            # Get first page
            users, resp, err = await self.client.list_users(query_parameters)

            if err:
                raise Exception(f"Error retrieving users from Okta: {err}")

            # Process first page
            await self._process_user_batch(users, user_details_map, include_groups)

            # Check for more pages and iterate through them
            while resp.has_next():
                users, err = await resp.next()
                if err:
                    raise Exception(f"Error retrieving next page from Okta: {err}")

                await self._process_user_batch(users, user_details_map, include_groups)

            return user_details_map

        except Exception as e:
            raise Exception(f"Failed to get users with details from Okta: {str(e)}")

    async def _process_user_batch(self, users: List, user_details_map: Dict[str, Dict[str, Any]], include_groups: bool):
        """
        Process a batch of users and extract their details.

        Args:
            users: List of user objects from Okta
            user_details_map: Dictionary to populate with user details
            include_groups: Whether to fetch group and role information
        """
        for user in users:
            if not hasattr(user, 'profile') or not hasattr(user.profile, 'login'):
                continue

            username = user.profile.login
            profile = user.profile

            # Build user details dictionary from profile
            details = {
                "username": username,
                "email": username,
                "status": user.status if hasattr(user, 'status') else 'UNKNOWN',
                "source": "Okta"
            }

            # Extract profile information
            if hasattr(profile, 'firstName'):
                details["first_name"] = profile.firstName
            if hasattr(profile, 'lastName'):
                details["last_name"] = profile.lastName
            if hasattr(profile, 'firstName') and hasattr(profile, 'lastName'):
                details["full_name"] = f"{profile.firstName} {profile.lastName}"
            if hasattr(profile, 'email'):
                details["email"] = profile.email
            if hasattr(profile, 'title'):
                details["title"] = profile.title
            if hasattr(profile, 'department'):
                details["department"] = profile.department
            if hasattr(profile, 'mobilePhone'):
                details["mobile_phone"] = profile.mobilePhone
            if hasattr(profile, 'userRole'):
                raw_role = profile.userRole
                details["user_role"] = self._translate_role(raw_role)
                details["user_role_code"] = raw_role

            # Optionally fetch groups and roles
            if include_groups:
                try:
                    groups, resp, err = await self.client.list_user_groups(user.id)
                    if not err and groups:
                        group_names = []
                        for group in groups:
                            if hasattr(group, 'profile') and hasattr(group.profile, 'name'):
                                group_names.append(group.profile.name)

                        if group_names:
                            details["groups"] = ", ".join(group_names)
                            details["roles"] = ", ".join(group_names)
                except Exception:
                    pass

                try:
                    roles, resp, err = await self.client.list_assigned_roles_for_user(user.id)
                    if not err and roles:
                        role_names = []
                        for role in roles:
                            if hasattr(role, 'type'):
                                role_names.append(role.type)

                        if role_names:
                            details["admin_roles"] = ", ".join(role_names)
                except Exception:
                    pass

            user_details_map[username] = details

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
