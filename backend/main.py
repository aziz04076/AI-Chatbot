"""
NexusAI - Production FastAPI Entrypoint for Local, Docker, and Vercel Serverless
"""
import sys
from pathlib import Path

# Ensure backend directory is in sys.path so 'app' packages resolve cleanly
backend_dir = str(Path(__file__).resolve().parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app

# Expose app for ASGI / Vercel Serverless runtime
__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
