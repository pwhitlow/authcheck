import asyncio
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from app.models import VerificationResults
from app.connectors import get_registry

router = APIRouter()


class VerifyRequest(BaseModel):
    users: List[str]


@router.post("/verify")
async def verify_users(request: VerifyRequest) -> VerificationResults:
    """
    Query all available connectors to verify user existence.

    Args:
        request: List of usernames to verify

    Returns:
        Grid data with results from all auth sources
    """
    if not request.users:
        raise HTTPException(status_code=400, detail="No users provided")

    registry = get_registry()
    connectors = registry.get_all_connectors()

    if not connectors:
        raise HTTPException(status_code=500, detail="No connectors available")

    # Build results dictionary
    results = {}

    # For each user, query all connectors in parallel
    for username in request.users:
        user_results = {}

        # Create tasks for all connectors for this user
        tasks = [
            connector.authenticate_user(username) for connector in connectors
        ]

        # Run all queries in parallel
        query_results = await asyncio.gather(*tasks)

        # Map results back to connector IDs
        for connector, result in zip(connectors, query_results):
            user_results[connector.get_connector_id()] = result

        results[username] = user_results

    # Get list of connector IDs for response
    source_ids = [connector.get_connector_id() for connector in connectors]

    return VerificationResults(
        users=request.users,
        sources=source_ids,
        results=results,
        timestamp=datetime.now(),
    )
