# Active Directory Integration Setup Guide

This guide explains how to set up real Active Directory integration for AuthCheck.

## Active Directory Overview

**Active Directory (AD)** stores user accounts and credentials in a centralized database.

**How it works:**
- AD stores user objects in a hierarchical structure (tree of organizational units)
- Each user has attributes like `sAMAccountName`, `userPrincipalName`, `mail`, etc.
- AuthCheck queries AD via **LDAP** (Lightweight Directory Access Protocol)
- Port 389 (standard), 636 (SSL/TLS), 3268/3269 (Global Catalog)

## Key Active Directory Concepts

### Distinguished Names (DN)
Every object in AD has a unique DN:
```
CN=John Doe,OU=Users,DC=example,DC=com
│         │   │              │        └─ Domain component (com)
│         │   │              └─ Domain component (example)
│         │   └─ Organizational Unit (Users)
│         └─ Common Name (John Doe)
└─ CN = Common Name
```

### User Attributes
Common attributes used for searching:
- `sAMAccountName` - Windows username (john.doe, jsmith)
- `userPrincipalName` - Email-like format (john.doe@example.com)
- `mail` - Email address
- `cn` - Common name (display name)
- `userAccountControl` - Account status (enabled/disabled)

### userAccountControl Values
Indicates account status:
- Bit 1 (0x0002) = ACCOUNTDISABLE - Account is disabled
- AuthCheck returns `True` only if user is ENABLED

## Prerequisites

You need to gather from your AD administrator:

| Parameter | Description | Example |
|-----------|-------------|---------|
| **Server** | AD server hostname or IP | `dc1.example.com` or `192.168.1.50` |
| **Port** | LDAP port | `389` (standard) or `636` (SSL) |
| **Base DN** | Root of your directory tree | `DC=example,DC=com` |
| **Bind DN** | Service account for querying | `CN=AuthCheck,OU=Services,DC=example,DC=com` |
| **Bind Password** | Service account password | `P@ssw0rd123!` |
| **Use SSL** | Whether to use LDAPS | `true` or `false` |

## Step 1: Get Active Directory Credentials

### Find Your Domain Components

Your domain name maps to DN components:
```
Domain: example.com
DN components: DC=example,DC=com

Domain: corp.example.com
DN components: DC=corp,DC=example,DC=com

Domain: internal.acme.co.uk
DN components: DC=internal,DC=acme,DC=co,DC=uk
```

### Find Your Base DN

The Base DN depends on your AD structure:

```
# Simple structure - search entire domain
Base DN: DC=example,DC=com

# Multiple OUs - search specific OU
Base DN: OU=Users,DC=example,DC=com

# Complex structure - specific division
Base DN: OU=Engineering,OU=Departments,DC=example,DC=com
```

**To find your base DN:**
1. Ask your AD administrator
2. Check existing LDAP configurations
3. Use `ldapsearch` command: `ldapsearch -H ldap://dc.example.com -b "DC=example,DC=com" -s base`

### Create a Service Account

You need a service account (not a user account) for querying AD:

**In Active Directory Users and Computers:**
1. Create new user: `AuthCheck` in Services OU
2. Set password (or ask admin to)
3. Uncheck "User must change password at next logon"
4. Check "Password never expires"
5. Full DN will be something like: `CN=AuthCheck,OU=Services,DC=example,DC=com`

**Permissions needed:**
- Read properties on all user objects
- Usually "Read" permission is sufficient
- No need for admin rights

## Step 2: Test Active Directory Connectivity

### Test with ldapsearch (Linux/Mac)

```bash
# Install ldap tools
sudo apt-get install ldap-utils  # Linux
brew install openldap            # Mac

# Test basic connectivity
ldapsearch -H ldap://dc.example.com:389 -x -b "DC=example,DC=com" -s base

# Test with bind (service account)
ldapsearch -H ldap://dc.example.com:389 \
  -D "CN=AuthCheck,OU=Services,DC=example,DC=com" \
  -w "password" \
  -b "OU=Users,DC=example,DC=com" \
  "(sAMAccountName=john.doe)"

# Expected: Should return John Doe's user record
```

### Test with Python

