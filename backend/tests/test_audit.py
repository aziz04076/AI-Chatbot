import pytest
from app.services.audit_service import compute_audit_hash, audit_service, GENESIS_HASH
from app.models.audit import AuditLog
from app.core.database import AsyncSessionLocal, init_db
from app.core.security import create_access_token
from sqlalchemy import delete
from httpx import AsyncClient, ASGITransport
from app.main import app

def test_compute_audit_hash_deterministic():
    h1 = compute_audit_hash(
        sequence_number=1,
        timestamp_iso="2026-09-27T12:00:00Z",
        user_id="user_123",
        user_role="operator",
        action="tool_execution",
        resource="tool:calculator",
        status="SUCCESS",
        details={"input": "2+2", "output": "4.0"},
        previous_hash=GENESIS_HASH
    )
    h2 = compute_audit_hash(
        sequence_number=1,
        timestamp_iso="2026-09-27T12:00:00Z",
        user_id="user_123",
        user_role="operator",
        action="tool_execution",
        resource="tool:calculator",
        status="SUCCESS",
        details={"input": "2+2", "output": "4.0"},
        previous_hash=GENESIS_HASH
    )
    assert h1 == h2
    assert len(h1) == 64

    # Any change in data produces completely different SHA-256 hash
    h3 = compute_audit_hash(
        sequence_number=1,
        timestamp_iso="2026-09-27T12:00:00Z",
        user_id="user_123",
        user_role="operator",
        action="tool_execution",
        resource="tool:calculator",
        status="SUCCESS",
        details={"input": "2+2", "output": "5.0"},  # Altered data
        previous_hash=GENESIS_HASH
    )
    assert h1 != h3

@pytest.mark.asyncio
async def test_audit_ledger_chain_and_verification():
    await init_db()
    async with AsyncSessionLocal() as db:
        await db.execute(delete(AuditLog))
        await db.commit()
        # Record Entry 1
        entry1 = await audit_service.record_event(
            db,
            action="auth_login",
            resource="system:auth",
            status="SUCCESS",
            user_id="admin_1",
            user_role="admin",
            details={"ip": "127.0.0.1"}
        )
        assert entry1.sequence_number >= 1
        assert len(entry1.entry_hash) == 64

        # Record Entry 2
        entry2 = await audit_service.record_event(
            db,
            action="tool_execution",
            resource="tool:infra_calculation",
            status="SUCCESS",
            user_id="admin_1",
            user_role="admin",
            details={"gpu": "A10G", "vram_gb": 24}
        )
        assert entry2.sequence_number == entry1.sequence_number + 1
        assert entry2.previous_hash == entry1.entry_hash

        # Verify chain integrity
        report = await audit_service.verify_chain_integrity(db)
        assert report["is_valid"] is True
        assert report["status"] == "VERIFIED_SECURE"
        assert len(report["corrupted_entries"]) == 0
        assert report["verified_blocks"] >= 2

@pytest.mark.asyncio
async def test_tamper_detection_flags_corrupted_record():
    await init_db()
    async with AsyncSessionLocal() as db:
        # Create a fresh record
        entry = await audit_service.record_event(
            db,
            action="test_action",
            resource="test_resource",
            status="SUCCESS",
            user_id="tamper_test_user",
            user_role="operator",
            details={"original": "legitimate_data"}
        )

        # Intentionally tamper with details in the database without updating hash
        entry.details = {"original": "tampered_by_malicious_actor"}
        db.add(entry)
        await db.commit()

        # Chain verification must detect the cryptographic discrepancy
        tamper_report = await audit_service.verify_chain_integrity(db)
        assert tamper_report["is_valid"] is False
        assert tamper_report["status"] == "TAMPER_DETECTED"
        assert len(tamper_report["corrupted_entries"]) > 0

        # Verify the compromised entry is flagged
        corrupted_seqs = [c["sequence_number"] for c in tamper_report["corrupted_entries"]]
        assert entry.sequence_number in corrupted_seqs

        # Repair back to legitimate content
        entry.details = {"original": "legitimate_data"}
        db.add(entry)
        await db.commit()

@pytest.mark.asyncio
async def test_audit_endpoints_rbac_authorization():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        viewer_token = create_access_token("viewer_user", role="viewer")
        operator_token = create_access_token("operator_user", role="operator")
        admin_token = create_access_token("admin_user", role="admin")

        # 1. /audit/logs: Viewer -> 403 Forbidden
        res_v_logs = await ac.get("/api/v1/audit/logs", headers={"Authorization": f"Bearer {viewer_token}"})
        assert res_v_logs.status_code == 403

        # 2. /audit/logs: Operator -> 200 OK
        res_op_logs = await ac.get("/api/v1/audit/logs", headers={"Authorization": f"Bearer {operator_token}"})
        assert res_op_logs.status_code == 200
        assert isinstance(res_op_logs.json(), list)

        # 3. /audit/verify: Operator -> 403 Forbidden (requires Admin)
        res_op_verify = await ac.get("/api/v1/audit/verify", headers={"Authorization": f"Bearer {operator_token}"})
        assert res_op_verify.status_code == 403

        # 4. /audit/verify: Admin -> 200 OK
        res_admin_verify = await ac.get("/api/v1/audit/verify", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_admin_verify.status_code == 200
        data = res_admin_verify.json()
        assert "is_valid" in data
        assert "verified_blocks" in data
