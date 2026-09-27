from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Literal, Dict, Any

class CalculatorToolResult(BaseModel):
    """Structured validated output for arithmetic and sizing calculations."""
    model_config = ConfigDict(from_attributes=True)

    expression: str
    result: float
    unit: Optional[str] = None
    explanation: str
    status: Literal["success", "error"] = "success"

class InfraSizingToolResult(BaseModel):
    """Structured validated output for GPU VRAM and cloud compute sizing."""
    model_config = ConfigDict(from_attributes=True)

    model_name: str = "Meta-Llama-3-8B"
    precision: str
    weights_vram_gb: float = Field(..., ge=0.0)
    kv_cache_per_stream_gb: float = Field(..., ge=0.0)
    concurrency: int = Field(..., ge=1)
    overhead_gb: float = Field(default=2.0, ge=0.0)
    total_vram_gb: float = Field(..., ge=0.0)
    recommended_gpu: str
    recommended_instance: str

class ResearchToolResult(BaseModel):
    """Structured validated output for internal architecture governance retrieval."""
    model_config = ConfigDict(from_attributes=True)

    query: str
    citations_count: int = Field(..., ge=0)
    top_sources: List[str] = Field(default_factory=list)
    key_findings: List[str] = Field(default_factory=list)
    governance_rules: List[str] = Field(default_factory=list)

class CodeArchitectToolResult(BaseModel):
    """Structured validated output for Infrastructure as Code generation."""
    model_config = ConfigDict(from_attributes=True)

    iac_type: Literal["terraform", "kubernetes", "helm", "istio", "python"]
    language: str
    code_snippet: str
    security_hardened: bool = True
    validation_checks: List[str] = Field(default_factory=list)

    @field_validator("code_snippet")
    @classmethod
    def validate_code_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Generated code snippet cannot be empty")
        return v

class WebSearchToolResult(BaseModel):
    """Structured validated output for web search retrieval."""
    model_config = ConfigDict(from_attributes=True)

    query: str
    abstract: str
    related_topics: List[str] = Field(default_factory=list)
    verified: bool = True
