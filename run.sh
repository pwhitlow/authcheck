#!/bin/bash

# User Authentication Verification Tool - Development Server

set -e

echo "🚀 Starting User Authentication Verification Tool"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""

# Set SSL certificate path for macOS
export SSL_CERT_FILE=$(python3 -c "import certifi; print(certifi.where())" 2>/dev/null)
if [ -n "$SSL_CERT_FILE" ]; then
    echo "🔒 SSL certificates configured"
fi

echo "🌐 Starting FastAPI server on http://localhost:8000"
echo "📊 API docs available at http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the FastAPI development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
