# RADIUS Integration Setup Guide

This guide explains how to set up real RADIUS integration for AuthCheck.

## RADIUS Protocol Overview

**RADIUS** (Remote Authentication Dial In User Service) is a network protocol for authentication and authorization.

**Key Characteristics:**
- Client/Server architecture
- Uses UDP (port 1812 by default)
- Shared secret between client and server
- No "list users" API - must authenticate to verify existence
- Very common in enterprise environments
- Lightweight and fast

## How AuthCheck Checks RADIUS Users

AuthCheck uses a "test authentication" approach:

1. Sends **Access-Request** packet with:
   - Username to check
   - Test password (always wrong)
   - NAS-Identifier (client name)

2. RADIUS server responds with:
   - **Access-Accept** (code 2) → User exists, password accepted
   - **Access-Reject** (code 3) → User exists, password rejected ✓
   - **Access-Challenge** (code 11) → User exists, needs additional auth ✓
   - **No response** → User doesn't exist
   - **Timeout** → Server unreachable or user doesn't exist

**Result:** If we get any response code indicating the server processed the request, user exists!

## Prerequisites

You need:
1. **RADIUS Server Address** - IP or hostname (e.g., `radius.example.com`)
2. **RADIUS Server Port** - Usually 1812 (standard) or custom port
3. **Shared Secret** - The password configured on RADIUS server for this client
4. **NAS-Identifier** - Optional friendly name for your client (default: "authcheck")

### Finding Your RADIUS Configuration

**In your organization:**
- Ask your Network/Systems team for RADIUS details
- Check existing RADIUS client configs (VPN, WiFi, dial-up systems)
- Look in Cisco, Juniper, or other network device configs
- Check FreeRADIUS or Windows NPS server configuration

**Common locations:**
- Linux: `/etc/raddb/clients.conf` or `/etc/freeradius/clients.conf`
- Windows NPS: Active Directory, look for RADIUS client entries
- Commercial appliances: Admin console → RADIUS clients

## Step 1: Verify RADIUS Server Connectivity

Before configuring AuthCheck, test basic connectivity:

### Test with radtest (Linux)

```bash
# Install if needed
sudo apt-get install freeradius-utils

# Test connection
radtest testuser testpassword 192.168.1.100 1812 shared_secret
```

Expected output if server is reachable:
```
Sending Access-Request of id 123 to 192.168.1.100 port 1812
...
Received Access-Reject id 123...  (User exists, password wrong)
```

### Test with Python

```python
from pyradius import Client

client = Client(
    server=("radius.example.com", 1812),
    secret=b"your_shared_secret",
    timeout=5
)

print(f"✓ Can reach RADIUS server at radius.example.com:1812")
```

## Step 2: Get RADIUS Credentials

Gather the following information:

| Parameter | Description | Example |
|-----------|-------------|---------|
| **Server** | RADIUS server hostname or IP | `192.168.1.100` or `radius.example.com` |
| **Port** | RADIUS authentication port | `1812` (standard) |
| **Secret** | Shared secret (password) | `SuperSecret123!` |
| **NAS-Identifier** | Your client name (optional) | `authcheck` (default) |

## Step 3: Configure AuthCheck

### Option A: Environment Variables (Recommended)

Create a `.env` file in the project root:

```env
# RADIUS Configuration
RADIUS_SERVER=radius.example.com
RADIUS_PORT=1812
RADIUS_SECRET=your_shared_secret_here
RADIUS_NAS_ID=authcheck
RADIUS_TIMEOUT=10
```

### Option B: Configuration Dictionary

Pass configuration when initializing:

```python
from app.connectors import get_registry

config = {
    "radius": {
        "server": "radius.example.com",
        "port": 1812,
        "secret": "your_shared_secret",
        "nas_identifier": "authcheck",
        "timeout": 10,
        "test_password": "__TEST__"  # Optional
    }
}

registry = get_registry()
radius = registry.get_connector("radius", config.get("radius"))
```

## Step 4: Test the Integration

### Test via Python REPL