```python
from ldap3 import Server, Connection

server = Server("dc.example.com", port=389)
conn = Connection(
    server,
    user="CN=AuthCheck,OU=Services,DC=example,DC=com",
    password="password"
)

if conn.bind():
    print("✓ Successfully connected to Active Directory")
else:
    print(f"✗ Connection failed: {conn.last_error}")
```

## Step 3: Configure AuthCheck

### Option A: Environment Variables (Recommended)

Create a `.env` file in the project root:

```env
# Active Directory Configuration
AD_SERVER=dc.example.com
AD_PORT=389
AD_BASE_DN=OU=Users,DC=example,DC=com
AD_BIND_DN=CN=AuthCheck,OU=Services,DC=example,DC=com
AD_BIND_PASSWORD=your_service_account_password
AD_USE_SSL=false
AD_TIMEOUT=10
```

### Option B: Configuration Dictionary

Pass configuration when initializing:

```python
from app.connectors import get_registry

config = {
    "active_directory": {
        "server": "dc.example.com",
        "port": 389,
        "base_dn": "OU=Users,DC=example,DC=com",
        "bind_dn": "CN=AuthCheck,OU=Services,DC=example,DC=com",
        "bind_password": "password",
        "use_ssl": False,
        "timeout": 10
    }
}

registry = get_registry()
ad = registry.get_connector("active_directory", config.get("active_directory"))
```

## Step 4: Test the Integration

### Test via Python REPL

```python
import asyncio
from app.connectors import get_registry
import os

# Set environment variables
os.environ["AD_SERVER"] = "dc.example.com"
os.environ["AD_PORT"] = "389"
os.environ["AD_BASE_DN"] = "OU=Users,DC=example,DC=com"
os.environ["AD_BIND_DN"] = "CN=AuthCheck,OU=Services,DC=example,DC=com"
os.environ["AD_BIND_PASSWORD"] = "password"

async def test():
    registry = get_registry()
    ad = registry.get_connector("active_directory")

    # Test with a known username
    try:
        result = await ad.authenticate_user("john.doe")
        print(f"User found: {result}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())
```

### Test via AuthCheck UI

1. Start the dev server: `./run.sh`
2. Open http://localhost:8000
3. Upload a CSV with AD usernames
4. Click "Verify Users"
5. Check the Active Directory column for results

### Test with ldapsearch

```bash
# Search for user
ldapsearch -H ldap://dc.example.com:389 \
  -D "CN=AuthCheck,OU=Services,DC=example,DC=com" \
  -w "password" \
  -b "OU=Users,DC=example,DC=com" \
  "(sAMAccountName=john.doe)" \
  userAccountControl

# Look for userAccountControl value
# If no ACCOUNTDISABLE bit (0x0002) set → Account is enabled
```

## Step 5: Verify Configuration

```python
ad = registry.get_connector("active_directory")

if ad.validate_config():
    print("✅ AD configuration is valid")
else:
    print("❌ AD configuration is missing or invalid")
```

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AD_SERVER` | Yes | None | AD server hostname/IP |
| `AD_PORT` | No | 389 | LDAP port |
| `AD_BASE_DN` | Yes | None | Base Distinguished Name |
| `AD_BIND_DN` | Yes | None | Service account DN |
| `AD_BIND_PASSWORD` | Yes | None | Service account password |
| `AD_USE_SSL` | No | false | Use LDAPS (port 636) |
| `AD_TIMEOUT` | No | 10 | Connection timeout (seconds) |

### Configuration Dictionary Keys

```python
{
    "server": str,           # Required: AD server
    "port": int,             # Optional: default 389
    "base_dn": str,          # Required: Base DN
    "bind_dn": str,          # Required: Service account DN
    "bind_password": str,    # Required: Service account password
    "use_ssl": bool,         # Optional: default False
    "timeout": int           # Optional: default 10
}
```

## How It Works

### User Search Process

```
1. Connect to LDAP server (port 389/636)
2. Bind (authenticate) as service account
3. Search for user using filters:
   - (sAMAccountName=john.doe)
   - (userPrincipalName=john.doe@example.com)
   - (mail=john.doe@example.com)
   - (cn=John Doe)
