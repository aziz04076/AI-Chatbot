import pytest
from app.core.rbac import (
    Role,
    normalize_role,
    has_role_permission,
    can_execute_tool,
    ROLE_HIERARCHY
)
from app.core.security import create_access_token
from app.services.agent_service import agent_orchestrator
from app.services.multi_agent import multi_agent_orchestrator
from httpx import AsyncClient, ASGITransport
from app.core.database import init_db
from app.main import app

def test_rbac_hierarchy_and_normalization():
    assert normalize_role("admin") == Role.ADMIN
    assert normalize_role("operator") == Role.OPERATOR
    assert normalize_role("viewer") == Role.VIEWER
    assert normalize_role("user") == Role.OPERATOR
    assert normalize_role("guest") == Role.VIEWER
    assert normalize_role(None) == Role.VIEWER

    # Role hierarchy: admin (3) > operator (2) > viewer (1)
    assert has_role_permission("admin", Role.ADMIN) is True
    assert has_role_permission("admin", Role.OPERATOR) is True
    assert has_role_permission("admin", Role.VIEWER) is True

    assert has_role_permission("operator", Role.ADMIN) is False
    assert has_role_permission("operator", Role.OPERATOR) is True
    assert has_role_permission("operator", Role.VIEWER) is True

    assert has_role_permission("viewer", Role.ADMIN) is False
    assert has_role_permission("viewer", Role.OPERATOR) is False
    assert has_role_permission("viewer", Role.VIEWER) is True

def test_tool_permission_matrix():
    # Sensitive infra calculation requires operator+
    allowed, err = can_execute_tool("viewer", "infra_calculation")
    assert allowed is False
    assert "Access Denied" in err

    allowed, err = can_execute_tool("operator", "infra_calculation")
    assert allowed is True
    assert err is None

    allowed, err = can_execute_tool("admin", "infra_calculation")
    assert allowed is True

    # Calculator requires operator+
    allowed, err = can_execute_tool("viewer", "calculator")
    assert allowed is False

    allowed, err = can_execute_tool("operator", "calculator")
    assert allowed is True

    # Research and Code tools accessible by viewer
    allowed, _ = can_execute_tool("viewer", "research")
    assert allowed is True
    allowed, _ = can_execute_tool("viewer", "code_architect")
    assert allowed is True

@pytest.mark.asyncio
async def test_agent_orchestrator_tool_rbac_enforcement():
    # Viewer attempting calculator tool
    viewer_result = await agent_orchestrator.execute_tool("calculator", "100 + 200", user_role="viewer")
    assert "Access Denied" in viewer_result["output"]
    assert viewer_result["structured_data"]["status"] == "forbidden"

    # Operator attempting calculator tool
    operator_result = await agent_orchestrator.execute_tool("calculator", "100 + 200", user_role="operator")
    assert operator_result["output"] == "300.0"
    assert operator_result["structured_data"]["status"] == "success"

@pytest.mark.asyncio
async def test_multi_agent_orchestrator_rbac_enforcement():
    query = "Calculate VRAM sizing for Llama-3-8B and design kubernetes deployment"

    # 1. As Viewer: Infra calculation subtask should be intercepted with access denied
    events_viewer = []
    async for event in multi_agent_orchestrator.execute_plan_stream(query, user_role="viewer"):
        events_viewer.append(event)

    infra_finish_viewer = [e for e in events_viewer if e.type == "agent_finish" and e.agent == "InfraCalculationAgent"]
    assert len(infra_finish_viewer) > 0
    assert "Access Denied" in infra_finish_viewer[0].output
    assert infra_finish_viewer[0].data.get("error") == "forbidden"

    # 2. As Operator: Infra calculation subtask runs and produces calculation
    events_operator = []
    async for event in multi_agent_orchestrator.execute_plan_stream(query, user_role="operator"):
        events_operator.append(event)

    infra_finish_operator = [e for e in events_operator if e.type == "agent_finish" and e.agent == "InfraCalculationAgent"]
    assert len(infra_finish_operator) > 0
    assert "Access Denied" not in infra_finish_operator[0].output
    assert "VRAM" in infra_finish_operator[0].output

@pytest.mark.asyncio
async def test_endpoint_rbac_eval_run():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Unauthenticated / Viewer -> 403 Forbidden
        viewer_token = create_access_token(subject="user_viewer", role="viewer")
        res_viewer = await ac.post("/api/v1/analytics/eval/run", headers={"Authorization": f"Bearer {viewer_token}"})
        assert res_viewer.status_code == 403
        assert "Insufficient permissions" in res_viewer.json()["detail"]

        # 2. Operator -> 200 OK
        operator_token = create_access_token(subject="user_operator", role="operator")
        res_operator = await ac.post("/api/v1/analytics/eval/run", headers={"Authorization": f"Bearer {operator_token}"})
        assert res_operator.status_code == 200
        assert "total_queries" in res_operator.json()

        # 3. Admin -> 200 OK
        admin_token = create_access_token(subject="user_admin", role="admin")
        res_admin = await ac.post("/api/v1/analytics/eval/run", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_admin.status_code == 200