```python
import asyncio
from app.connectors import get_registry
import os

# Set environment variables
os.environ["RADIUS_SERVER"] = "radius.example.com"
os.environ["RADIUS_PORT"] = "1812"
os.environ["RADIUS_SECRET"] = "your_shared_secret"

async def test():
    registry = get_registry()
    radius = registry.get_connector("radius")

    # Test with a known username
    try:
        result = await radius.authenticate_user("john.doe")
        print(f"User found: {result}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())
```

### Test via AuthCheck UI

1. Start the dev server: `./run.sh`
2. Open http://localhost:8000
3. Upload a CSV with RADIUS usernames
4. Click "Verify Users"
5. Check the RADIUS column for results

### Test Connection Without AuthCheck

```bash
# Using radtest
radtest john.doe test_password radius.example.com 1812 shared_secret

# Expected output:
# Sending Access-Request of id 123 to radius.example.com port 1812
# Received Access-Reject id 123 (User exists, password wrong!)
```

## Step 5: Verify Configuration

```python
radius = registry.get_connector("radius")

if radius.validate_config():
    print("✅ RADIUS configuration is valid")
else:
    print("❌ RADIUS configuration is missing or invalid")
    print("Required: server, port, secret")
```

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RADIUS_SERVER` | Yes | None | RADIUS server hostname/IP |
| `RADIUS_PORT` | No | 1812 | RADIUS auth port |
| `RADIUS_SECRET` | Yes | None | Shared secret (password) |
| `RADIUS_NAS_ID` | No | authcheck | NAS-Identifier value |
| `RADIUS_TIMEOUT` | No | 10 | Request timeout in seconds |

### Configuration Dictionary Keys

```python
{
    "server": str,           # Required: hostname/IP
    "port": int,             # Optional: default 1812
    "secret": str,           # Required: shared secret
    "nas_identifier": str,   # Optional: default "authcheck"
    "timeout": int,          # Optional: default 10
    "test_password": str     # Optional: dummy password for testing
}
```

## How It Works

### User Existence Check

```
1. Client sends Access-Request with:
   - User_Name: "john.doe"
   - User_Password: "__TEST_PASSWORD__"  (intentionally wrong)
   - NAS_Identifier: "authcheck"

2. RADIUS server receives request

3. RADIUS server responds:
   - If user exists: Access-Reject (password was wrong)
   - If user doesn't exist: No response or timeout

4. AuthCheck interprets response:
   - Response codes 2, 3, 11: User EXISTS (return True)
   - No response/timeout: User DOESN'T exist (return False)
```

### RADIUS Response Codes

| Code | Name | Meaning | User Exists? |
|------|------|---------|-------------|
| 2 | Access-Accept | Credentials accepted | ✓ Yes |
| 3 | Access-Reject | Credentials rejected | ✓ Yes |
| 11 | Access-Challenge | Additional auth needed | ✓ Yes |
| Other | - | Unknown response | ✗ No |
| None | Timeout | No response | ✗ No |

## Troubleshooting

### "RADIUS server did not respond (timeout)"

**Causes:**
- Server address/port incorrect
- RADIUS service not running
- Firewall blocking UDP port 1812
- Network unreachable

**Solutions:**
```bash
# Test connectivity
ping radius.example.com
telnet radius.example.com 1812  # Won't work for UDP, but tests network
nmap -u -p 1812 radius.example.com

# Check RADIUS server status
sudo systemctl status freeradius
radtest testuser testpass radius.example.com 1812 shared_secret

# Increase timeout
RADIUS_TIMEOUT=30  # Try 30 seconds
```

### "Access-Reject" but user should exist

**Causes:**
- Correct behavior! RADIUS-Reject means user exists but password was wrong
- This is expected since we're using a dummy test password

**Check:**
- Try with actual RADIUS password to verify server is working
- Test with `radtest` to confirm

### "Connection refused"

**Causes:**
- RADIUS server not listening on that port
- Wrong IP address or port
- RADIUS service not started

**Solutions:**
```bash
# Verify RADIUS is listening
sudo netstat -ulnp | grep 1812
sudo ss -ulnp | grep 1812

# Start RADIUS service
sudo systemctl start freeradius
```

### "Invalid shared secret"

**Causes:**
- Shared secret doesn't match what's configured on server
- Extra spaces or hidden characters in secret

**Solutions:**
```bash
# Check secret in FreeRADIUS config
sudo grep -r "secret" /etc/freeradius/

