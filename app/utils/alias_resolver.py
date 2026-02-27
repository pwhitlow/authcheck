"""User group resolver for associating multiple email addresses to a single user."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class UserGroupResolver:
    """
    Manages user email groupings for alias association.

    This class provides a mechanism to associate multiple email addresses
    into logical groups representing a single user. Groups are loaded from
    a JSON configuration file and provide bidirectional mapping between
    individual emails and group identifiers.
    """

    _instance = None

    def __init__(self):
        """Initialize the resolver with empty mappings."""
        self._email_to_group_id: Dict[str, str] = {}  # email -> group_id
        self._groups: Dict[str, List[str]] = {}       # group_id -> [emails]
        self._display_names: Dict[str, str] = {}      # group_id -> display_name
        self._loaded = False

    def _load_config(self) -> None:
        """
        Load user group configuration from JSON file.

        Looks for user_alias_mapping.json in the project root directory.
        If the file doesn't exist or is malformed, logs a warning and
        continues with no groupings (graceful degradation).
        """
        if self._loaded:
            return

        # Look for config file in project root (parent of app directory)
        config_path = Path(__file__).parent.parent.parent / "user_alias_mapping.json"

        if not config_path.exists():
            logger.info(f"No user alias mapping file found at {config_path}. "
                       "User grouping disabled.")
            self._loaded = True
            return

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)

            # Validate version
            if config.get("version") != "1.0":
                logger.warning(f"Unknown config version: {config.get('version')}. "
                             "Expected 1.0. Continuing anyway.")

            # Process groups
            groups = config.get("groups", [])
            seen_emails: Set[str] = set()

            for group in groups:
                group_id = group.get("id")
                emails = group.get("emails", [])
                display_name = group.get("display_name", "")

                # Validate group structure
                if not group_id:
                    logger.warning("Skipping group with missing 'id' field")
                    continue

                if not emails:
                    logger.warning(f"Skipping group {group_id} with no emails")
                    continue

                # Check for duplicate emails across groups
                for email in emails:
                    if email in seen_emails:
                        logger.warning(f"Email {email} appears in multiple groups. "
                                     f"Using first occurrence.")
                        continue

                    seen_emails.add(email)
                    self._email_to_group_id[email] = group_id

                # Store group data
                self._groups[group_id] = emails
                self._display_names[group_id] = display_name

            logger.info(f"Loaded {len(self._groups)} user groups from {config_path}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse {config_path}: {e}. "
                        "User grouping disabled.")
        except Exception as e:
            logger.error(f"Error loading user alias mapping: {e}. "
                        "User grouping disabled.")

        self._loaded = True

    def get_group_id(self, email: str) -> str:
        """
        Get the group ID for an email address.

        Args:
            email: The email address to look up

        Returns:
            The group ID if the email is part of a group, otherwise
            the email itself (acting as its own group ID)
        """
        self._load_config()
        return self._email_to_group_id.get(email, email)

    def get_group_emails(self, group_id: str) -> List[str]:
        """
        Get all emails in a group.

        Args:
            group_id: The group identifier

        Returns:
            List of email addresses in the group. If group_id doesn't
            correspond to a group, returns a list containing just the
            group_id itself (treating it as a single-email group)
        """
        self._load_config()
        return self._groups.get(group_id, [group_id])

    def get_display_name(self, group_id: str) -> str:
        """
        Get the display name for a group.

        Args:
            group_id: The group identifier

        Returns:
            The display name if defined, otherwise empty string
        """
        self._load_config()
        return self._display_names.get(group_id, "")

    def consolidate_users(
        self,
        user_sources: Dict[str, Dict[str, bool]]
    ) -> tuple[Dict[str, Dict[str, bool]], Dict[str, List[str]]]:
        """
        Consolidate user sources by grouping associated emails.

        Takes a mapping of individual emails to their source existence and
        merges them by group. For each group, uses OR logic across all
        emails - a source is marked as True if ANY email in the group
        exists in that source.

        Args:
            user_sources: Mapping of {email: {source: exists}}

        Returns:
            Tuple of:
            - Consolidated matrix {group_id: {source: found_in_any_email}}
            - Group details {group_id: [list_of_emails]}
        """
        self._load_config()

        consolidated_matrix: Dict[str, Dict[str, bool]] = {}
        group_details: Dict[str, List[str]] = {}

        for email, sources in user_sources.items():
            group_id = self.get_group_id(email)

            # Initialize group entry if first time seeing this group
            if group_id not in consolidated_matrix:
                consolidated_matrix[group_id] = {}
                group_details[group_id] = []

            # Track all emails in this group (in order encountered)
            if email not in group_details[group_id]:
                group_details[group_id].append(email)

            # OR merge: mark as True if ANY email in group exists in source
            for source_id, exists in sources.items():
                consolidated_matrix[group_id][source_id] = (
                    consolidated_matrix[group_id].get(source_id, False) or exists
                )

        return consolidated_matrix, group_details

    def save_to_file(self) -> None:
        """
        Save current group configuration to the JSON file.

        Writes the current in-memory group mappings back to the
        user_alias_mapping.json file in the project root.
        """
        config_path = Path(__file__).parent.parent.parent / "user_alias_mapping.json"

        # Build config structure
        groups_list = []
        for group_id, emails in self._groups.items():
            groups_list.append({
                "id": group_id,
                "emails": emails,
                "display_name": self._display_names.get(group_id, "")
            })

        config = {
            "version": "1.0",
            "groups": groups_list
        }

        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"Saved {len(groups_list)} groups to {config_path}")
        except Exception as e:
            logger.error(f"Failed to save user alias mapping: {e}")
            raise

    def merge_users(self, emails: List[str], display_name: str = "") -> str:
        """
        Merge multiple email addresses into a single group.

        Args:
            emails: List of email addresses to merge
            display_name: Optional display name for the group

        Returns:
            The group_id of the newly created or updated group
        """
        if len(emails) < 2:
            raise ValueError("Need at least 2 emails to merge")

        # Use first email as the primary one
        primary_email = emails[0]

        # Check if any of these emails are already in groups
        existing_groups = set()
        for email in emails:
            if email in self._email_to_group_id:
                existing_groups.add(self._email_to_group_id[email])

        if existing_groups:
            # Merge into the first existing group
            group_id = list(existing_groups)[0]

            # Add all emails to this group
            for email in emails:
                if email not in self._groups[group_id]:
                    self._groups[group_id].append(email)
                self._email_to_group_id[email] = group_id

            # Update display name if provided
            if display_name:
                self._display_names[group_id] = display_name
        else:
            # Create new group using primary email as group_id
            group_id = primary_email
            self._groups[group_id] = emails
            self._display_names[group_id] = display_name

            # Map all emails to this group
            for email in emails:
                self._email_to_group_id[email] = group_id

        # Save to file
        self.save_to_file()

        return group_id

    def split_users(self, group_id: str, emails_to_keep: List[str]) -> None:
        """
        Split a group by removing specified emails.

        Args:
            group_id: The group to split
            emails_to_keep: List of emails to keep in the group.
                           All other emails will be removed from the group.
        """
        if group_id not in self._groups:
            raise ValueError(f"Group {group_id} not found")

        current_emails = self._groups[group_id]
        emails_to_remove = [e for e in current_emails if e not in emails_to_keep]

        if not emails_to_remove:
            # Nothing to remove
            return

        if not emails_to_keep:
            # Removing all emails - delete the entire group
            for email in current_emails:
                del self._email_to_group_id[email]
            del self._groups[group_id]
            if group_id in self._display_names:
                del self._display_names[group_id]
        else:
            # Update group with only kept emails
            self._groups[group_id] = emails_to_keep

            # Remove mappings for removed emails
            for email in emails_to_remove:
                del self._email_to_group_id[email]

            # If only one email left, consider removing the group
            if len(emails_to_keep) == 1:
                del self._groups[group_id]
                del self._email_to_group_id[emails_to_keep[0]]
                if group_id in self._display_names:
                    del self._display_names[group_id]

        # Save to file
        self.save_to_file()

    def is_grouped(self, email: str) -> bool:
        """
        Check if an email is part of a group (i.e., has associated aliases).

        Args:
            email: The email address to check

        Returns:
            True if the email is part of a group with multiple emails,
            False if it's standalone
        """
        self._load_config()
        group_id = self.get_group_id(email)
        group_emails = self.get_group_emails(group_id)
        return len(group_emails) > 1


# Singleton instance
_resolver_instance: UserGroupResolver = None


def get_user_group_resolver() -> UserGroupResolver:
    """
    Get the singleton UserGroupResolver instance.

    Returns:
        The global UserGroupResolver instance
    """
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = UserGroupResolver()
    return _resolver_instance
