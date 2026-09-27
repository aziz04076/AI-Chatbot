import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.audit import AuditLog

logger = logging.getLogger("NexusAI-AuditService")

GENESIS_HASH = "0" * 64

def format_timestamp(dt: Optional[datetime]) -> str:
    """Formats datetime deterministically to standard UTC string: YYYY-MM-DDTHH:MM:SSZ"""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def compute_audit_hash(
    sequence_number: int,
    timestamp_iso: str,
    user_id: str,
    user_role: str,
    action: str,
    resource: str,
    status: str,
    details: Optional[Dict[str, Any]],
    previous_hash: str
) -> str:
    """
    Computes deterministic SHA-256 digest over audit entry fields.
    Guarantees tamper-evident linkage across sequential blocks.
    """
    normalized_details = json.dumps(details or {}, sort_keys=True)
    payload = (
        f"{sequence_number}|{timestamp_iso}|{user_id}|{user_role}|"
        f"{action}|{resource}|{status}|{normalized_details}|{previous_hash}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

class AuditService:
    """
    High-assurance audit service providing immutable, tamper-evident record logging.
    """
    async def record_event(
        self,
        db: AsyncSession,
        action: str,
        resource: str,
        status: str = "SUCCESS",
        user_id: str = "guest_user",
        user_role: str = "viewer",
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Appends an immutable entry to the cryptographic audit hash chain.
        """
        # 1. Fetch latest sequence and previous hash
        stmt = select(AuditLog).order_by(desc(AuditLog.sequence_number)).limit(1)
        latest = (await db.execute(stmt)).scalar_one_or_none()

        if latest is None:
            sequence_number = 1
            previous_hash = GENESIS_HASH
        else:
            sequence_number = latest.sequence_number + 1
            previous_hash = latest.entry_hash

        now = datetime.now(timezone.utc)
        timestamp_iso = format_timestamp(now)

        # 2. Compute cryptographic SHA-256 entry hash
        entry_hash = compute_audit_hash(
            sequence_number=sequence_number,
            timestamp_iso=timestamp_iso,
            user_id=user_id,
            user_role=user_role,
            action=action,
            resource=resource,
            status=status,
            details=details,
            previous_hash=previous_hash
        )

        # 3. Persist audit log
        log_entry = AuditLog(
            sequence_number=sequence_number,
            timestamp=now,
            user_id=user_id,
            user_role=user_role,
            action=action,
            resource=resource,
            status=status,
            details=details or {},
            previous_hash=previous_hash,
            entry_hash=entry_hash
        )

        db.add(log_entry)
        await db.commit()
        await db.refresh(log_entry)
        logger.info(f"Audit log #{sequence_number} recorded: [{action}] {resource} -> {status} (hash: {entry_hash[:12]}...)")
        return log_entry

    async def verify_chain_integrity(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Traverses the full audit trail from genesis block to tip,
        cryptographically re-calculating hashes to detect tampering or record deletions.
        """
        stmt = select(AuditLog).order_by(AuditLog.sequence_number.asc())
        records = (await db.execute(stmt)).scalars().all()

        if not records:
            return {
                "is_valid": True,
                "total_records": 0,
                "verified_blocks": 0,
                "corrupted_entries": [],
                "genesis_hash": GENESIS_HASH,
                "latest_hash": None,
                "status": "HEALTHY_EMPTY"
            }

        corrupted = []
        expected_prev = GENESIS_HASH

        for idx, record in enumerate(records):
            # Check 1: Sequence continuity
            expected_seq = idx + 1
            if record.sequence_number != expected_seq:
                corrupted.append({
                    "sequence_number": record.sequence_number,
                    "id": record.id,
                    "reason": f"Sequence discontinuity: Expected {expected_seq}, found {record.sequence_number}"
                })

            # Check 2: Previous hash link
            if record.previous_hash != expected_prev:
                corrupted.append({
                    "sequence_number": record.sequence_number,
                    "id": record.id,
                    "reason": f"Previous hash mismatch: Expected {expected_prev}, got {record.previous_hash}"
                })

            # Check 3: Recomputed cryptographic hash matches stored hash
            timestamp_iso = format_timestamp(record.timestamp)
            recomputed = compute_audit_hash(
                sequence_number=record.sequence_number,
                timestamp_iso=timestamp_iso,
                user_id=record.user_id,
                user_role=record.user_role,
                action=record.action,
                resource=record.resource,
                status=record.status,
                details=record.details,
                previous_hash=record.previous_hash
            )

            if record.entry_hash != recomputed:
                corrupted.append({
                    "sequence_number": record.sequence_number,
                    "id": record.id,
                    "reason": f"Cryptographic tamper detected: Expected {recomputed}, recorded {record.entry_hash}"
                })

            expected_prev = record.entry_hash

        is_valid = len(corrupted) == 0
        return {
            "is_valid": is_valid,
            "total_records": len(records),
            "verified_blocks": len(records) - len(corrupted),
            "corrupted_entries": corrupted,
            "genesis_hash": GENESIS_HASH,
            "latest_hash": records[-1].entry_hash if records else None,
            "status": "VERIFIED_SECURE" if is_valid else "TAMPER_DETECTED"
        }

    async def query_logs(
        self,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        action: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[AuditLog]:
        """Queries audit log ledger with optional filtering."""
        stmt = select(AuditLog).order_by(desc(AuditLog.sequence_number))
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)
        stmt = stmt.limit(limit).offset(offset)
        return list((await db.execute(stmt)).scalars().all())

audit_service = AuditService()
