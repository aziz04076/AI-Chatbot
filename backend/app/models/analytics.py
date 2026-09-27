import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

class AnalyticsLog(Base):
    __tablename__ = "analytics_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    endpoint = Column(String(100), nullable=False)
    query_snippet = Column(String(255), nullable=True)
    latency_ms = Column(Float, nullable=False)
    tokens_generated = Column(Integer, default=0)
    model_name = Column(String(100), nullable=True)
    status_code = Column(Integer, default=200)
    user_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String(36), ForeignKey("messages.id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False) # 1 = Thumbs Up, -1 = Thumbs Down
    comment = Column(Text, nullable=True)
    user_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    message = relationship("Message", back_populates="feedbacks")
