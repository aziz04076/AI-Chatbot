from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from app.config import settings

router = APIRouter(prefix="/models", tags=["Model Versioning"])

class SwitchModelRequest(BaseModel):
    model_name: str

class ModelListResponse(BaseModel):
    current_model: str
    available_models: List[str]

@router.get("", response_model=ModelListResponse)
async def list_models():
    """Lists fine-tuned model versions and current active checkpoint."""
    return ModelListResponse(
        current_model=settings.DEFAULT_MODEL,
        available_models=settings.AVAILABLE_MODELS
    )

@router.post("/switch")
async def switch_model(payload: SwitchModelRequest):
    """Dynamically switches active model version."""
    if payload.model_name in settings.AVAILABLE_MODELS:
        settings.DEFAULT_MODEL = payload.model_name
        return {"status": "success", "message": f"Active model switched to {payload.model_name}"}
    return {"status": "error", "message": f"Model {payload.model_name} not found in available checkpoints."}
