from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime

class SystemHealth(BaseModel):
    gpu_available: bool
    gpu_name: str
    gpu_vram_used_gb: float
    gpu_vram_total_gb: float
    cpu_percent: float
    ram_used_gb: float
    ram_total_gb: float
    status: str

class TopicTrend(BaseModel):
    topic: str
    count: int
    percentage: float

class AnalyticsSummary(BaseModel):
    total_queries: int
    avg_latency_ms: float
    user_satisfaction_percent: float
    active_sessions_count: int
    system_health: SystemHealth
    top_topics: List[TopicTrend]
    daily_query_volume: List[Dict[str, Any]]
