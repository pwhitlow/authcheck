from typing import List
import csv
import os
from .base import BaseConnector


class ADPConnector(BaseConnector):
    """ADP employee data connector - reads from CSV file."""

    def __init__(self, config: dict = None):
        """
        Initialize ADP connector.

        Config can specify csv_path, defaults to slack_employees.csv
        """
        super().__init__(config)
        self.csv_path = self.config.get('csv_path', 'slack_employees.csv')
        self._users_cache = None

    def _load_users(self) -> set:
        """Load users from CSV file and cache them."""
        if self._users_cache is not None:
            return self._users_cache

        users = set()
        csv_path = os.path.join(os.path.dirname(__file__), '..', '..', self.csv_path)

        if not os.path.exists(csv_path):
            # Return empty set if file doesn't exist
            self._users_cache = users
            return users

        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    first = row.get(' FirstName', '').strip()
                    last = row.get('LastName', '').strip()

                    if first and last:
                        # Create email in firstinitiallastname@hudsonalpha.org format
                        email = f"{first[0].lower()}{last.lower()}@hudsonalpha.org"
                        users.add(email)
        except Exception:
            # If error reading file, return empty set
            pass

        self._users_cache = users
        return users

    async def authenticate_user(self, username: str) -> bool:
        """
        Check if user exists in ADP employee list.

        Args:
            username: Username/email to search for

        Returns:
            True if user exists in ADP data, False otherwise
        """
        users = self._load_users()
        return username.lower() in users

    async def get_all_users(self) -> List[str]:
        """
        Get list of all users from ADP CSV.

        Returns:
            List of usernames (email addresses)
        """
        users = self._load_users()
        return sorted(list(users))

    def get_display_name(self) -> str:
        """Get human-readable name for this connector."""
        return "ADP"

    def get_connector_id(self) -> str:
        """Get unique identifier for this connector."""
        return "adp"

    def validate_config(self) -> bool:
        """Validate that CSV file exists."""
        csv_path = os.path.join(os.path.dirname(__file__), '..', '..', self.csv_path)
        return os.path.exists(csv_path)