4. Check userAccountControl attribute:
   - If bit 0x0002 set → Account disabled → return False
   - If bit 0x0002 not set → Account enabled → return True
5. If no user found → return False
6. Disconnect (unbind)
```

### Username Matching

AuthCheck tries multiple search attributes:

```
Username: "john.doe"
1. Try sAMAccountName=john.doe
2. Try userPrincipalName=john.doe@example.com
3. Try mail=john.doe@example.com
4. Try cn=John Doe
5. If no exact match, try wildcard: *john.doe*
```

This means you can use:
- Windows usernames: `john.doe`
- Email addresses: `john.doe@example.com`
- Display names: `John Doe`

## Troubleshooting

### "Invalid credentials" or "Bad DN"

**Causes:**
- Service account DN incorrect
- Service account password wrong
- AD not allowing bind

**Solutions:**
```bash
# Test bind manually
ldapsearch -H ldap://dc.example.com:389 \
  -D "CN=AuthCheck,OU=Services,DC=example,DC=com" \
  -w "password" \
  -b "DC=example,DC=com" \
  -s base

# Try with AD administrator account
ldapsearch -H ldap://dc.example.com:389 \
  -D "administrator@example.com" \
  -w "admin_password" \
  -b "DC=example,DC=com" \
  -s base

# Check user exists and credentials
net user authcheck /domain  # Windows
getent passwd authcheck     # Linux
```

### "Connection refused" or "Can't connect"

**Causes:**
- Wrong server address/IP
- LDAP service not running
- Firewall blocking port 389/636
- Wrong port specified

**Solutions:**
```bash
# Test connectivity
ping dc.example.com
telnet dc.example.com 389  # Won't work but tests network
nc -zv dc.example.com 389  # Better connectivity test

# Check if LDAP is running (on DC)
netstat -an | grep 389
ss -ulnp | grep 389

# Try different IPs/hostnames
dc1.example.com
192.168.1.50
ad.internal

# For SSL, try port 636
AD_PORT=636
AD_USE_SSL=true
```

### "Search failed" but connection works

**Causes:**
- Base DN incorrect
- Service account lacks permissions
- User doesn't exist in that OU

**Solutions:**
```bash
# Test base DN
ldapsearch -H ldap://dc.example.com:389 \
  -D "CN=AuthCheck,OU=Services,DC=example,DC=com" \
  -w "password" \
  -b "OU=Users,DC=example,DC=com" \
  -s base

# Search all users (find structure)
ldapsearch -H ldap://dc.example.com:389 \
  -D "CN=AuthCheck,OU=Services,DC=example,DC=com" \
  -w "password" \
  -b "DC=example,DC=com" \
  "(objectClass=user)" \
  sAMAccountName | head -20

# Check service account permissions
# In AD: Right-click OU → Delegate Control
# Give "Read" permission to AuthCheck account
```

### "User not found" but user exists

**Causes:**
- User in different OU than base DN
- Username format wrong (case sensitive)
- User's attributes don't match search

**Solutions:**
```bash
# Search entire domain (slow but comprehensive)
AD_BASE_DN=DC=example,DC=com
AD_PORT=3268  # Global Catalog port

# Try different username formats
john.doe           # sAMAccountName
john.doe@example.com  # userPrincipalName
jdoe               # Short username
John Doe           # Display name

# Find user's actual DN
ldapsearch -H ldap://dc.example.com:389 \
  -D "CN=AuthCheck,OU=Services,DC=example,DC=com" \
  -w "password" \
  -b "DC=example,DC=com" \
  "(sAMAccountName=john.doe)" \
  distinguishedName

# Update AD_BASE_DN to include that OU
```

### Disabled accounts showing as not found

**Expected behavior:**
- AuthCheck returns `False` for disabled accounts
- This is correct - disabled users shouldn't access systems

**To find disabled accounts:**
```bash
ldapsearch -H ldap://dc.example.com:389 \
  -D "CN=AuthCheck,OU=Services,DC=example,DC=com" \
  -w "password" \
  -b "OU=Users,DC=example,DC=com" \
  "(userAccountControl:1.2.840.113556.1.4.803:=2)" \
  sAMAccountName

