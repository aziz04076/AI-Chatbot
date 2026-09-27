import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, JSON
from app.core.database import Base

class AuditLog(Base):
    """
    Immutable, append-only audit ledger with cryptographic SHA-256 hash chaining.
    """
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sequence_number = Column(Integer, unique=True, index=True, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    user_id = Column(String(100), nullable=False, default="guest_user")
    user_role = Column(String(20), nullable=False, default="viewer")
    action = Column(String(100), nullable=False, index=True)
    resource = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="SUCCESS")
    details = Column(JSON, nullable=True)
    previous_hash = Column(String(64), nullable=False)
    entry_hash = Column(String(64), nullable=False, unique=True)

    def to_dict(self):
        return {
            "id": self.id,
            "sequence_number": self.sequence_number,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_id": self.user_id,
            "user_role": self.user_role,
            "action": self.action,
            "resource": self.resource,
            "status": self.status,
            "details": self.details,
            "previous_hash": self.previous_hash,
            "entry_hash": self.entry_hash
        }
