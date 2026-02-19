# Okta API Calls - Behind the Scenes

This document shows exactly what API calls AuthCheck makes to Okta.

## API Endpoint

**Base URL**: `https://your-org.okta.com/api/v1`

**Authentication**: Bearer token in `Authorization` header

## Get All Active Users

### Request

```http
GET /api/v1/users?filter=status eq "ACTIVE"&limit=200 HTTP/1.1
Host: dev-12345678.okta.com
Authorization: Bearer 00abcDEF1234567890ghijklmNOPQRS_tuvwxyz
Accept: application/json
```

### What This Does

- Queries the Okta Users API
- Filters for users with status = "ACTIVE"
- Returns maximum 200 users per request (pagination limit)
- Results sorted by ID

### Response Example

```json
[
  {
    "id": "00ub0oNGTSWTBKOLGLHO",
    "status": "ACTIVE",
    "created": "2013-07-02T21:36:25.344Z",
    "activated": "2013-07-02T21:36:25.344Z",
    "statusChanged": "2013-07-02T21:36:25.344Z",
    "lastLogin": "2024-02-17T10:30:00.000Z",
    "lastUpdated": "2024-02-17T10:30:00.000Z",
    "passwordChanged": "2013-07-02T21:36:25.344Z",
    "profile": {
      "firstName": "John",
      "lastName": "Doe",
      "email": "john.doe@example.com",
      "login": "john.doe@example.com",
      "mobilePhone": null
    },
    "_links": {...}
  },
  {
    "id": "00ub0oNGTSWTBKOLGLH1",
    "status": "ACTIVE",
    "profile": {
      "firstName": "Jane",
      "lastName": "Smith",
      "email": "jane.smith@example.com",
      "login": "jane.smith@example.com"
    }
  }
]
```

**What AuthCheck Extracts**: `profile.login` field from each user

## Pagination

### How It Works

Okta uses cursor-based pagination via the `Link` header:

```http
Link: <https://dev-12345678.okta.com/api/v1/users?after=00ub0oNGTSWTBKOLGLH2&filter=status%20eq%20%22ACTIVE%22>; rel="next"
```

### AuthCheck Pagination Logic

```
1. Make first request
   GET /api/v1/users?filter=status eq "ACTIVE"&limit=200
   ↓
2. Receive 200 users + Link header with rel="next"
   ↓
3. Extract 'after' parameter from Link header
   ↓
4. Make next request
   GET /api/v1/users?filter=status eq "ACTIVE"&limit=200&after=00ub0...
   ↓
5. Repeat until no Link header with rel="next"
   ↓
6. Return all combined users
```

### Example Flow

```
Request 1: GET /api/v1/users?filter=status eq "ACTIVE"&limit=200
Response: 200 users, Link header has rel="next"
          Compile list: [user 1, user 2, ..., user 200]

Request 2: GET /api/v1/users?filter=status eq "ACTIVE"&limit=200&after=00ub0...
Response: 150 users, no Link header with rel="next"
          Compile list: [user 1-200, user 201-350]

Final Result: 350 total users
```

## Check Single User

### Request

```http
GET /api/v1/users?filter=profile.login eq "john.doe@example.com" HTTP/1.1
Host: dev-12345678.okta.com
Authorization: Bearer YOUR_TOKEN
Accept: application/json
```

### Response

If user found:
```json
[
  {
    "id": "00ub0oNGTSWTBKOLGLHO",
    "status": "ACTIVE",
    "profile": {
      "login": "john.doe@example.com"
    }
  }
]
```

If user not found:
```json
[]
```

## API Response Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Return the users |
| 400 | Bad Request | Invalid filter syntax |
| 401 | Unauthorized | Invalid/expired API token |
| 403 | Forbidden | Token lacks permissions |
| 429 | Rate Limited | Too many requests (wait & retry) |
| 500 | Server Error | Okta service issue |

## Rate Limiting

### Default Limits

- **Development org**: 10,000 requests/minute
- **Production org**: 10,000 requests/minute per tenant

### Rate Limit Headers

Every response includes:

```http
X-Rate-Limit-Limit: 10000
X-Rate-Limit-Remaining: 9995
X-Rate-Limit-Reset: 1613644274
```

### AuthCheck Behavior

- Runs one comparison at a time
- For 500 users with pagination: ~3 API calls
- For 1000 users: ~5 API calls
- No retry logic (intentionally simple for now)

## Common Filters

### By Status

```
# Active users only
filter=status eq "ACTIVE"

# All users (any status)
filter=status eq "ACTIVE" OR status eq "PROVISIONED" OR status eq "STAGED"

# Provisioned users
filter=status eq "PROVISIONED"
```

### By Attribute

```
# By login (email)
filter=profile.login eq "john@example.com"

# By name (partial match)
filter=profile.firstName eq "John"

# By email
filter=profile.email eq "john@example.com"

# Combine: Active users with "john" in name
filter=status eq "ACTIVE" AND profile.firstName eq "John"
```

### Date-Based

