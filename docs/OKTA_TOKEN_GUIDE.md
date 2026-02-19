# Okta API Token - Step-by-Step Guide

This guide walks you through getting your Okta API token with screenshots descriptions.

## Prerequisites

- Okta admin account access
- Your Okta organization (dev or production)

## Step 1: Access Okta Admin Console

### Option A: Developer Account

1. Go to https://developer.okta.com
2. Sign in with your developer account
3. You should already have an org set up

### Option B: Company Okta Instance

1. Ask your IT/Okta administrator for the Okta URL
2. Usually format: `https://company.okta.com` or `https://company-dev.okta.com`
3. Sign in with your admin credentials

## Step 2: Navigate to API Tokens

### Method 1: Via Settings (Recommended)

1. **Click your profile icon** (top right corner)
   - You'll see a circular icon with your initials
   - Look in the far top right

2. **Select "Settings"**
   - A dropdown menu appears
   - Click the gear icon or "Settings"

3. **You're now in Settings**
   - Left sidebar shows options
   - Look for "Security" section

### Method 2: Via Admin Menu

1. **In Admin Console, look for menu**
   - Top left: Hamburger menu or "Admin"
   - Click to expand

2. **Navigate to Security → API**
   - Left sidebar: Security → API → Tokens

## Step 3: Find the Tokens Page

Once in the right place, you should see:

```
┌─────────────────────────────────┐
│  Okta Admin Console             │
├─────────────────────────────────┤
│ Security                        │
│   ├─ API                        │
│   │   ├─ Tokens                 │ ← Click here
│   │   └─ Authorization Servers  │
│   ├─ Authentication             │
│   └─ ...                        │
└─────────────────────────────────┘
```

### What You Should See

The Tokens page shows:
- List of existing tokens
- "Create Token" button
- Token expiration info

## Step 4: Create a New Token

1. **Click "Create Token" button** (top right of page)

2. **Give it a name**
   ```
   Token Name: authcheck-api
   ```
   (You can use any name, this is for your reference)

3. **Click "Create Token"**

4. **IMPORTANT: Copy the token immediately!**
   - The token appears in a modal/alert
   - It looks like: `00abcDEF1234567890ghijklmNOPQRS_tuvwxyz`
   - Copy it now - **You won't see it again!**
   - Paste it somewhere safe (text editor, password manager, etc.)

### What the Modal Looks Like

```
┌────────────────────────────────────┐
│      Token Created                 │
├────────────────────────────────────┤
│                                    │
│  Make sure to copy your token now  │
│  You won't be able to see it again │
│                                    │
│  Token:                            │
│  00abcDEF1234567890ghijklmNOPQRS_ │
│  tuvwxyz                           │
│                                    │
│  [Copy]  [Close]                   │
│                                    │
└────────────────────────────────────┘
```

## Step 5: Get Your Organization URL

Your Okta org URL is in the browser:

```
https://dev-12345678.okta.com/admin/dashboard
     ↑                       ↑
     Your org URL (everything before /admin)

Extract: https://dev-12345678.okta.com
```

### Alternative Ways to Find It

1. **Check settings**
   - Account settings often show org URL

2. **Ask admin**
   - IT/Okta team knows the exact URL

3. **Check any Okta emails**
   - Usually contain the org URL

## Step 6: Configure AuthCheck

Now you have:
- ✅ Organization URL: `https://dev-12345678.okta.com`
- ✅ API Token: `00abcDEF1234567890ghijklmNOPQRS_tuvwxyz`

### Create .env File

In the AuthCheck directory, create a file named `.env`:

```bash
# Copy this into a text editor and save as .env in the authcheck directory

OKTA_ORG_URL=https://dev-12345678.okta.com
OKTA_API_TOKEN=00abcDEF1234567890ghijklmNOPQRS_tuvwxyz
```