# Returns all disabled accounts in that OU
```

## SSL/TLS Configuration

### Use LDAPS (Secure LDAP)

```env
AD_SERVER=dc.example.com
AD_PORT=636
AD_USE_SSL=true
```

**Note:** AuthCheck doesn't verify SSL certificates by default (security trade-off for flexibility). In production, consider:

```python
# In active_directory.py, modify Tls():
tls = Tls(validate=ssl.CERT_REQUIRED)
```

### Common Issues with SSL

```bash
# Test SSL connectivity
openssl s_client -connect dc.example.com:636

# Check certificate
openssl s_client -connect dc.example.com:636 -showcerts

# If cert validation fails, get admin to provide cert
```

## Performance Tips

### For Large User Lists

```python
import asyncio

async def verify_users_batch(usernames, connector, batch_size=20):
    """Verify users in batches to manage AD load."""
    results = {}

    for i in range(0, len(usernames), batch_size):
        batch = usernames[i:i + batch_size]
        tasks = [connector.authenticate_user(u) for u in batch]
        batch_results = await asyncio.gather(*tasks)

        for user, result in zip(batch, batch_results):
            results[user] = result

    return results
```

### Use Global Catalog for Large Forests

```env
# Global Catalog = all domains in forest
# Ports: 3268 (plain), 3269 (SSL)
AD_SERVER=gc.example.com
AD_PORT=3268
AD_BASE_DN=DC=example,DC=com
```

## Security Best Practices

1. **Service Account Security**
   - Use dedicated service account (not admin)
   - Strong password (20+ characters)
   - Password never expires
   - Disable interactive logon
   - Monitor for unusual activity

2. **Firewall & Network**
   - Only allow from trusted networks
   - Restrict LDAP to specific servers
   - Consider VPN for remote access
   - Monitor LDAP connections

3. **Credentials Protection**
   - Never hardcode passwords
   - Use .env file (not in git)
   - Rotate passwords regularly
   - Use managed secrets in production

4. **Monitoring & Auditing**
   - Log all queries
   - Monitor failed lookups
   - Track authentication attempts
   - Enable AD audit logging

5. **Configuration**
   - Minimal permissions (read-only)
   - Regular security reviews
   - Keep AD patches current
   - Document AD structure

## Active Directory Domains

If you have multiple domains:

```
Single Domain:
AD_BASE_DN=DC=example,DC=com

Multiple Domains - Query All:
AD_SERVER=gc.example.com
AD_PORT=3268

Multiple Domains - Specific:
AD_BASE_DN=DC=subdomain,DC=example,DC=com
```

## Advanced: Custom LDAP Filters

The connector uses built-in filters, but you can modify for specific needs:

```python
# In active_directory.py, modify search filters:

# Only enabled users
search_filter = f"(&({attr}={username})(!(userAccountControl:1.2.840.113556.1.4.803:=2)))

# Only users in specific groups
search_filter = f"(&({attr}={username})(memberOf=CN=SalesTeam,OU=Groups,DC=example,DC=com)))

# Only enabled users in specific groups
search_filter = f"(&({attr}={username})(!(userAccountControl:1.2.840.113556.1.4.803:=2))(memberOf=CN=SalesTeam,OU=Groups,DC=example,DC=com)))
```

## Active Directory Versions

AuthCheck works with:
- **Windows Server 2003** and newer
- **Azure AD** (uses different protocol, would need separate connector)
- **OpenLDAP** and compatible servers

## Additional Resources

- [LDAP RFC 4511](https://tools.ietf.org/html/rfc4511)
- [Active Directory Schema](https://docs.microsoft.com/en-us/windows/win32/adschema/)
- [ldap3 Documentation](https://ldap3.readthedocs.io/)
- [AD User Attributes](https://docs.microsoft.com/en-us/windows/win32/adschema/a-samaccountname)

## Next Steps

1. Gather AD server details from IT
2. Create service account in AD
3. Test with ldapsearch
4. Set environment variables
5. Test with AuthCheck
6. Deploy to production

---

**Questions about your AD setup?** Contact your Active Directory administrator for server details.
