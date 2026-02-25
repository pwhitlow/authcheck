# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AuthCheck is a FastAPI-based authentication verification tool that checks user existence across multiple authentication sources (Okta, RADIUS, Active Directory). The system is designed around a pluggable connector architecture where authentication sources are queried in parallel using async/await patterns.

## Development Commands

### Running the Application

```bash
# Quick start with auto-setup (creates venv, installs deps, runs server)
./run.sh

# Or manually with uvicorn
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Using Docker
docker-compose up
```

### Testing

```bash
# Run integration tests
python test_api.py

# Test with sample CSV
# 1. Start server (see above)
# 2. Visit http://localhost:8000
# 3. Upload sample_users.csv
```

### API Documentation

Visit http://localhost:8000/docs for interactive Swagger UI documentation.

## Architecture

### Connector Pattern (Critical to Understand)

The entire system is built around a **pluggable connector pattern** using a registry system:

1. **BaseConnector** (`app/connectors/base.py`): Abstract base class defining the interface
   - `authenticate_user(username)`: Check if user exists (required)
   - `get_all_users()`: Enumerate all users (optional)
   - `get_display_name()`: Human-readable name (required)
   - `get_connector_id()`: Unique ID (required)
   - `validate_config()`: Validate connector config (optional)

2. **ConnectorRegistry** (`app/connectors/__init__.py`): Central registry managing all connectors
   - Singleton pattern via `get_registry()`
   - Auto-registers default connectors on init
   - Provides `get_all_connectors()` for parallel queries

3. **Individual Connectors**: Each auth source implements BaseConnector
   - `app/connectors/okta.py`
   - `app/connectors/radius.py`
   - `app/connectors/active_directory.py`

**Important**: Currently all connectors are stubs returning placeholder data. Phase 3 implementation will replace stubs with real API calls.

### Async/Await Design

All connector queries use async/await for parallel execution:

```python
# Bad: Sequential queries (slow)
for connector in connectors:
    result = await connector.authenticate_user(username)

# Good: Parallel queries (fast)
tasks = [connector.authenticate_user(username) for connector in connectors]
results = await asyncio.gather(*tasks)
```

This pattern is used in:
- `app/routes/query.py`: User verification endpoint
- `app/routes/comparison.py`: Cross-source user comparison

### Request Flow

```
Browser → Nginx (port 80) → FastAPI (port 8000)
                              ↓
                         Route Handler
                              ↓
                      ConnectorRegistry
                              ↓
            [Okta, RADIUS, AD] ← Parallel async queries
                              ↓
                         JSON Response
```

## Adding New Authentication Sources

To add a new connector (e.g., LDAP):

1. **Create connector file** `app/connectors/ldap.py`:

```python
from .base import BaseConnector

class LDAPConnector(BaseConnector):
    async def authenticate_user(self, username: str) -> bool:
        # Implement LDAP query
        # Access config: self.config.get('ldap_server')
        # See okta.py for example of real implementation
        return True

    def get_display_name(self) -> str:
        return "LDAP"

    def get_connector_id(self) -> str:
        return "ldap"

    def validate_config(self) -> bool:
        return 'ldap_server' in self.config
```

2. **Register in** `app/connectors/__init__.py`:

```python
from .ldap import LDAPConnector

# In ConnectorRegistry._register_default_connectors():
self.register("ldap", LDAPConnector)
```

3. **Done!** No other changes needed. The connector will automatically:
   - Appear in `/verify` endpoint results
   - Be included in `/compare` endpoint
   - Show up in the web UI grid

## Key Files and Their Purpose

- `app/main.py`: FastAPI app initialization, route registration, health endpoint
- `app/models.py`: Pydantic models for request/response validation
- `app/routes/upload.py`: CSV file upload and parsing
- `app/routes/query.py`: User verification across connectors (POST /verify)
- `app/routes/comparison.py`: Cross-source user comparison (GET /compare)
- `app/connectors/__init__.py`: Connector registry (singleton pattern)
- `app/connectors/base.py`: Abstract base class for all connectors

## API Endpoints

- `POST /upload`: Upload CSV with usernames, returns parsed user list
- `POST /verify`: Verify users across all sources, returns grid results
- `GET /compare`: Enumerate and compare users from all sources (requires connector support)
- `GET /health`: Health check
- `GET /docs`: Swagger UI

## Important Patterns

### 1. Registry Pattern
The connector registry allows dynamic addition of new auth sources without modifying core verification logic. New connectors are auto-discovered and included in all queries.

### 2. Async Parallel Queries
All connector queries execute in parallel using `asyncio.gather()`. Never query connectors sequentially unless there's a dependency between queries.

### 3. Error Handling in Connectors
When implementing real connectors, handle errors within the connector and return `False` for authentication failures. Don't let exceptions bubble up unless it's a critical failure.

### 4. Config Pattern
Connectors receive config dict in `__init__`. For Okta, use the SDK configuration format (JSON with orgUrl, authorizationMode, clientId, scopes, privateKey). For other connectors, use environment variables or config dicts as appropriate.

## Current Implementation Status

**Phase 1 & 2 (Complete)**:
- Core FastAPI framework
- Connector registry system
- CSV upload/parsing
- Parallel verification
- Stub connectors (return hardcoded values)

**Phase 3 (In Progress)**:
- Okta connector: **COMPLETE** - Uses Okta Python SDK with Private Key authentication and full pagination
- RADIUS connector: **PENDING** - Stub implementation
- Active Directory connector: **PENDING** - Stub implementation
- Proper error handling and timeouts
- Retry logic for failed queries

**When implementing remaining connectors**: Update individual connector files (radius.py, active_directory.py) with real implementations. The registry and routing logic requires no changes.

## Common Tasks

### Debugging Connector Issues
Check if connector is registered:
```python
from app.connectors import get_registry
registry = get_registry()
print(registry.list_connector_ids())  # Should include your connector
```

### Testing Individual Connectors
```python
from app.connectors import get_registry
registry = get_registry()
connector = registry.get_connector("okta")
result = await connector.authenticate_user("test.user")
```

### Viewing Logs
FastAPI logs go to stdout. Use `--log-level debug` for verbose output:
```bash
uvicorn app.main:app --reload --log-level debug
```

## Important Notes

- **Async Required**: All connector methods that do I/O must be async
- **Connector IDs**: Must be unique, lowercase, no spaces
- **No Global State**: Each connector instance should be independent
- **Config Validation**: Implement `validate_config()` to check for required configuration before queries
- **Enumeration Optional**: Only implement `get_all_users()` if the auth source supports user listing
- **Okta SDK**: The Okta connector uses the official Okta Python SDK (`from okta.client import Client`), not direct API calls
- **Reference Implementation**: See `app/connectors/okta.py` for a complete working example of a real connector implementation
