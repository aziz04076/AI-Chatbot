import pytest
import asyncio
import sys
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import init_db
from app.services.rag_service import rag_service

@pytest.fixture(scope="session", autouse=True)
def setup_test_suite():
    """Synchronous session fixture initializing database schema and RAG index."""
    asyncio.run(init_db())
    rag_service.index_documents()
