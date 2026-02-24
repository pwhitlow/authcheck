# Okta Connector Setup Guide

This guide explains how to configure the Okta connector for the AuthCheck application using the Okta Python SDK.

## Overview

The Okta connector uses the official Okta Python SDK to interact with your Okta organization. Authentication is handled via Private Key JWT authentication, which is the recommended method for machine-to-machine authentication.

## Prerequisites

1. Access to your Okta Admin Console
2. Permission to create OAuth applications
3. Ability to generate and manage private keys

## Configuration

The Okta connector expects a configuration dictionary with the following structure:

```json
{
    "orgUrl": "https://your-org.okta.com",
    "authorizationMode": "PrivateKey",
    "clientId": "your_client_id",
    "scopes": ["okta.users.read", "okta.users.manage"],
    "privateKey": "your_private_key_content"
}
```

### Configuration Fields

| Field | Description | Required |
|-------|-------------|----------|
| `orgUrl` | Your Okta organization URL (e.g., `https://hudsonalpha.okta.com`) | Yes |
| `authorizationMode` | Authentication mode - use `"PrivateKey"` | Yes |
| `clientId` | OAuth 2.0 Client ID from your Okta application | Yes |
| `scopes` | List of OAuth scopes needed (minimum: `okta.users.read`) | Yes |
| `privateKey` | Private key content for JWT authentication | Yes |

### Required Scopes

For basic user verification:
- `okta.users.read` - Read user information

For full functionality (including user enumeration):
- `okta.users.read`
- `okta.users.manage`

## Setting Up Okta Application

### Step 1: Create OAuth Application

1. Log in to your Okta Admin Console
2. Navigate to **Applications** → **Applications**
3. Click **Create App Integration**
4. Select **API Services** as the application type
5. Click **Next**
6. Enter a name (e.g., "AuthCheck User Verification")
7. Click **Save**

### Step 2: Generate Private Key

1. In your application settings, go to the **General** tab
2. Under **Client Credentials**, click **Edit**
3. Select **Public key / Private key** as the client authentication method
4. Click **Add key**
5. Choose to either:
   - Generate a new key pair (recommended)
   - Upload an existing public key
6. Save the private key securely (you'll need this for configuration)
7. Note the Client ID shown on the page

### Step 3: Grant Required Scopes

1. In your application, go to the **Okta API Scopes** tab
2. Click **Grant** next to:
   - `okta.users.read`
   - `okta.users.manage` (if you want to enumerate all users)
3. Confirm the grants

## Configuration Methods

### Method 1: Configuration File (Recommended for Testing)

Create a configuration file (e.g., `~/.okta_config`):

```json
{
    "orgUrl": "https://your-org.okta.com",
    "authorizationMode": "PrivateKey",
    "clientId": "0oa...",
    "scopes": ["okta.users.read", "okta.users.manage"],
    "privateKey": "-----BEGIN PRIVATE KEY-----\nMIIEvg...\n-----END PRIVATE KEY-----"
}
```

Load it in your application:

```python
import json
from pathlib import Path

with open(Path.home() / ".okta_config", 'r') as f:
    okta_config = json.load(f)

# Pass to connector
connector = OktaConnector(okta_config)
```

### Method 2: Environment Variables + Code

Set environment variables and construct config in code:

```bash
export OKTA_ORG_URL="https://your-org.okta.com"
export OKTA_CLIENT_ID="0oa..."
export OKTA_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."
```

```python
import os

okta_config = {
    "orgUrl": os.getenv("OKTA_ORG_URL"),
    "authorizationMode": "PrivateKey",
    "clientId": os.getenv("OKTA_CLIENT_ID"),
    "scopes": ["okta.users.read", "okta.users.manage"],
    "privateKey": os.getenv("OKTA_PRIVATE_KEY")
}

connector = OktaConnector(okta_config)
```

### Method 3: Direct Configuration

Pass configuration directly when creating connector:

```python
okta_config = {
    "orgUrl": "https://your-org.okta.com",
    "authorizationMode": "PrivateKey",
    "clientId": "your_client_id",
    "scopes": ["okta.users.read"],
    "privateKey": "your_private_key_content"
}

from app.connectors.okta import OktaConnector
connector = OktaConnector(okta_config)
```

## Usage

### Check if User Exists

```python
result = await connector.authenticate_user("user@example.com")
if result:
    print("User exists and is active")
else:
    print("User not found or inactive")
```

### Get All Active Users

```python
users = await connector.get_all_users()
print(f"Found {len(users)} active users")
for username in users:
    print(f"  - {username}")
```

## Username Format

The Okta connector searches for users by their `profile.login` field. This is typically:

- Email address: `user@domain.com`
- Username: `username`

The exact format depends on your Okta configuration. If your organization uses email-style logins, you may need to append the domain:

```python
username = f"{user}@hudsonalpha.org"
result = await connector.authenticate_user(username)
```

## Troubleshooting

### "User not found" for existing users

**Cause**: Username format mismatch

**Solution**: Check the `profile.login` field in Okta for your users. Use the exact format when querying.

### Authentication errors

**Cause**: Invalid private key or client ID

**Solution**:
1. Verify your Client ID is correct
2. Ensure the private key is properly formatted with newlines
3. Check that the application has been granted the required scopes

### Permission errors

**Cause**: Missing OAuth scopes

**Solution**: Grant `okta.users.read` and `okta.users.manage` scopes to your application in Okta Admin Console

## Security Best Practices

1. **Never commit private keys to version control**
2. Store private keys securely (use environment variables or secrets management)
3. Use the minimum required scopes
4. Rotate keys periodically
5. Monitor application access logs in Okta

## Integration with AuthCheck

The connector is already registered in the ConnectorRegistry. To use it:

1. Create your Okta configuration (see above)
2. Pass it to the connector when initializing
3. The connector will be automatically included in verification queries

No code changes needed - just provide the configuration!
