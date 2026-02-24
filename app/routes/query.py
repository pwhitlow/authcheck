import asyncio
import json
from typing import List
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from app.models import VerificationResults
from app.connectors import get_registry

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

    # Load connector configurations
    connector_config = load_connector_config()

    registry = get_registry()
    connectors = registry.get_all_connectors(connector_config)

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
