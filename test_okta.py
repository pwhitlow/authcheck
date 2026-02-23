#!/usr/bin/env python3
"""
Test script to verify Okta connection and fetch users.
"""

import asyncio
import os
from dotenv import load_dotenv
from app.connectors import get_registry

# Load environment variables from .env
load_dotenv()


async def test_okta():
    """Test Okta connector configuration and fetch users."""
    print("\n" + "=" * 60)
    print("OKTA CONNECTION TEST")
    print("=" * 60 + "\n")

    # Check environment variables
    org_url = os.getenv("OKTA_ORG_URL")
    client_id = os.getenv("OKTA_CLIENT_ID")
    client_secret = os.getenv("OKTA_CLIENT_SECRET")
    private_key = os.getenv("OKTA_PRIVATE_KEY")
    api_token = os.getenv("OKTA_API_TOKEN")

    print("📋 Configuration Check:")
    print(f"  OKTA_ORG_URL: {org_url if org_url else '❌ NOT SET'}")

    if client_id and private_key:
        print(f"  OKTA_CLIENT_ID: ✓ SET ({len(client_id)} chars)")
        print(f"  OKTA_PRIVATE_KEY: ✓ SET")
        auth_method = "OAuth2 (private_key_jwt)"
    elif client_id and client_secret:
        print(f"  OKTA_CLIENT_ID: ✓ SET ({len(client_id)} chars)")
        print(f"  OKTA_CLIENT_SECRET: ✓ SET ({len(client_secret)} chars)")
        auth_method = "OAuth2 (client_secret)"
    elif api_token:
        print(
            f"  OKTA_API_TOKEN: ✓ SET "
            f"({len(api_token)} chars)"
        )
        auth_method = "API Token"
    else:
        auth_method = None

    if not org_url or not auth_method:
        print("\n❌ Missing configuration!")
        print("\nCreate a .env file with ONE of these options:")
        print("\n  Option 1: OAuth2 with Private Key JWT (Most Secure)")
        print("    OKTA_ORG_URL=https://yourorg.okta.com")
        print("    OKTA_CLIENT_ID=your_client_id")
        print("    OKTA_PRIVATE_KEY=your_private_key_json")
        print("\n  Option 2: OAuth2 with Client Secret")
        print("    OKTA_ORG_URL=https://yourorg.okta.com")
        print("    OKTA_CLIENT_ID=your_client_id")
        print("    OKTA_CLIENT_SECRET=your_client_secret")
        print("\n  Option 3: API Token (Legacy)")
        print("    OKTA_ORG_URL=https://yourorg.okta.com")
        print("    OKTA_API_TOKEN=your_api_token")
        return False

    print(f"\n  Auth Method: {auth_method}")

    print("\n✅ Configuration looks good!\n")

    # Get connector
    registry = get_registry()
    okta = registry.get_connector("okta")

    # Validate config
    print("🔐 Validating Okta configuration...")
    if not okta.validate_config():
        print("❌ Configuration validation failed!")
        return False

    print("✅ Configuration valid\n")

    # Test getting all users
    print("📊 Fetching all active users from Okta...")
    print("   (This may take a minute for large organizations)\n")

    try:
        users = await okta.get_all_users()

        print(f"✅ Successfully fetched {len(users)} active users from Okta!\n")

        # Show sample users
        if users:
            print("📝 Sample users (first 10):")
            for i, user in enumerate(users[:10], 1):
                print(f"   {i:2}. {user}")

            if len(users) > 10:
                print(f"   ... and {len(users) - 10} more")

        print("\n" + "=" * 60)
        print("✅ CONNECTION SUCCESSFUL!")
        print("=" * 60 + "\n")
        return True

    except ValueError as e:
        print(f"❌ Authentication Error: {e}")
        print("\nPossible causes:")
        print("  • Invalid API token")
        print("  • Incorrect org URL")
        print("  • Token permissions insufficient")
        print("\nTo fix:")
        print("  1. Verify org URL is correct (https://yourorg.okta.com)")
        print("  2. Check API token hasn't expired")
        print("  3. Create new token with proper permissions")
        return False

    except TimeoutError as e:
        print(f"❌ Timeout Error: {e}")
        print("\nPossible causes:")
        print("  • Okta server is slow/unreachable")
        print("  • Network connectivity issue")
        print("  • Very large user base taking too long")
        print("\nTo fix:")
        print("  1. Check internet connection")
        print("  2. Try again in a moment")
        print("  3. Increase OKTA_TIMEOUT in .env")
        return False

    except ConnectionError as e:
        print(f"❌ Connection Error: {e}")
        print("\nPossible causes:")
        print("  • Can't reach Okta servers")
        print("  • Firewall blocking connection")
        print("  • Incorrect org URL")
        print("\nTo fix:")
        print("  1. Verify org URL: https://yourorg.okta.com (note the https://)")
        print("  2. Test manually: curl https://yourorg.okta.com/api/v1/users")
        print("  3. Check firewall settings")
        return False

    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        print("\nFull error details:")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_okta())
    exit(0 if success else 1)
