# Okta Integration Setup Guide

This guide explains how to set up real Okta integration for AuthCheck.

## Prerequisites

- Okta organization (https://yourorg.okta.com)
- Admin access to Okta to create API tokens
- AuthCheck application running locally or on a server

## Step 1: Create Okta API Token

1. Log in to your Okta admin console
2. Navigate to: **Security** → **API** → **Tokens**
3. Click **Create Token**
4. Enter a name: `authcheck-api`
5. Click **Create Token**
6. **Copy the token value** (you won't be able to see it again!)

## Step 2: Get Your Organization URL

Your Okta organization URL is displayed in the Okta admin console:
- Format: `https://yourorgname.okta.com`
- Or if using custom domain: `https://yourdomain.example.com`

## Step 3: Configure AuthCheck

### Option A: Environment Variables (Recommended)

Create a `.env` file in the project root:

```env
# Okta Configuration
OKTA_ORG_URL=https://yourorg.okta.com
OKTA_API_TOKEN=your_api_token_here
```

### Option B: Configuration Dictionary

Pass configuration when initializing the app:

```python
from app.connectors import get_registry

config = {
    "okta": {
        "org_url": "https://yourorg.okta.com",
        "api_token": "your_api_token_here",
        "timeout": 10  # Optional: request timeout in seconds
    }
}

registry = get_registry()
okta_connector = registry.get_connector("okta", config.get("okta"))
```

## Step 4: Test the Integration

### Test via Python REPL

```python
import asyncio
from app.connectors import get_registry
import os

# Set environment variables first
os.environ["OKTA_ORG_URL"] = "https://yourorg.okta.com"
os.environ["OKTA_API_TOKEN"] = "your_api_token"

async def test():
    registry = get_registry()
    okta = registry.get_connector("okta")

    # Test with a known user
    result = await okta.authenticate_user("john.doe@example.com")
    print(f"User found: {result}")

asyncio.run(test())
```

### Test via AuthCheck UI

1. Start the dev server: `./run.sh`
2. Open http://localhost:8000
3. Upload a CSV with usernames
4. Click "Verify Users"
5. Check the Okta column for results

### Test via cURL

```bash
# Get Okta users
curl -X GET "https://yourorg.okta.com/api/v1/users?filter=status%20eq%20%22ACTIVE%22" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Accept: application/json"

# Search for specific user
curl -X GET 'https://yourorg.okta.com/api/v1/users?filter=profile.login%20eq%20%22john.doe@example.com%22' \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Accept: application/json"
```

## Step 5: Verify Configuration

The connector will automatically validate configuration on first use:

```python
okta = registry.get_connector("okta")

if okta.validate_config():
    print("✅ Okta configuration is valid")
else:
    print("❌ Okta configuration is missing or invalid")
```

## API Reference

### User Search Filters

Okta supports various filters for user searches:

```
# Search by email/login
filter=profile.login eq "john.doe@example.com"

# Search by username
filter=profile.userName eq "john.doe"

# Search by first name
filter=profile.firstName eq "John"

# Combine filters
filter=profile.firstName eq "John" AND profile.lastName eq "Doe"

# Last login date
filter=lastLogin gt "2024-01-01T00:00:00.000Z"

# Account status
filter=status eq "ACTIVE"
filter=status eq "PROVISIONED"
filter=status eq "STAGED"
filter=status eq "DEPROVISIONED"
```

## User Status Values

- `STAGED` - User created but hasn't activated
- `PROVISIONED` - User created and waiting activation
- `ACTIVE` - User is active and can authenticate
- `RECOVERY` - User account locked
- `LOCKED_OUT` - User account temporarily locked
- `PASSWORD_EXPIRED` - User password has expired
- `SUSPENDED` - Administrator suspended the account
- `DEPROVISIONED` - User account has been deprovisioned

The connector only returns `True` for `ACTIVE` status users.

## Troubleshooting

### "Invalid API token"

- Verify token is correct (copy from Okta admin console again)
- Check token hasn't expired
- Verify API permissions in Okta:
  - Security → API → Trusted Origins (add your server URL)
  - Admin role must have API access

### "Insufficient permissions"

- Verify your API token's permissions
- In Okta admin: **Security** → **API** → **Tokens**
- Check the scope/permissions assigned to the token
- May need admin access to create proper token

### Request timeout

- Increase timeout in configuration: `"timeout": 30`
- Check network connectivity to Okta
- Okta may be rate limiting - add retry logic

### User not found

- Verify username format matches Okta's `profile.login` field
- Usually this is the email address
- May also be just the username without domain

### Connection refused

- Verify org URL is correct (check Okta admin console)
- Ensure HTTPS is used (not HTTP)
- Check firewall/network access to Okta

## Security Best Practices

1. **Never commit `.env` file**
   - Add to `.gitignore` (already done)
   - Use environment variables in production

2. **API Token Security**
   - Treat like a password
   - Rotate regularly
   - Use service account user for API token
   - Delete tokens when no longer needed

3. **Rate Limiting**
   - Okta free tier: 10,000 API requests/min
   - Okta professional: 30,000 API requests/min
   - Consider caching for large user lists

4. **Logging**
   - Never log full API tokens
   - Log only masked version (first 4 chars)
   - Store logs securely

## Advanced Configuration

### Custom Request Timeout

```python
config = {
    "okta": {
        "org_url": "https://yourorg.okta.com",
        "api_token": "your_token",
        "timeout": 30  # 30 seconds instead of default 10
    }
}
```

### Batch User Verification

For large user lists, consider implementing batch verification:

```python
import asyncio

async def verify_users_batch(usernames, connector, batch_size=10):
    """Verify users in batches to manage load."""
    results = {}

    for i in range(0, len(usernames), batch_size):
        batch = usernames[i:i + batch_size]
        tasks = [connector.authenticate_user(user) for user in batch]
        batch_results = await asyncio.gather(*tasks)

        for user, result in zip(batch, batch_results):
            results[user] = result

    return results
```

## Monitoring & Debugging

### Enable Request Logging

```python
import httpx
import logging

# Enable httpx debug logging
logging.basicConfig(level=logging.DEBUG)
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.DEBUG)
```

### Check Okta API Response

```python
# In okta.py, temporarily modify to log responses:
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

## Integration with AuthCheck

The Okta connector is automatically integrated into AuthCheck:

1. When AuthCheck starts, it loads all connectors including Okta
2. When you click "Verify Users", Okta is queried along with other sources
3. Results are aggregated and displayed in the grid

### View Results

The results grid shows:
- ✓ (green) - User is ACTIVE in Okta
- ✗ (red) - User not found or not ACTIVE in Okta
- Error message if API fails

## Next Steps

1. Get API token from Okta
2. Set environment variables
3. Test integration locally
4. Deploy to production with HTTPS
5. Monitor API usage in Okta dashboard

## Additional Resources

- [Okta API Documentation](https://developer.okta.com/docs/api/)
- [Okta Users API Reference](https://developer.okta.com/docs/api/openapi/okta-management/management/tag/User/)
- [Okta Admin Console](https://developer.okta.com/docs/guides/okta-admin-console/)
- [API Token Authentication](https://developer.okta.com/docs/guides/create-an-api-token/)
