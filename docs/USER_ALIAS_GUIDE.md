# User Alias Association Guide

## Overview

The User Alias Association System allows you to link multiple email addresses that belong to the same person. This is useful when users have:
- Contractor accounts with different email domains
- External email addresses
- Temporary or legacy accounts
- Multiple organizational email addresses

## Two Ways to Manage Aliases

### 1. JSON Configuration File (Bulk Import)

**File:** `user_alias_mapping.json` (in project root)

Use this method for:
- Bulk imports of known aliases
- Version-controlled alias configurations
- Automated setup

**Example:**
```json
{
  "version": "1.0",
  "groups": [
    {
      "id": "user_001",
      "emails": [
        "john.doe@hudsonalpha.org",
        "j.doe@contractor.com",
        "john.d@external.org"
      ],
      "display_name": "John Doe (Multiple Accounts)"
    }
  ]
}
```

**Setup:**
```bash
cd user-auth-verification
cp user_alias_mapping.json.example user_alias_mapping.json
# Edit the file with your groups
```

### 2. Interactive Merge/Split UI

Use this method for:
- Ad-hoc merging of discovered duplicates
- Interactive management of user groups
- Quick fixes without editing JSON

**How to Use:**

#### Merging Accounts

1. Navigate to any user's detail page: `http://localhost:8000/user/email@example.com`
2. Click the **"Merge with Other Accounts"** button
3. Check the boxes next to emails you want to merge
4. Click **"Merge Selected"**
5. The page will reload showing the merged group

#### Splitting Groups

1. Navigate to a grouped user's detail page
2. You'll see a **"GROUPED (N)"** badge and all associated emails
3. Click the **"Split Group"** button
4. Uncheck emails you want to remove from the group
5. Click **"Split Group"**
6. Unchecked emails become independent again

## How Grouping Affects the Comparison Matrix

### Before Grouping:
```
Username                      Okta  AD   Slack
john.doe@hudsonalpha.org      ✓     ✗    ✓
j.doe@contractor.com          ✗     ✓    ✗
john.d@external.org           ✗     ✗    ✓
```

### After Grouping:
```
Username                      Okta  AD   Slack
john.doe@hudsonalpha.org      ✓     ✓    ✓
  ↳ j.doe@contractor.com      GROUPED (3)
  ↳ john.d@external.org
```

**Key Features:**
- **Single Row:** All emails appear together
- **OR Logic:** ✓ appears if ANY email exists in that source
- **Badge:** Shows how many emails are grouped
- **Counts:** Statistics reflect consolidated totals

## API Endpoints

The following REST API endpoints are available:

### Get Group Info
```bash
GET /api/user/{email}/group-info
```

**Response:**
```json
{
  "is_grouped": true,
  "group_id": "user_001",
  "emails": ["email1@example.com", "email2@example.com"],
  "display_name": "John Doe"
}
```

### Merge Users
```bash
POST /api/users/merge
Content-Type: application/json

{
  "emails": ["email1@example.com", "email2@example.com"],
  "display_name": "John Doe (Optional)"
}
```

### Split Group
```bash
POST /api/users/split
Content-Type: application/json

{
  "group_id": "user_001",
  "emails_to_keep": ["email1@example.com"]
}
```

## Technical Details

### Storage
- Groups are stored in `user_alias_mapping.json`
- The file is automatically created/updated when using the UI
- The file can be committed to version control (no sensitive data)

### Group IDs
- When using JSON: Use the `id` field you specify
- When using UI: The first email becomes the group ID
- Group IDs are stable identifiers

### Merging Behavior
- If any email is already in a group, new emails are added to that group
- If multiple emails are in different groups, they're consolidated into one
- The primary email (first in the list) becomes the group representative

### Splitting Behavior
- Unchecked emails become independent (no longer grouped)
- If only 1 email remains, the group is automatically dissolved
- If all emails are removed, the group is deleted

### Edge Cases
- **No config file:** System works normally without grouping
- **Invalid JSON:** Logs error, continues without grouping
- **Duplicate emails:** First occurrence wins, warning logged
- **Empty groups:** Skipped during validation

## Best Practices

1. **Use JSON for bulk setup:** If you know aliases in advance, use the JSON file
2. **Use UI for discovery:** When you find duplicates during analysis, use the UI
3. **Document reasons:** Use the `display_name` field to explain why accounts are grouped
4. **Regular audits:** Periodically review `user_alias_mapping.json` for outdated groups
5. **Commit the file:** Track alias changes in version control

## Troubleshooting

### Groups not appearing after JSON edit
- Check JSON syntax with a validator
- Restart the application (config is loaded on startup)
- Check logs for parsing errors

### Can't merge users
- Ensure you have at least 2 emails selected
- Check browser console for errors
- Verify API endpoints are accessible

### Split button not showing
- Verify the user is actually in a group (GROUPED badge should appear)
- Check browser console for JavaScript errors
- Refresh the page

## Example Workflow

1. **Initial Setup:**
   ```bash
   cd user-auth-verification
   cp user_alias_mapping.json.example user_alias_mapping.json
   # Add known aliases to the file
   ./run.sh
   ```

2. **Run Comparison:**
   - Visit http://localhost:8000
   - Click "Start Comparison"
   - Review the matrix for duplicates

3. **Merge Duplicates:**
   - Click on a suspected duplicate email
   - Click "Merge with Other Accounts"
   - Select related emails
   - Click "Merge Selected"

4. **Verify:**
   - Return to comparison view
   - Verify the merged row shows correct checkmarks
   - Check that counts are updated

5. **Adjust if Needed:**
   - Visit merged user's detail page
   - Click "Split Group" if needed
   - Uncheck emails to remove
   - Click "Split Group"
