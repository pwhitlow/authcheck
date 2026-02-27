from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Dict, Any, List
import asyncio
import json
import os
from pathlib import Path

from app.connectors import get_registry
from app.utils.alias_resolver import get_user_group_resolver

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
    # Get group information
    resolver = get_user_group_resolver()
    group_id = resolver.get_group_id(username)
    group_emails = resolver.get_group_emails(group_id)
    is_grouped = len(group_emails) > 1
    display_name = resolver.get_display_name(group_id)

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

    # Build email list HTML for split UI
    split_email_list_html = ""
    for i, email in enumerate(group_emails):
        split_email_list_html += f'<div class="email-checkbox"><input type="checkbox" checked value="{email}" id="split-{i}"><label for="split-{i}">{email}</label></div>'

    # Build associated emails list for header
    associated_emails_html = ""
    if is_grouped:
        associated_emails_html = '<div class="email-list"><strong>Associated Emails:</strong>'
        for email in group_emails:
            associated_emails_html += f'<div class="email-item">{email}</div>'
        associated_emails_html += '</div>'

    # Build group badge
    group_badge_html = f'<span class="grouped-badge">GROUPED ({len(group_emails)})</span>' if is_grouped else ''

    # Build action button
    action_button_html = '<button class="btn btn-danger" onclick="showSplitUI()">Split Group</button>' if is_grouped else '<button class="btn btn-primary" onclick="showMergeUI()">Merge with Other Accounts</button>'

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
        .action-buttons {{
            margin: 20px 0;
            display: flex;
            gap: 10px;
        }}
        .btn {{
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s;
        }}
        .btn-primary {{
            background: #0066cc;
            color: white;
        }}
        .btn-primary:hover {{
            background: #0052a3;
        }}
        .btn-danger {{
            background: #dc3545;
            color: white;
        }}
        .btn-danger:hover {{
            background: #c82333;
        }}
        .btn-secondary {{
            background: #6c757d;
            color: white;
        }}
        .btn-secondary:hover {{
            background: #545b62;
        }}
        .merge-container, .split-container {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: none;
        }}
        .merge-container.active, .split-container.active {{
            display: block;
        }}
        .email-checkbox {{
            display: flex;
            align-items: center;
            padding: 10px;
            margin: 5px 0;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        .email-checkbox input {{
            margin-right: 10px;
        }}
        .grouped-badge {{
            background: #17a2b8;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            margin-left: 10px;
        }}
        .email-list {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            margin: 10px 0;
        }}
        .email-item {{
            padding: 8px 0;
            border-bottom: 1px solid #dee2e6;
        }}
        .email-item:last-child {{
            border-bottom: none;
        }}
    </style>
</head>
<body>
    <a href="/" class="back-link">← Back to Verification</a>

    <div class="header">
        <h1>User Details</h1>
        <div class="username">{username} {group_badge_html}</div>
        {associated_emails_html}
    </div>

    <div class="action-buttons">
        {action_button_html}
    </div>

    <!-- Merge UI -->
    <div id="merge-container" class="merge-container">
        <h2>Merge Accounts</h2>
        <p>Select email addresses to merge with <strong>{username}</strong>:</p>
        <div id="merge-email-list"></div>
        <div style="margin-top: 15px;">
            <button class="btn btn-primary" onclick="submitMerge()">Merge Selected</button>
            <button class="btn btn-secondary" onclick="cancelMerge()">Cancel</button>
        </div>
    </div>

    <!-- Split UI -->
    <div id="split-container" class="split-container">
        <h2>Split Group</h2>
        <p>Uncheck emails to remove from this group:</p>
        <div id="split-email-list">
            {split_email_list_html}
        </div>
        <div style="margin-top: 15px;">
            <button class="btn btn-danger" onclick="submitSplit()">Split Group</button>
            <button class="btn btn-secondary" onclick="cancelSplit()">Cancel</button>
        </div>
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

    html_content += f"""
    <script>
        const currentUsername = "{username}";
        const groupId = "{group_id}";
        const isGrouped = {str(is_grouped).lower()};
        let allAvailableEmails = [];

        async function loadAllEmails() {{
            try {{
                const response = await fetch('/compare');
                const data = await response.json();
                allAvailableEmails = data.all_users.filter(u => u !== currentUsername);
                return allAvailableEmails;
            }} catch (error) {{
                console.error('Error loading emails:', error);
                return [];
            }}
        }}

        async function showMergeUI() {{
            const container = document.getElementById('merge-container');
            const emailList = document.getElementById('merge-email-list');

            // Load all available emails
            const emails = await loadAllEmails();

            // Build checkbox list
            emailList.innerHTML = '<div class="email-checkbox"><input type="checkbox" checked disabled value="' + currentUsername + '"><label>' + currentUsername + ' (Current)</label></div>';

            emails.forEach((email, i) => {{
                emailList.innerHTML += '<div class="email-checkbox"><input type="checkbox" value="' + email + '" id="merge-' + i + '"><label for="merge-' + i + '">' + email + '</label></div>';
            }});

            container.classList.add('active');
        }}

        function cancelMerge() {{
            document.getElementById('merge-container').classList.remove('active');
        }}

        async function submitMerge() {{
            const checkboxes = document.querySelectorAll('#merge-email-list input[type="checkbox"]:checked');
            const selectedEmails = Array.from(checkboxes).map(cb => cb.value);

            if (selectedEmails.length < 2) {{
                alert('Please select at least one email to merge with ' + currentUsername);
                return;
            }}

            try {{
                const response = await fetch('/api/users/merge', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{
                        emails: selectedEmails,
                        display_name: ""
                    }})
                }});

                const result = await response.json();

                if (result.success) {{
                    alert('Successfully merged accounts!');
                    window.location.reload();
                }} else {{
                    alert('Error merging accounts: ' + result.message);
                }}
            }} catch (error) {{
                alert('Error: ' + error.message);
            }}
        }}

        function showSplitUI() {{
            document.getElementById('split-container').classList.add('active');
        }}

        function cancelSplit() {{
            document.getElementById('split-container').classList.remove('active');
        }}

        async function submitSplit() {{
            const checkboxes = document.querySelectorAll('#split-email-list input[type="checkbox"]:checked');
            const emailsToKeep = Array.from(checkboxes).map(cb => cb.value);

            if (emailsToKeep.length === 0) {{
                if (!confirm('This will delete the entire group. Are you sure?')) {{
                    return;
                }}
            }}

            try {{
                const response = await fetch('/api/users/split', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{
                        group_id: groupId,
                        emails_to_keep: emailsToKeep
                    }})
                }});

                const result = await response.json();

                if (result.success) {{
                    alert('Successfully split group!');
                    window.location.reload();
                }} else {{
                    alert('Error splitting group: ' + result.message);
                }}
            }} catch (error) {{
                alert('Error: ' + error.message);
            }}
        }}

        // Hide split UI by default if not grouped
        if (!isGrouped) {{
            document.getElementById('split-container').classList.remove('active');
        }}
    </script>
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


# Pydantic models for merge/split requests
class MergeRequest(BaseModel):
    emails: List[str]
    display_name: str = ""


class SplitRequest(BaseModel):
    group_id: str
    emails_to_keep: List[str]


class GroupInfoResponse(BaseModel):
    is_grouped: bool
    group_id: str
    emails: List[str]
    display_name: str


@router.get("/api/user/{email}/group-info")
async def get_user_group_info(email: str) -> GroupInfoResponse:
    """
    Get group information for a specific email address.

    Args:
        email: The email address to check

    Returns:
        Group information including whether the email is grouped,
        group ID, all associated emails, and display name
    """
    resolver = get_user_group_resolver()
    group_id = resolver.get_group_id(email)
    emails = resolver.get_group_emails(group_id)
    display_name = resolver.get_display_name(group_id)
    is_grouped = len(emails) > 1

    return GroupInfoResponse(
        is_grouped=is_grouped,
        group_id=group_id,
        emails=emails,
        display_name=display_name
    )


@router.post("/api/users/merge")
async def merge_users(request: MergeRequest):
    """
    Merge multiple email addresses into a single group.

    Args:
        request: MergeRequest with emails to merge and optional display name

    Returns:
        Success message with the group_id
    """
    resolver = get_user_group_resolver()

    try:
        group_id = resolver.merge_users(request.emails, request.display_name)
        return {
            "success": True,
            "message": f"Successfully merged {len(request.emails)} emails",
            "group_id": group_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/users/split")
async def split_users(request: SplitRequest):
    """
    Split a group by removing specified emails.

    Args:
        request: SplitRequest with group_id and emails to keep

    Returns:
        Success message
    """
    resolver = get_user_group_resolver()

    try:
        resolver.split_users(request.group_id, request.emails_to_keep)
        return {
            "success": True,
            "message": f"Successfully split group"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
