# Okta OAuth2 Setup Guide

This guide walks you through configuring OAuth2 for AuthCheck when API tokens don't work.

## Why OAuth2?

Some Okta organizations have restrictions on API token access. OAuth2 with service apps is often more reliable and is actually more secure for production use.

## Step-by-Step Configuration

### Step 1: Create Application Integration

In Okta Admin Console:

1. Go to **Applications** → **Applications** (left sidebar)
2. Click **Create App Integration** button (top right)
3. In the dialog that appears:
   - **Sign-in method**: Select **API Services**
   - Click **Create**

### Step 2: Configure the App

1. **General Settings Tab**
   - App name: `AuthCheck API` (or any name)
   - Logo: (optional)
   - Click **Save**

2. **Go to the General tab** (should be default)
   - You'll see:
     - **Client ID** (looks like: `0oa123abc...`)
     - **Client Secret** (looks like: `abc123...`)
   - **Copy both values** - you'll need them shortly

### Step 3: Configure Scopes

1. **Still in the General tab, scroll down**
2. Look for **Grant types** section
   - Make sure **Client Credentials** is checked ✓
   - This allows the service app to authenticate

3. Look for **Scopes** section
   - You should see available scopes
   - Enable/check: **`okta.users.read`**
   - This gives permission to read user information
   - Click to select it

4. Click **Save** or **Update** to apply changes

### Step 4: Verify Configuration

1. **Go to Security** → **API** → **Tokens**
   - The app you created should show up as an "API Service" (not a Token)
   - Status should show as "Active"

2. **Your app should have:**
   - ✅ Client ID
   - ✅ Client Secret
   - ✅ Client Credentials grant type
   - ✅ `okta.users.read` scope enabled

## Step 5: Update .env File

Create or update `.env` file in your AuthCheck directory:

```bash
OKTA_ORG_URL=https://hudsonalpha.okta.com
OKTA_CLIENT_ID=your_client_id_here
OKTA_CLIENT_SECRET=your_client_secret_here
```

Replace:
- `your_client_id_here` with the Client ID from the app
- `your_client_secret_here` with the Client Secret from the app

## Step 6: Test Connection

```bash
python3 test_okta.py
```

Expected output:
```
============================================================
OKTA CONNECTION TEST
============================================================

📋 Configuration Check:
  OKTA_ORG_URL: https://hudsonalpha.okta.com
  OKTA_CLIENT_ID: ✓ SET (25 chars)
  OKTA_CLIENT_SECRET: ✓ SET (40 chars)

  Auth Method: OAuth2

✅ Configuration looks good!

🔐 Validating Okta configuration...
✅ Configuration valid

📊 Fetching all active users from Okta...

✅ Successfully fetched 42 active users from Okta!

📝 Sample users (first 10):
    1. user1@example.com
    2. user2@example.com
    ...

============================================================
✅ CONNECTION SUCCESSFUL!
============================================================
```

## How OAuth2 Works

When you click "Compare All Users":

```
1. AuthCheck loads Client ID and Secret from .env
   ↓
2. Requests access token from:
   POST https://hudsonalpha.okta.com/oauth2/v1/token
   With: grant_type=client_credentials, scope=okta.users.read
   ↓
3. Okta returns access token (valid for 1 hour)
   ↓
4. AuthCheck uses token to query users:
   GET /api/v1/users with Bearer token
   ↓
5. Okta returns list of users
```

The token is cached and reused for 1 hour, so you don't request a new one every time.

## Troubleshooting

### Error: "Failed to get access token"

**Cause**: Credentials are wrong or app not configured correctly

**Fix**:
1. Verify Client ID and Secret are copied exactly (no spaces)
2. Make sure "Client Credentials" grant type is enabled
3. Make sure `okta.users.read` scope is enabled
4. Check that app status is "Active"

### Error: "Insufficient permissions"

**Cause**: App doesn't have the right scope

**Fix**:
1. Go to app configuration
2. Enable `okta.users.read` scope (under Scopes section)
3. Save changes
4. Test again

### Still getting "Invalid token" or 401 errors?

**Try these steps**:
1. Delete the app entirely
2. Create a brand new one from scratch
3. Copy credentials fresh from the creation popup
4. Update .env immediately
5. Test within 1 minute of creation

## Security Best Practices

1. **Never share credentials**
   - Client Secret should be treated like a password
   - Don't commit .env to git (it's in .gitignore)

2. **Rotate credentials regularly**
   - Delete old app when creating new one
   - Update .env with new credentials

3. **Monitor usage**
   - Check System Log for API access from your app
   - Look for suspicious activity

4. **In production**
   - Use secure secrets management (AWS Secrets Manager, HashiCorp Vault, etc.)
   - Don't store credentials in .env files
   - Use IAM roles or workload identity if possible

## FAQ

**Q: Why OAuth2 instead of API tokens?**
A: Some Okta orgs have restrictions on API token access for security reasons. OAuth2 is actually more secure and is the recommended approach for service-to-service communication.

**Q: Do I need to refresh the token?**
A: No, AuthCheck handles it automatically. The token is cached and refreshed as needed.

**Q: What if I want to use API tokens instead?**
A: You can! Just configure `OKTA_API_TOKEN` instead of OAuth2. AuthCheck supports both.

**Q: Can multiple apps use the same credentials?**
A: Yes, but it's better practice to create one per application for better auditing.

**Q: What happens if the Client Secret is compromised?**
A: Delete the app immediately and create a new one. The compromised Secret becomes useless.

## Next Steps

1. Create the OAuth2 app in Okta
2. Get Client ID and Secret
3. Update .env file
4. Run `python3 test_okta.py`
5. Run `./run.sh` to start AuthCheck
6. Click "Compare All Users"
7. See your Okta users!

## Additional Resources

- [Okta OAuth2 API Tokens](https://developer.okta.com/docs/guides/implement-oauth2/client-credentials/main/)
- [Service App Documentation](https://developer.okta.com/docs/concepts/api-overview/)
- [Scopes and Permissions](https://developer.okta.com/docs/reference/api/scopes/)
