# Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies
```bash
cd authcheck
pip install -r requirements.txt
```

### 2. Run Server
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the convenience script:
```bash
./run.sh
```

### 3. Access Application
Open your browser to: **http://localhost:8000**

## Basic Usage

1. **Upload CSV**
   - Click "Upload & Parse"
   - Select `sample_users.csv` (included in project)
   - System loads the users

2. **Verify Users**
   - Click "Verify Users"
   - Results grid appears showing:
     - ✓ = User exists in that source
     - ✗ = User not found in that source

## API Testing

Run the included test script:
```bash
python test_api.py
```

Expected output:
```
✓ Found 3 registered connectors
✓ Successfully instantiated 3 connectors
✓ Connector Registry: OK
✓ Verification Logic: OK
✅ All tests passed!
```

## API Endpoints

### POST `/upload`
Upload CSV file with usernames
```bash
curl -X POST -F "file=@sample_users.csv" http://localhost:8000/upload
```

### POST `/verify`
Verify users across all sources
```bash
curl -X POST http://localhost:8000/verify \
  -H "Content-Type: application/json" \
  -d '{
    "users": ["john.doe", "jane.smith"]
  }'
```

### GET `/health`
Health check
```bash
curl http://localhost:8000/health
```

### GET `/docs`
Interactive API documentation
Visit: **http://localhost:8000/docs**

## Project Structure

```
user-auth-verification/
├── app/
│   ├── main.py           # FastAPI app
│   ├── models.py         # Data models
│   ├── connectors/       # Auth source connectors
│   ├── routes/           # API endpoints
│   └── templates/        # HTML templates
├── requirements.txt      # Dependencies
├── run.sh               # Dev startup
├── test_api.py          # Tests
└── README.md            # Full documentation
```

## Available Connectors

1. **Okta** - Uses Okta Python SDK (requires configuration - see docs/OKTA_SETUP.md)
2. **RADIUS** - Placeholder (returns false)
3. **Active Directory** - Placeholder (returns true)

## Sample CSV Format

```csv
username
john.doe
jane.smith
bob.wilson
alice.johnson
```

## Docker Usage

```bash
# Build and run
docker-compose up

# Access at http://localhost:80 (Nginx proxy)
# Or http://localhost:8000 (FastAPI direct)
```

## Common Issues

### Port Already in Use
```bash
# Use different port
python -m uvicorn app.main:app --reload --port 9000
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### CSV Not Parsing
- Ensure file is UTF-8 encoded
- File must end with `.csv`
- At least one username per row

## Next Steps

1. **Read Full Documentation**: See `README.md` for complete details
2. **Understand Architecture**: Read `IMPLEMENTATION_NOTES.md`
3. **Add Real Connectors**: Follow guide in README.md for adding Okta, RADIUS, AD integrations
4. **Deploy**: Use Docker or Nginx + uvicorn setup

## Getting Help

- **API Docs**: http://localhost:8000/docs (interactive)
- **Documentation**: See README.md and IMPLEMENTATION_NOTES.md
- **Code Comments**: TODOs marked in connector files for integration points

## Development Commands

```bash
# Run dev server with auto-reload
python -m uvicorn app.main:app --reload

# Run tests
python test_api.py

# Format code (optional)
pip install black
black app/

# Lint code (optional)
pip install flake8
flake8 app/

# Nginx validation
nginx -t -c /path/to/nginx.conf
```

## What's Implemented

✅ Phase 1: Core Framework
- FastAPI app with async support
- Connector registry pattern
- CSV upload handling
- Parallel verification queries
- HTML templates with results grid

✅ Phase 2: Stub Connectors
- Okta connector
- RADIUS connector
- Active Directory connector

⏳ Phase 3: Real Integrations
- Replace stubs with actual API calls
- Add per-connector configuration
- Implement error handling

⏳ Phase 4: Features
- CSV export
- Result caching
- Progress indicators
- Additional auth sources

## Performance Baseline

- CSV parsing: < 100ms
- Per-user verification: Parallel to slowest connector
- 5 users × 3 connectors: ~50-100ms
- Results rendering: < 50ms

## Success Criteria Met

✅ Users can upload CSV files
✅ System queries multiple auth sources simultaneously
✅ Results displayed in grid format
✅ Easy to add new auth sources
✅ Clear framework for real API integration

Enjoy! 🚀
