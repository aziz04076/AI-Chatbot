from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    model_name: Optional[str] = "nexus-llama3-8b-v1"
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = True
    use_rag: Optional[bool] = True
    use_tools: Optional[bool] = True

class Citation(BaseModel):
    source: str
    snippet: str
    similarity: float
    retrieval_method: Optional[str] = "hybrid"
    bm25_rank: Optional[int] = None
    vector_rank: Optional[int] = None

class ChatResponse(BaseModel):
    message_id: str
    conversation_id: str
    content: str
    confidence_score: float
    model_name: str
    follow_ups: List[str] = []
    citations: List[Citation] = []
    latency_ms: float
    tokens_generated: int
    trace_id: Optional[str] = None
    traceparent: Optional[str] = None
    trace_spans: Optional[List[Dict[str, Any]]] = None

class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    confidence_score: Optional[float] = None
    model_name: Optional[str] = None
    created_at: datetime

class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[MessageOut] = []

class FeedbackCreate(BaseModel):
    message_id: str
    rating: int = Field(..., description="1 for positive, -1 for negative")
    comment: Optional[str] = None
