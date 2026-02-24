# AuthCheck - User Authentication Verification Tool

A web application for verifying user account existence across multiple authentication sources (Okta, RADIUS, Active Directory, and others to be added).

## Overview

This tool allows you to:
- Upload a CSV file containing usernames
- Query multiple authentication sources in parallel
- View results in a grid format showing which sources each user exists in
- Easily add new authentication sources as integration details become available

## Architecture

```
Browser (HTML/CSS/JS)
    ↓ HTTP
Nginx (Reverse Proxy)
    ↓
FastAPI Backend
├─ API Routes
├─ Connector Registry
├─ Query Logic
└─ Pluggable Connectors
   ├─ Okta
   ├─ RADIUS
   └─ Active Directory
```

### Key Features

- **Pluggable Connectors**: Add new authentication sources without changing core logic
- **Parallel Queries**: All auth sources queried simultaneously for performance
- **Extensible Design**: Framework ready for additional integrations
- **Simple Web UI**: No complex JavaScript, just a clean form and results grid

## Project Structure

```
authcheck/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── models.py            # Pydantic data models
│   ├── connectors/          # Auth source connectors
│   │   ├── __init__.py      # Registry
│   │   ├── base.py          # Abstract base class
│   │   ├── okta.py          # Okta connector
│   │   ├── radius.py        # RADIUS connector
│   │   └── active_directory.py  # AD connector
│   ├── routes/              # API endpoints
│   │   ├── upload.py        # CSV upload handler
│   │   └── query.py         # Verification logic
│   └── templates/           # HTML templates
│       ├── base.html
│       └── index.html
├── nginx/
│   └── nginx.conf           # Nginx configuration
├── requirements.txt         # Python dependencies
└── README.md
```

## Installation & Setup

### Prerequisites
- Python 3.9+
- pip
- (Optional) Nginx for reverse proxy

### Quick Start

1. **Clone and navigate to project**
   ```bash
   cd authcheck
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the FastAPI development server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Access the application**
   - Open browser and navigate to `http://localhost:8000`

## Usage

### Basic Workflow

1. **Prepare CSV File**
   - Single column with usernames
   - Optional header row (recognized headers: "username", "user", "email", "account")
   - Example:
     ```csv
     username
     john.doe
     jane.smith
     bob.wilson
     ```

2. **Upload CSV**
   - Click "Upload & Parse" button
   - Select your CSV file
   - System parses and displays loaded users

3. **Verify Users**
   - Click "Verify Users" button
   - System queries all available auth sources in parallel
   - Results displayed in grid format

4. **Interpret Results**
   - ✓ (green) = User exists in that source
   - ✗ (red) = User does not exist in that source

## API Endpoints

### POST `/upload`
Upload a CSV file containing usernames.

**Request:**
```
Content-Type: multipart/form-data
file: [CSV file]
```

**Response:**
```json
{
  "user_count": 3,
  "users": ["john.doe", "jane.smith", "bob.wilson"],
  "message": "Successfully parsed 3 users"
}
```

### POST `/verify`
Query all connectors to verify user existence.

**Request:**
```json
{
  "users": ["john.doe", "jane.smith", "bob.wilson"]
}
```

**Response:**
```json
{
  "users": ["john.doe", "jane.smith", "bob.wilson"],
  "sources": ["okta", "radius", "active_directory"],
  "results": {
    "john.doe": {
      "okta": true,
      "radius": false,
      "active_directory": true
    },
    "jane.smith": {
      "okta": true,
      "radius": true,
      "active_directory": false
    }
  },
  "timestamp": "2025-02-17T10:30:00"
}
```

### GET `/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

## Extending with New Authentication Sources

### To add a new connector (e.g., LDAP):

1. **Create new connector file** `app/connectors/ldap.py`

```python
from .base import BaseConnector

class LDAPConnector(BaseConnector):
    """LDAP authentication source connector."""

    async def authenticate_user(self, username: str) -> bool:
        """
        Check if user exists in LDAP.

        TODO: Implement actual LDAP integration
        """
        # Placeholder implementation
        return True

    def get_display_name(self) -> str:
        return "LDAP"

    def get_connector_id(self) -> str:
        return "ldap"

    def validate_config(self) -> bool:
        """Validate LDAP configuration."""
        # Check for required config like server address, bind DN, etc.
        return True
```

2. **Register in connector registry** `app/connectors/__init__.py`

```python
from .ldap import LDAPConnector

# In ConnectorRegistry._register_default_connectors():
self.register("ldap", LDAPConnector)
```

3. **Update configuration** (as needed)

The connector is now automatically available - no other changes required!

### Implementing Real API Calls

Once integration details are available for a connector:

1. Update the `authenticate_user()` method with actual API calls
2. Add required configuration fields to `validate_config()`
3. Update `.env` or config system with credentials/endpoints
4. Test with real data

## Configuration

### Okta Configuration

The Okta connector uses the Okta Python SDK with Private Key authentication. Create a configuration file (e.g., `~/.okta_config`):

```json
{
    "orgUrl": "https://your-org.okta.com",
    "authorizationMode": "PrivateKey",
    "clientId": "your_client_id",
    "scopes": ["okta.users.read", "okta.users.manage"],
    "privateKey": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
}
```

See `docs/OKTA_SETUP.md` for detailed setup instructions.

### Other Connectors

Environment variables or configuration dictionaries for other connectors:

```env
# RADIUS
RADIUS_SERVER=radius.example.com
RADIUS_SECRET=shared_secret

# Active Directory
AD_SERVER=ldap.example.com
AD_BASE_DN=DC=example,DC=com
AD_USERNAME=your_username
AD_PASSWORD=your_password
```

## Development

### Running Tests (when implemented)

```bash
pytest tests/
```

### Code Structure Notes

- **Connector Pattern**: All auth sources implement `BaseConnector` interface
- **Async Design**: FastAPI handles async queries for scalability
- **Registry Pattern**: Connectors auto-discovered and managed centrally
- **Simple Frontend**: HTML/CSS/JS with minimal dependencies

## Troubleshooting

### CSV Upload Fails
- Ensure file is valid UTF-8 encoded
- Check that file ends with `.csv`
- Verify at least one username per row

### Verification Hangs
- Check backend logs for connector timeouts
- Verify auth source connectivity
- Increase timeout values in `nginx.conf` if needed

### Nginx Configuration
To use Nginx as reverse proxy:

```bash
# Test configuration
nginx -t -c /path/to/nginx.conf

# Run Nginx
nginx -c /path/to/nginx.conf

# Reload configuration
nginx -s reload
```

## Implementation Phases

### Phase 1: Core Framework ✅
- FastAPI setup with async support
- Connector registry system
- Basic HTML templates
- CSV upload functionality
- Parallel verification queries

### Phase 2: Stub Connectors ✅
- Okta connector (placeholder)
- RADIUS connector (placeholder)
- Active Directory connector (placeholder)

### Phase 3: Real Integrations (Pending)
- Replace stub implementations with actual API calls
- Add error handling per connector
- Support connector-specific configuration
- Add timeout/retry logic

### Phase 4: Features (Pending)
- Progress indicators for long queries
- CSV export of results
- Result caching/history
- User filtering and sorting
- Additional auth sources as needed

## Support & Feedback

For issues or feedback, please report at: https://github.com/anthropics/claude-code/issues

## License

To be determined

## Changelog

### v1.0.0 (2025-02-17)
- Initial release with core framework
- Stub connectors for Okta, RADIUS, Active Directory
- CSV upload and verification endpoints
- Basic web UI with results grid