```
# Users created after specific date
filter=created gt "2024-01-01T00:00:00.000Z"

# Users who logged in recently
filter=lastLogin gt "2024-02-01T00:00:00.000Z"
```

## Testing Manually

### Using cURL

```bash
# Set up variables
ORG_URL="https://dev-12345678.okta.com"
API_TOKEN="00abcDEF1234567890ghijklmNOPQRS_tuvwxyz"

# Get all active users
curl -X GET \
  "${ORG_URL}/api/v1/users?filter=status%20eq%20%22ACTIVE%22&limit=200" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Accept: application/json" \
  | jq '.[] | .profile.login'

# Get specific user
curl -X GET \
  "${ORG_URL}/api/v1/users?filter=profile.login%20eq%20%22john.doe@example.com%22" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Accept: application/json" \
  | jq '.'
```

### Using Python

```python
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

org_url = os.getenv("OKTA_ORG_URL")
api_token = os.getenv("OKTA_API_TOKEN")

# Get all active users
client = httpx.Client(timeout=10)
response = client.get(
    f"{org_url}/api/v1/users",
    params={
        "filter": 'status eq "ACTIVE"',
        "limit": 200
    },
    headers={
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json"
    }
)

print(f"Status: {response.status_code}")
print(f"Users found: {len(response.json())}")

for user in response.json():
    print(f"  {user['profile']['login']}")
```

## Authentication Errors & Solutions

### Error: 401 Unauthorized

```json
{
  "errorCode": "E0000011",
  "errorSummary": "Invalid token provided",
  "errorLink": "E0000011",
  "errorId": "oae123..."
}
```

**Solutions:**
1. Check token is copied correctly (no extra spaces)
2. Verify token hasn't expired (tokens don't expire by default, but check Okta admin)
3. Create new token:
   - Admin Console → Security → API → Tokens
   - Delete old token
   - Create new one
   - Copy immediately

### Error: 403 Forbidden

```json
{
  "errorCode": "E0000006",
  "errorSummary": "You do not have permission to access the feature you are trying to use",
  "errorLink": "E0000006"
}
```

**Solutions:**
1. Verify your admin account has API access
2. Check API token was created by admin user
3. Verify token scope includes user read permissions

### Error: 429 Rate Limited

```json
{
  "errorCode": "E0000047",
  "errorSummary": "API call exceeded rate limit due to too many requests.",
  "errorLink": "E0000047"
}
```

**Solutions:**
1. Check `X-Rate-Limit-Reset` header
2. Wait that many seconds before retrying
3. Reduce request frequency
4. Contact Okta support if limits are too low

## Understanding the Response

### User Object Structure

```json
{
  "id": "00ub0oNGTSWTBKOLGLHO",           // Unique Okta ID
  "status": "ACTIVE",                      // User status
  "created": "2013-07-02T21:36:25.344Z",  // Account created date
  "activated": "2013-07-02T21:36:25.344Z",// Account activated date
  "statusChanged": "2013-07-02T21:36:25.344Z", // Last status change
  "lastLogin": "2024-02-17T10:30:00.000Z",// Last login time
  "lastUpdated": "2024-02-17T10:30:00.000Z", // Last profile update
  "passwordChanged": "2013-07-02T21:36:25.344Z", // Last password change
  "profile": {
    "firstName": "John",
    "lastName": "Doe",
    "email": "john.doe@example.com",      // Email address
    "login": "john.doe@example.com",      // ← AuthCheck uses this!
    "mobilePhone": null,
    "secondEmail": null
    // ... other custom attributes
  },
  "_links": {
    "self": {...},
    "activate": {...}
    // ... links for related operations
  }
}
```

## Performance Considerations

### Large Organizations

**Scenario**: 5000 active users

```
Calculations:
- Per request: 200 users
- Total requests: 5000 / 200 = 25 requests
- Estimated time: 25 requests × 0.5 sec per request = 12.5 seconds
- Rate limit impact: 25 / 10000 = 0.25% of daily limit
```

### Optimization

If you need faster results:
1. Filter by active users only (already done)
2. Limit attributes returned: `?attributes=profile.login`
3. Increase page size if supported: `&limit=500` (check Okta docs)

## Okta API Documentation

For more details, see official docs:
- [Okta Users API](https://developer.okta.com/docs/api/openapi/okta-management/management/tag/User/)
- [Filter Operations](https://developer.okta.com/docs/api/openapi/okta-management/management/tag/User/#tag/User/operation/listUsers)
- [Rate Limiting](https://developer.okta.com/docs/api/getting_started/rate-limits)

## Summary

What happens when you click "Compare All Users":

1. AuthCheck checks environment variables for Okta config
2. Validates org URL and API token
3. Makes request #1: `GET /api/v1/users?filter=status eq "ACTIVE"&limit=200`
4. Receives response with up to 200 users
5. Checks `Link` header for pagination
6. If more results exist, makes request #2 with `after` cursor
7. Repeats until no more results
8. Extracts `profile.login` from each user
9. Returns sorted list of all active users
10. Compares with other sources (AD, etc.)
11. Displays matrix showing who has accounts where

**Time to complete**: Usually 1-5 seconds depending on user count and network
