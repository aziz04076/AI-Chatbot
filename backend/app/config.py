from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    PROJECT_NAME: str = "NexusAI - Enterprise Cloud & DevOps AI Assistant"
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "nexus_secret_key_change_in_production_jwt_signature_9876543210"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{Path(__file__).resolve().parent.parent.as_posix()}/data/nexus.db"

    # Redis (with in-memory fallback)
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_EXPIRATION_SECONDS: int = 3600
    RATE_LIMIT_PER_MINUTE: int = 60

    # Inference Engine Configuration
    INFERENCE_MODE: str = "mock"
    LLM_API_BASE: str = "http://localhost:8000/v1"
    LLM_API_KEY: str = "dummy_or_openai_or_groq_key"
    DEFAULT_MODEL: str = "nexus-llama3-8b-v1"
    AVAILABLE_MODELS: List[str] = [
        "nexus-llama3-8b-v1",
        "nexus-mistral-7b-v2",
        "nexus-devops-specialist-qlora",
        "gpt-4o-mini"
    ]

    # RAG Settings
    CHROMA_PERSIST_DIRECTORY: str = str(Path(__file__).resolve().parent.parent / "data" / "chromadb")
    KNOWLEDGE_BASE_DIR: str = str(Path(__file__).resolve().parent.parent / "data" / "knowledge_base")
    RAG_TOP_K: int = 4
    SIMILARITY_THRESHOLD: float = 0.65

    # Speech / Audio
    WHISPER_MODEL: str = "base"
    TTS_VOICE: str = "en-US-ChristopherNeural"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "*"
    ]

settings = Settings()