# Verify exact match (check for spaces)
echo -n "your_secret" | wc -c  # Count characters

# Make sure there are no trailing spaces in .env
```

### "User not found" but user exists

**Causes:**
- Wrong username format (case sensitive)
- Server not properly configured as RADIUS client
- User domain prefix needed (e.g., "DOMAIN\username")

**Solutions:**
```bash
# Try different username formats
john.doe           # Email format
johndoe            # No dot
jdoe               # First initial
domain\johndoe     # Windows domain format

# Test with radtest
radtest john.doe dummy_pass radius.example.com 1812 secret

# Check RADIUS logs
sudo tail -f /var/log/freeradius/radius.log
```

### Large number of users times out

**Causes:**
- Default 10-second timeout too short for slow servers
- Server is overloaded

**Solutions:**
```env
# Increase timeout
RADIUS_TIMEOUT=30

# Implement batch processing
# Query in smaller groups (10-20 users at a time)
```

## Security Best Practices

1. **Protect Shared Secret**
   - Treat like a password
   - Never commit `.env` file to git
   - Use strong, random secrets

2. **Network Security**
   - RADIUS should only be accessible from trusted networks
   - Consider VPN or private network
   - Monitor for unauthorized access

3. **Firewall Rules**
   - Only allow RADIUS client IPs
   - Restrict outbound RADIUS access

4. **Monitoring**
   - Log all RADIUS queries
   - Monitor for failed authentication attempts
   - Alert on unusual patterns

5. **Configuration**
   - Use specific RADIUS client entries (not wildcards)
   - Implement per-client shared secrets
   - Regular security audits

## Advanced Configuration

### Custom Test Password

By default, AuthCheck uses `__TEST_PASSWORD__` as test password. To customize:

```python
config = {
    "radius": {
        "server": "radius.example.com",
        "secret": "shared_secret",
        "test_password": "my_custom_test_pass"
    }
}
```

### Multiple RADIUS Servers

To query multiple RADIUS servers, create multiple connectors:

```python
registry = get_registry()

configs = {
    "radius_primary": {
        "server": "radius1.example.com",
        "secret": "secret1"
    },
    "radius_backup": {
        "server": "radius2.example.com",
        "secret": "secret2"
    }
}

# Would need to modify connector loading to handle multiple instances
```

### Batch User Verification

For large user lists:

```python
import asyncio

async def verify_users_batch(usernames, connector, batch_size=20):
    """Verify users in batches to manage server load."""
    results = {}

    for i in range(0, len(usernames), batch_size):
        batch = usernames[i:i + batch_size]
        tasks = [connector.authenticate_user(u) for u in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for user, result in zip(batch, batch_results):
            if isinstance(result, Exception):
                results[user] = False  # Treat errors as user not found
            else:
                results[user] = result

    return results
```

## Testing Scenarios

### Scenario 1: User Exists
```
→ Send: User_Name=john.doe, User_Password=wrongpass
← Receive: Access-Reject (code 3)
Result: Return True (user exists)
```

### Scenario 2: User Doesn't Exist
```
→ Send: User_Name=nonexistent, User_Password=wrongpass
← Receive: No response (timeout)
Result: Return False (user doesn't exist)
```

### Scenario 3: User Locked Out
```
→ Send: User_Name=john.doe, User_Password=wrongpass
← Receive: Access-Reject (code 3) with Message-Authenticator
Result: Return True (user exists, account locked)
```

## RADIUS Servers Tested

- **FreeRADIUS** - Open source, most common
- **Windows NPS** - Microsoft RADIUS implementation
- **Cisco ACS** - Cisco Access Control Server
- **Radius Guard** - Commercial RADIUS server

## Additional Resources

- [RADIUS Protocol RFC 2865](https://tools.ietf.org/html/rfc2865)
- [FreeRADIUS Documentation](https://freeradius.org/documentation/)
- [pyradius Library](https://github.com/wichert/pyradius)
- [RADIUS Explained](https://www.techtarget.com/searchnetworking/definition/RADIUS)

## Next Steps

1. Gather RADIUS server details
2. Test connectivity with radtest
3. Set environment variables
4. Test with AuthCheck
5. Deploy to production

**Questions about your RADIUS server setup?** Refer to your network team or system administrator for server details.
