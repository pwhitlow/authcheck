from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, List
import asyncio
import json
import os
from pathlib import Path

from app.connectors import get_registry

router = APIRouter()

# Set up templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def load_connector_config() -> Dict[str, Any]:
    """Load connector configuration from environment and config files."""
    connector_config = {}

    # Load Okta configuration from ~/.okta_config if it exists
    okta_config_path = os.path.expanduser("~/.okta_config")
    if os.path.exists(okta_config_path):
        try:
            with open(okta_config_path, "r") as f:
                connector_config["okta"] = json.load(f)
        except Exception:
            pass

    return connector_config


@router.get("/user/{username}", response_class=HTMLResponse)
async def get_user_details(username: str):
    """
    Get detailed information about a specific user from all connectors.

    Args:
        username: Email/username to look up

    Returns:
        HTML page with user details from all sources
    """
    registry = get_registry()
    connector_config = load_connector_config()
    connectors = registry.get_all_connectors(connector_config)

    # Query all connectors in parallel for this user's details
    tasks = [connector.get_user_details(username) for connector in connectors]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Compile user details from all sources
    user_data = {
        "username": username,
        "sources": {}
    }

    for connector, result in zip(connectors, results):
        connector_id = connector.get_connector_id()
        connector_name = connector.get_display_name()

        # Skip connectors that are not implemented or not configured
        if isinstance(result, Exception):
            # Skip NotImplementedError (connector stubs) and configuration errors
            if isinstance(result, (NotImplementedError, ValueError)):
                continue
            # For other exceptions, you could optionally show an error or skip
            continue
        elif result:
            # Connector returned data - show it
            user_data["sources"][connector_id] = {
                "name": connector_name,
                "found": True,
                "details": result
            }
        else:
            # Connector returned None (user not found) - show "Not Found"
            user_data["sources"][connector_id] = {
                "name": connector_name,
                "found": False
            }

    # Build HTML response
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>User Details - {username}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            max-width: 1200px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            margin: 0 0 10px 0;
            color: #333;
        }}
        .username {{
            color: #666;
            font-size: 18px;
        }}
        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            color: #0066cc;
            text-decoration: none;
        }}
        .back-link:hover {{
            text-decoration: underline;
        }}
        .connector-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .connector-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
        }}
        .connector-name {{
            font-size: 20px;
            font-weight: 600;
            color: #333;
        }}
        .status-badge {{
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 500;
        }}
        .status-found {{
            background: #d4edda;
            color: #155724;
        }}
        .status-not-found {{
            background: #f8d7da;
            color: #721c24;
        }}
        .details-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }}
        .detail-item {{
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        .detail-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 4px;
        }}
        .detail-value {{
            font-size: 14px;
            color: #333;
            font-weight: 500;
        }}
        .no-details {{
            color: #666;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <a href="/" class="back-link">← Back to Verification</a>

    <div class="header">
        <h1>User Details</h1>
        <div class="username">{username}</div>
    </div>
"""

    # Add connector cards
    for connector_id, source_data in user_data["sources"].items():
        status_class = "status-found" if source_data["found"] else "status-not-found"
        status_text = "Found" if source_data["found"] else "Not Found"

        html_content += f"""
    <div class="connector-card">
        <div class="connector-header">
            <div class="connector-name">{source_data["name"]}</div>
            <div class="status-badge {status_class}">{status_text}</div>
        </div>
"""

        if source_data["found"] and "details" in source_data:
            details = source_data["details"]
            html_content += '        <div class="details-grid">\n'

            for key, value in details.items():
                if value and key not in ["exists", "username", "source", "user_role_code"]:
                    # Format the label
                    label = key.replace('_', ' ').title()
                    html_content += f"""
            <div class="detail-item">
                <div class="detail-label">{label}</div>
                <div class="detail-value">{value}</div>
            </div>
"""

            html_content += '        </div>\n'
        else:
            html_content += '        <div class="no-details">No additional details available</div>\n'

        html_content += '    </div>\n'

    html_content += """
</body>
</html>
"""

    return HTMLResponse(content=html_content)


@router.get("/api/users/all")
async def get_all_users():
    """
    Get all unique users across all connectors with their details.

    Returns:
        JSON with list of all users and their aggregated details
    """
    registry = get_registry()
    connector_config = load_connector_config()
    connectors = registry.get_all_connectors(connector_config)

    # Get all users from all connectors
    all_usernames = set()

    for connector in connectors:
        try:
            users = await connector.get_all_users()
            all_usernames.update(users)
        except NotImplementedError:
            # Connector doesn't support enumeration, skip it
            continue
        except Exception:
            # Error getting users, skip this connector
            continue

    # Get details for each unique user
    user_records = []

    for username in sorted(all_usernames):
        tasks = [connector.get_user_details(username) for connector in connectors]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate details from all sources
        user_record = {"username": username, "sources": {}}

        for connector, result in zip(connectors, results):
            connector_id = connector.get_connector_id()

            if isinstance(result, Exception):
                user_record["sources"][connector_id] = {"found": False}
            elif result:
                user_record["sources"][connector_id] = {"found": True, "details": result}
            else:
                user_record["sources"][connector_id] = {"found": False}

        user_records.append(user_record)

    return {
        "total_users": len(user_records),
        "users": user_records
    }
