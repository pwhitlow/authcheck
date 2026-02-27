import asyncio
import json
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, List, Set
from app.connectors import get_registry
from app.utils.alias_resolver import get_user_group_resolver

router = APIRouter()


def load_connector_config():
    """Load connector configurations from files."""
    config = {}

    # Try to load Okta config from ~/.okta_config
    okta_config_path = Path.home() / ".okta_config"
    if okta_config_path.exists():
        try:
            with open(okta_config_path, 'r') as f:
                config['okta'] = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load Okta config: {e}")

    return config


class ComparisonResult(BaseModel):
    """Results from comparing users across all sources."""

    all_users: List[str]  # Combined list of all unique users (may be group IDs)
    sources: List[str]  # List of source names that support enumeration
    user_sources: Dict[str, Dict[str, bool]]  # {group_id: {source_id: found}}
    source_counts: Dict[str, int]  # {source_id: user_count}
    user_roles: Dict[str, str]  # {group_id: okta_role or "n/a"}
    user_groups: Dict[str, List[str]]  # {group_id: [list_of_emails]}
    timestamp: datetime


@router.get("/compare")
async def compare_users() -> ComparisonResult:
    """
    Compare users across all available data sources.

    Gets list of all users from each source that supports enumeration,
    then compares them to show which users exist in which systems.

    Returns:
        Grid data showing which users are in which sources
    """
    # Load connector configurations
    connector_config = load_connector_config()

    registry = get_registry()
    connectors = registry.get_all_connectors(connector_config)

    all_users_set: Set[str] = set()
    source_users: Dict[str, Set[str]] = {}
    sources_with_data = []

    # Get users from each connector that supports enumeration
    tasks = []
    connector_info = []

    for connector in connectors:
        connector_id = connector.get_connector_id()
        connector_info.append((connector_id, connector.get_display_name(), connector))
        tasks.append(connector.get_all_users())

    # Run all queries in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    for (connector_id, display_name, connector), result in zip(
        connector_info, results
    ):
        if isinstance(result, Exception):
            # Connector doesn't support enumeration or failed
            continue

        # This connector supports enumeration
        sources_with_data.append(connector_id)
        user_set = set(result)
        source_users[connector_id] = user_set
        all_users_set.update(user_set)

    # Build comparison matrix
    user_sources_matrix = {}
    for username in sorted(all_users_set, key=str.lower):
        user_sources_matrix[username] = {}
        for connector_id in sources_with_data:
            user_sources_matrix[username][connector_id] = (
                username in source_users[connector_id]
            )

    # Apply alias grouping/consolidation
    resolver = get_user_group_resolver()
    consolidated_matrix, group_details = resolver.consolidate_users(user_sources_matrix)

    # Update all_users_set to group IDs and use consolidated matrix
    all_users_set = set(consolidated_matrix.keys())
    user_sources_matrix = consolidated_matrix

    # Count users per source (based on consolidated groups)
    source_counts = {}
    for connector_id in sources_with_data:
        count = sum(1 for group_data in consolidated_matrix.values()
                   if group_data.get(connector_id, False))
        source_counts[connector_id] = count

    # Get Okta roles for all users (optimized batch fetch)
    user_roles = {}
    okta_connector = None
    for connector_id, display_name, connector in connector_info:
        if connector_id == "okta":
            okta_connector = connector
            break

    if okta_connector:
        try:
            # Fetch all users with details in one batch operation
            # This is much faster than calling get_user_details() for each user
            all_user_details = await okta_connector.get_all_users_with_details(include_groups=False)

            # Extract roles from the batch results
            # For groups, use role from first email in group that has a role
            for group_id in all_users_set:
                group_emails = resolver.get_group_emails(group_id)
                role_found = False

                # Try each email in group until we find a role
                for email in group_emails:
                    if email in all_user_details and "user_role" in all_user_details[email]:
                        user_roles[group_id] = all_user_details[email]["user_role"]
                        role_found = True
                        break

                if not role_found:
                    user_roles[group_id] = "n/a"
        except Exception:
            # If batch fetch fails, fall back to n/a for all users
            for group_id in all_users_set:
                user_roles[group_id] = "n/a"
    else:
        # No Okta connector available
        for group_id in all_users_set:
            user_roles[group_id] = "n/a"

    return ComparisonResult(
        all_users=sorted(list(all_users_set), key=str.lower),
        sources=sources_with_data,
        user_sources=user_sources_matrix,
        source_counts=source_counts,
        user_roles=user_roles,
        user_groups=group_details,
        timestamp=datetime.now(),
    )
