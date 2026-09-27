from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.rbac import Role, require_role
from app.services.audit_service import audit_service

router = APIRouter(prefix="/audit", tags=["Security & Audit"])

@router.get("/logs", response_model=List[Dict[str, Any]])
async def get_audit_trail(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    _role: str = Depends(require_role(Role.OPERATOR)),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves paginated audit log entries from the immutable cryptographic ledger.
    Authorized for Operator and Admin roles.
    """
    logs = await audit_service.query_logs(db, limit=limit, offset=offset, action=action, user_id=user_id)
    return [log.to_dict() for log in logs]

@router.get("/verify", response_model=Dict[str, Any])
async def verify_audit_ledger_integrity(
    _role: str = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Cryptographically verifies the SHA-256 hash chain of the audit trail.
    Detects any unauthorized record modifications, deletions, or sequence gaps.
    Authorized exclusively for Admin superusers.
    """
    return await audit_service.verify_chain_integrity(db)
