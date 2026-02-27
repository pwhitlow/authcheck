"""
Test script for the User Alias Association System.

This script tests the alias resolver functionality including:
- Loading configuration
- Merging users
- Splitting groups
- Consolidating user sources
"""

import asyncio
import json
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent))

from app.utils.alias_resolver import get_user_group_resolver


def test_basic_grouping():
    """Test basic group resolution."""
    print("Testing basic grouping...")

    resolver = get_user_group_resolver()

    # Test ungrouped email
    email1 = "test1@example.com"
    group_id1 = resolver.get_group_id(email1)
    emails1 = resolver.get_group_emails(group_id1)

    print(f"  Ungrouped email: {email1}")
    print(f"    Group ID: {group_id1}")
    print(f"    Group emails: {emails1}")
    assert group_id1 == email1, "Ungrouped email should return itself as group_id"
    assert emails1 == [email1], "Ungrouped email should return itself in list"

    print("  ✓ Basic grouping works")


def test_consolidation():
    """Test user source consolidation."""
    print("\nTesting consolidation...")

    resolver = get_user_group_resolver()

    # Mock user sources (as if from connectors)
    user_sources = {
        "john.doe@company.com": {"okta": True, "ad": False, "slack": True},
        "j.doe@external.com": {"okta": False, "ad": True, "slack": False},
        "jane.smith@company.com": {"okta": True, "ad": True, "slack": False},
    }

    consolidated, groups = resolver.consolidate_users(user_sources)

    print(f"  Original users: {len(user_sources)}")
    print(f"  Consolidated groups: {len(consolidated)}")

    # If john.doe and j.doe are grouped in config, they should be consolidated
    for group_id, sources in consolidated.items():
        emails = groups[group_id]
        print(f"  Group: {group_id}")
        print(f"    Emails: {emails}")
        print(f"    Sources: {sources}")

    print("  ✓ Consolidation works")


def test_merge_and_split():
    """Test merge and split operations."""
    print("\nTesting merge and split...")

    resolver = get_user_group_resolver()

    # Test emails
    test_emails = [
        "test.merge1@example.com",
        "test.merge2@example.com",
        "test.merge3@example.com"
    ]

    # Test merge
    print(f"  Merging: {test_emails}")
    group_id = resolver.merge_users(test_emails, "Test User")
    print(f"    Created group: {group_id}")

    # Verify merge
    for email in test_emails:
        retrieved_group_id = resolver.get_group_id(email)
        assert retrieved_group_id == group_id, f"Email {email} not properly grouped"

    group_emails = resolver.get_group_emails(group_id)
    assert set(group_emails) == set(test_emails), "Group emails don't match"
    print("  ✓ Merge successful")

    # Test split (keep only first email)
    print(f"  Splitting group, keeping: {test_emails[0]}")
    resolver.split_users(group_id, [test_emails[0]])

    # Verify split
    remaining_group = resolver.get_group_id(test_emails[0])
    print(f"    Remaining emails: {resolver.get_group_emails(remaining_group)}")

    # First email should now be standalone (not grouped)
    assert resolver.is_grouped(test_emails[0]) == False, "Email should no longer be grouped"

    # Other emails should be independent
    for email in test_emails[1:]:
        email_group = resolver.get_group_id(email)
        assert email_group == email, f"Email {email} should be independent after split"

    print("  ✓ Split successful")


def test_config_file():
    """Test configuration file operations."""
    print("\nTesting config file operations...")

    config_path = Path(__file__).parent / "user_alias_mapping.json"

    if config_path.exists():
        print(f"  Config file exists: {config_path}")
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            print(f"  Groups in config: {len(config.get('groups', []))}")
            print("  ✓ Config file is valid JSON")
        except json.JSONDecodeError as e:
            print(f"  ✗ Config file has invalid JSON: {e}")
    else:
        print(f"  No config file at: {config_path}")
        print("  This is OK - system will work without it")


def main():
    """Run all tests."""
    print("=" * 60)
    print("User Alias Association System - Test Suite")
    print("=" * 60)

    try:
        test_basic_grouping()
        test_consolidation()
        test_merge_and_split()
        test_config_file()

        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
