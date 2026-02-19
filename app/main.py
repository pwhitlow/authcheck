from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
import os
from pathlib import Path

from app.routes import upload, query, comparison

# Get the directory containing this file
BASE_DIR = Path(__file__).resolve().parent

# Create FastAPI app
app = FastAPI(
    title="AuthCheck - User Authentication Verification",
    description="Verify user accounts across multiple authentication sources",
    version="1.0.0",
)

# Set up Jinja2 templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Include routers
app.include_router(upload.router)
app.include_router(query.router)
app.include_router(comparison.router)


@app.get("/")
async def index():
    """Serve the main index page."""
    return FileResponse(str(BASE_DIR / "templates" / "index.html"), media_type="text/html")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
