#!/usr/bin/env python3
"""
Test script to verify Okta connector configuration and connectivity.

Usage:
    python test_okta_connection.py [username]

If username is not provided, will test with a default test username.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.connectors.okta import OktaConnector


async def test_okta_connection(test_username=None):
    """Test Okta connector configuration and connectivity."""

    print("=" * 70)
    print("Okta Connector Test")
    print("=" * 70)
    print()

    # Load configuration
    print("📁 Loading Okta configuration...")
    config_path = Path.home() / ".okta_config"

    if not config_path.exists():
        print(f"❌ Error: Configuration file not found at {config_path}")
        print()
        print("Please create ~/.okta_config with your Okta credentials.")
        print("See .okta_config.example for format.")
        sys.exit(1)

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"✓ Loaded configuration from {config_path}")
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in configuration file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        sys.exit(1)

    print()

    # Display configuration summary (without sensitive data)
    print("🔧 Configuration Summary:")
    print(f"   Org URL: {config.get('orgUrl', 'NOT SET')}")
    print(f"   Client ID: {config.get('clientId', 'NOT SET')}")
    print(f"   Auth Mode: {config.get('authorizationMode', 'NOT SET')}")
    print(f"   Scopes: {', '.join(config.get('scopes', []))}")
    private_key = config.get('privateKey')
    if private_key:
        if isinstance(private_key, dict):
            print(f"   Private Key: JWK format (kid: {private_key.get('kid', 'N/A')})")
        else:
            print(f"   Private Key: PEM format ({len(private_key)} chars)")
    else:
        print(f"   Private Key: NOT SET")
    print()

    # Create connector
    print("🔌 Creating Okta connector...")
    try:
        connector = OktaConnector(config)
        print("✓ Connector created successfully")
    except Exception as e:
        print(f"❌ Error creating connector: {e}")
        sys.exit(1)

    print()

    # Validate configuration
    print("✅ Validating configuration...")
    if connector.validate_config():
        print("✓ Configuration is valid")
    else:
        print("❌ Configuration validation failed")
        print("   Please check that all required fields are present:")
        print("   - orgUrl")
        print("   - authorizationMode")
        print("   - clientId")
        print("   - scopes")
        print("   - privateKey")
        sys.exit(1)

    print()

    # Test user lookup
    if test_username is None:
        print("💡 No test username provided. Provide one as argument to test user lookup.")
        print("   Example: python test_okta_connection.py user@hudsonalpha.org")
    else:
        print(f"🔍 Testing user lookup for: {test_username}")
        try:
            result = await connector.authenticate_user(test_username)
            if result:
                print(f"✓ User '{test_username}' found and is ACTIVE in Okta")
            else:
                print(f"✗ User '{test_username}' not found or not ACTIVE in Okta")
        except Exception as e:
            print(f"❌ Error during user lookup: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    print()

    # Test user enumeration
    print("👥 Testing user enumeration (get all active users)...")
    print("   This may take a moment for organizations with many users...")
    try:
        users = await connector.get_all_users()
        print(f"✓ Successfully retrieved {len(users)} active users from Okta")

        if len(users) > 0:
            print()
            print(f"   First 5 users:")
            for user in users[:5]:
                print(f"     - {user}")
            if len(users) > 5:
                print(f"     ... and {len(users) - 5} more")
    except Exception as e:
        print(f"❌ Error during user enumeration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print()
    print("=" * 70)
    print("✅ All tests passed!")
    print("=" * 70)
    print()
    print("Your Okta connector is configured correctly and ready to use.")
    print()


if __name__ == "__main__":
    test_username = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(test_okta_connection(test_username))
