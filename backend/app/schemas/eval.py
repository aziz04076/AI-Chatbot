from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal

class BenchmarkQuery(BaseModel):
    """Ground truth definition for a held-out evaluation query."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    query: str
    category: str
    expected_sources: List[str]
    expected_keywords: List[str]
    unsupported_claims: List[str] = Field(default_factory=list)

class QueryEvalResult(BaseModel):
    """Audit evaluation result for an individual benchmark query."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    query: str
    category: str
    retrieved_sources: List[str]
    precision_at_k: float = Field(..., ge=0.0, le=1.0)
    recall_at_k: float = Field(..., ge=0.0, le=1.0)
    reciprocal_rank: float = Field(..., ge=0.0, le=1.0)
    grounded_score: float = Field(..., ge=0.0, le=1.0)
    hallucination_detected: bool
    latency_ms: float = Field(..., ge=0.0)
    status: Literal["passed", "flagged", "failed"]

class EvalBenchmarkReport(BaseModel):
    """Comprehensive evaluation benchmark report across held-out test suite."""
    model_config = ConfigDict(from_attributes=True)

    timestamp: str
    total_queries: int
    retrieval_precision_at_k: float = Field(..., ge=0.0, le=1.0)
    retrieval_recall_at_k: float = Field(..., ge=0.0, le=1.0)
    mean_reciprocal_rank: float = Field(..., ge=0.0, le=1.0)
    hallucination_rate: float = Field(..., ge=0.0, le=100.0)
    faithfulness_score: float = Field(..., ge=0.0, le=100.0)
    latency_p50_ms: float = Field(..., ge=0.0)
    latency_p95_ms: float = Field(..., ge=0.0)
    latency_p99_ms: float = Field(..., ge=0.0)
    composite_score: float = Field(..., ge=0.0, le=100.0)
    query_results: List[QueryEvalResult] = Field(default_factory=list)