**DO NOT:**
- Commit this to git (it's already in .gitignore)
- Share this file
- Post the token online
- Leave it in version control

### Verify the File

```bash
# Check that .env file exists
ls -la .env

# Check contents (shows masked token)
cat .env
```

## Step 7: Test the Connection

Use the test script to verify everything works:

```bash
# Make test script executable
chmod +x test_okta.py

# Run the test
python3 test_okta.py
```

### Successful Output

```
============================================================
OKTA CONNECTION TEST
============================================================

📋 Configuration Check:
  OKTA_ORG_URL: https://dev-12345678.okta.com
  OKTA_API_TOKEN: ✓ SET (40 chars)

✅ Configuration looks good!

🔐 Validating Okta configuration...
✅ Configuration valid

📊 Fetching all active users from Okta...
   (This may take a minute for large organizations)

✅ Successfully fetched 42 active users from Okta!

📝 Sample users (first 10):
    1. john.doe@example.com
    2. jane.smith@example.com
    3. bob.wilson@example.com
    ...

============================================================
✅ CONNECTION SUCCESSFUL!
============================================================
```

### Troubleshooting

**If you see: "Configuration validation failed"**
- Check OKTA_ORG_URL format (should be `https://...`)
- Verify OKTA_API_TOKEN is not empty

**If you see: "401 Unauthorized"**
- Check token is copied exactly (no spaces)
- Verify it's your admin token (not from old/deleted token)
- Try creating a new token

**If you see: "Connection refused"**
- Verify org URL is correct
- Check you have internet connection
- Add `https://` to the URL if missing

**If you see: "Timeout"**
- You have a large user base - script is still working
- Can take 1-5 minutes for very large orgs
- Try again

## Step 8: Run AuthCheck

Once test passes, run the app:

```bash
# Start the development server
./run.sh

# Or manually:
python3 -m uvicorn app.main:app --reload
```

### Access the App

Open browser to: http://localhost:8000

### Test the Feature

1. Click "Compare All Users" tab
2. Click "🚀 Start Comparison" button
3. Wait for results
4. You should see all your Okta users in the grid!

## API Token Security

### ⚠️ Important Security Notes

1. **Treat like a password**
   - Don't share in email, chat, or version control
   - Don't paste in public forums

2. **Store securely**
   - Use password manager
   - Keep .env file protected
   - Consider using secrets management in production

3. **Rotate periodically**
   - Delete old tokens
   - Create new ones
   - Recommended: Every 90 days

4. **Monitor usage**
   - Check Okta admin console for token activity
   - Delete unused tokens immediately

5. **What token provides access to**
   - Can read user information
   - Depending on scope, may be able to modify users
   - Should be read-only for safety

### Revoking a Token

If you accidentally shared a token:

1. Go back to Okta admin console
2. Navigate to Security → API → Tokens
3. Find the token in the list
4. Click "Revoke" or delete it
5. Create a new token
6. Update .env file

## Tips & Tricks

### Find Your Org URL Quickly

```bash
# If you have curl, test the connection:
curl -I https://dev-12345678.okta.com/api/v1/users

# Should return 401 (unauthorized) - that's good!
# Means the server exists but needs authentication
```

### List All Your Users Manually

```bash
# Replace with your values
ORG_URL="https://dev-12345678.okta.com"
TOKEN="your_token_here"

curl -X GET \
  "${ORG_URL}/api/v1/users?filter=status%20eq%20%22ACTIVE%22&limit=200" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Accept: application/json" \
  | python3 -m json.tool
```

### Check Token Permissions

Okta tokens inherit permissions from the user who created them. Your admin account determines what the token can do.

Default permissions for admin tokens include:
- ✅ Read all users
- ✅ Read groups
- ✅ Read attributes
- ❌ Modify users (intentionally restricted for safety)

## Next Steps

1. ✅ Get org URL
2. ✅ Create API token
3. ✅ Configure .env file
4. ✅ Test connection with test script
5. ✅ Run AuthCheck
6. ✅ Click "Compare All Users"
7. ✅ See your Okta users!

## Support

**Questions?**
- See `OKTA_SETUP.md` for detailed configuration
- See `OKTA_API_CALLS.md` for technical details
- Check `docs/` folder for other guides

**Issues?**
- Check error message in test output
- Verify org URL: `https://yourorg.okta.com` (note https://)
- Create fresh token if old one seems broken
- Check internet connection

## Summary

```
┌──────────────────────────────────────┐
│  1. Sign in to Okta Admin Console    │
│  2. Go to Security → API → Tokens    │
│  3. Click "Create Token"             │
│  4. Name it "authcheck-api"          │
│  5. Copy the token immediately       │
│  6. Create .env with:               │
│     OKTA_ORG_URL=...                │
│     OKTA_API_TOKEN=...              │
│  7. Run: python3 test_okta.py        │
│  8. See "✅ CONNECTION SUCCESSFUL!"  │
│  9. Run: ./run.sh                    │
│  10. Click "Compare All Users"       │
└──────────────────────────────────────┘
```

You're done! 🎉
