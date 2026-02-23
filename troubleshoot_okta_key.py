#!/usr/bin/env python3
"""
Troubleshooting script for Okta private_key_jwt authentication.
"""

import json
import jwt
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("OKTA PRIVATE_KEY_JWT TROUBLESHOOTING")
print("=" * 70)

# Check all necessary environment variables
client_id = os.getenv("OKTA_CLIENT_ID")
org_url = os.getenv("OKTA_ORG_URL")
private_key_input = os.getenv("OKTA_PRIVATE_KEY")

print("\n📋 Configuration Check:")
print(f"  OKTA_CLIENT_ID: {'✓' if client_id else '✗'} {client_id or 'NOT SET'}")
print(f"  OKTA_ORG_URL: {'✓' if org_url else '✗'} {org_url or 'NOT SET'}")
print(f"  OKTA_PRIVATE_KEY: {'✓' if private_key_input else '✗'} {'SET' if private_key_input else 'NOT SET'}")

if not all([client_id, org_url, private_key_input]):
    print("\n❌ Missing required configuration!")
    exit(1)

# Prepare private key
private_key_input = private_key_input.replace("\\n", "\n")
token_url = f"{org_url}/oauth2/v1/token"

# Create the JWT
now = datetime.utcnow()
exp = now + timedelta(seconds=10)

header = {
    "alg": "RS256",
    "typ": "JWT",
    # NOTE: If Okta requires a 'kid', uncomment and set it:
    # "kid": "your_key_id_here"
}

payload = {
    "iss": client_id,
    "sub": client_id,
    "aud": token_url,
    "iat": int(now.timestamp()),
    "exp": int(exp.timestamp()),
}

try:
    token = jwt.encode(payload, private_key_input, algorithm="RS256", headers=header)
    print("\n✓ JWT created successfully")
    print(f"\n🔐 JWT Details:")
    print(f"  Header: {jwt.decode(token, options={'verify_signature': False}, algorithms=['RS256'])['iss']}")
    
    # Show first part of token
    parts = token.split('.')
    print(f"  Token parts: {len(parts)} (header.payload.signature)")
    print(f"  Total length: {len(token)} characters")
    
    print(f"\n📊 Token expiration:")
    print(f"  iat (issued at): {now.isoformat()} UTC")
    print(f"  exp (expiration): {exp.isoformat()} UTC")
    print(f"  Time to expiry: {(exp - now).total_seconds()} seconds")
    
    print("\n❓ Troubleshooting:")
    print("  1. Is this private key registered in Okta Admin Console?")
    print("     Go to: Apps → [Your App] → Credentials → Public Keys")
    print("  2. What Key ID (kid) did Okta assign?")
    print("     If you have a kid, add this to the code:")
    print('       header["kid"] = "your_kid_from_okta"')
    print("  3. Is the key marked as Active?")
    print("  4. Check Okta System Log for detailed error messages:")
    print("     Admin Console → Logs")
    print("  5. Verify the app has Client Credentials grant type enabled")
    print("  6. Verify the app has okta.users.read scope enabled")
    
except Exception as e:
    print(f"\n❌ Error creating JWT: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
