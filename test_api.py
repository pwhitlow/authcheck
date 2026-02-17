#!/usr/bin/env python3
"""
Simple test script to verify API endpoints.
Run with: python test_api.py
"""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.connectors import get_registry


async def test_connectors():
    """Test that connectors are registered and accessible."""
    print("🔍 Testing Connector Registry...")
    print("-" * 50)

    registry = get_registry()

    # List available connectors
    connector_ids = registry.list_connector_ids()
    print(f"✓ Found {len(connector_ids)} registered connectors:")
    for conn_id in connector_ids:
        print(f"  - {conn_id}")

    print()

    # Get all connectors
    connectors = registry.get_all_connectors()
    print(f"✓ Successfully instantiated {len(connectors)} connectors:")
    for connector in connectors:
        print(f"  - {connector.get_display_name()} ({connector.get_connector_id()})")

    print()
    print("✓ Connector Registry: OK")
    print()


async def test_verification():
    """Test the verification logic."""
    print("🔍 Testing Verification Logic...")
    print("-" * 50)

    registry = get_registry()
    connectors = registry.get_all_connectors()

    test_user = "test.user"
    print(f"Querying connectors for user: {test_user}")
    print()

    # Query all connectors for a test user
    tasks = [connector.authenticate_user(test_user) for connector in connectors]
    results = await asyncio.gather(*tasks)

    print("Results:")
    for connector, result in zip(connectors, results):
        status = "✓ Found" if result else "✗ Not Found"
        print(f"  {connector.get_display_name():20} {status}")

    print()
    print("✓ Verification Logic: OK")
    print()


async def main():
    """Run all tests."""
    print()
    print("=" * 50)
    print("User Auth Verification - API Test Suite")
    print("=" * 50)
    print()

    try:
        await test_connectors()
        await test_verification()

        print("=" * 50)
        print("✅ All tests passed!")
        print("=" * 50)
        print()
        print("To start the development server, run:")
        print("  python -m uvicorn app.main:app --reload")
        print()
        print("Then visit: http://localhost:8000")
        print()

    except Exception as e:
        print()
        print("=" * 50)
        print(f"❌ Test failed: {e}")
        print("=" * 50)
        print()
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
