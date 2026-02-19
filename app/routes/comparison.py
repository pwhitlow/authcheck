import asyncio
from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, List, Set
from app.connectors import get_registry

router = APIRouter()


class ComparisonResult(BaseModel):
    """Results from comparing users across all sources."""

    all_users: List[str]  # Combined list of all unique users
    sources: List[str]  # List of source names that support enumeration
    user_sources: Dict[str, Dict[str, bool]]  # {username: {source_id: found}}
    source_counts: Dict[str, int]  # {source_id: user_count}
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
    registry = get_registry()
    connectors = registry.get_all_connectors()

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
    for username in sorted(all_users_set):
        user_sources_matrix[username] = {}
        for connector_id in sources_with_data:
            user_sources_matrix[username][connector_id] = (
                username in source_users[connector_id]
            )

    # Count users per source
    source_counts = {
        connector_id: len(source_users[connector_id])
        for connector_id in sources_with_data
    }

    return ComparisonResult(
        all_users=sorted(list(all_users_set)),
        sources=sources_with_data,
        user_sources=user_sources_matrix,
        source_counts=source_counts,
        timestamp=datetime.now(),
    )
