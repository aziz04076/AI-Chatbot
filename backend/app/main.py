import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.core.database import init_db
from app.core.redis import cache_manager
from app.services.rag_service import rag_service
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.voice import router as voice_router
from app.api.v1.files import router as files_router
from app.api.v1.models import router as models_router
from app.api.v1.audit import router as audit_router
from app.models.audit import AuditLog

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("NexusAI-Core")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    logger.info("Initiating NexusAI Backend Lifespan...")
    await init_db()
    logger.info("Database tables verified and initialized.")

    await cache_manager.initialize()

    # Pre-index domain knowledge documents
    rag_service.index_documents()
    logger.info("RAG vector index warmed up and ready.")

    yield

    # Shutdown sequence
    logger.info("NexusAI Backend shutdown complete.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Production-grade AI chatbot backend with WebSockets, LoRA fine-tuning, RAG, agentic tools & analytics.",
    lifespan=lifespan
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Timing & Telemetry Middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
    return response

# Register API routers
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(chat_router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_router, prefix=settings.API_V1_PREFIX)
app.include_router(voice_router, prefix=settings.API_V1_PREFIX)
app.include_router(files_router, prefix=settings.API_V1_PREFIX)
app.include_router(models_router, prefix=settings.API_V1_PREFIX)
app.include_router(audit_router, prefix=settings.API_V1_PREFIX)

@app.get("/health", tags=["Health"])
async def health_check():
    """Service health probe endpoint."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "active_model": settings.DEFAULT_MODEL,
        "inference_mode": settings.INFERENCE_MODE
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
