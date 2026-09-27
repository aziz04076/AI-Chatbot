from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.analytics_service import analytics_service
from app.services.eval_service import eval_service
from app.schemas.analytics import AnalyticsSummary
from app.schemas.eval import EvalBenchmarkReport
from app.core.circuit_breaker import llm_circuit_breaker
from app.core.rbac import Role, require_role
from typing import Dict, Any

router = APIRouter(prefix="/analytics", tags=["Analytics & Health"])

@router.get("/metrics", response_model=AnalyticsSummary)
async def get_analytics_metrics(db: AsyncSession = Depends(get_db)):
    """Returns comprehensive analytics summary, user satisfaction, and system health metrics."""
    return await analytics_service.get_summary(db)

@router.get("/circuit-breaker", response_model=Dict[str, Any])
async def get_circuit_breaker_status():
    """Returns real-time health, state, and resilience metrics for LLM Circuit Breaker."""
    return llm_circuit_breaker.get_metrics()

@router.get("/eval", response_model=EvalBenchmarkReport)
async def get_evaluation_report():
    """Returns the latest held-out test set evaluation benchmark report."""
    return eval_service.get_latest_report()

@router.post("/eval/run", response_model=EvalBenchmarkReport)
async def run_evaluation_benchmark(_role: str = Depends(require_role(Role.OPERATOR))):
    """Executes a fresh evaluation benchmark on the held-out test suite. Guarded by RBAC operator+."""
    return eval_service.run_benchmark()
