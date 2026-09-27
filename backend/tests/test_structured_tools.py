import pytest
from pydantic import ValidationError
from app.schemas.tool_outputs import (
    CalculatorToolResult,
    InfraSizingToolResult,
    ResearchToolResult,
    CodeArchitectToolResult,
    WebSearchToolResult
)
from app.schemas.agent import SubTask
from app.services.agent_service import AgentToolRegistry, agent_orchestrator
from app.services.multi_agent.agents import (
    InfraCalculationAgent,
    ResearchAgent,
    CodeArchitectAgent
)

def test_calculator_tool_result_schema():
    """Verifies CalculatorToolResult serialization and constraints."""
    res = CalculatorToolResult(
        expression="16 * 1024",
        result=16384.0,
        unit="MB",
        explanation="Multiplication of 16 GB to MB",
        status="success"
    )
    assert res.result == 16384.0
    assert res.status == "success"
    assert res.unit == "MB"
    dump = res.model_dump()
    assert dump["result"] == 16384.0

def test_infra_sizing_tool_result_constraints():
    """Verifies numerical constraints (concurrency >= 1, total_vram_gb >= 0)."""
    valid = InfraSizingToolResult(
        model_name="Meta-Llama-3-8B",
        precision="4-bit AWQ",
        weights_vram_gb=4.62,
        kv_cache_per_stream_gb=0.5,
        concurrency=16,
        overhead_gb=2.0,
        total_vram_gb=14.62,
        recommended_gpu="1x NVIDIA A10G",
        recommended_instance="g5.2xlarge"
    )
    assert valid.total_vram_gb == 14.62
    assert valid.concurrency == 16

    # Test concurrency < 1 triggers ValidationError
    with pytest.raises(ValidationError):
        InfraSizingToolResult(
            model_name="Meta-Llama-3-8B",
            precision="4-bit AWQ",
            weights_vram_gb=4.62,
            kv_cache_per_stream_gb=0.5,
            concurrency=0,  # Invalid: ge=1 constraint
            overhead_gb=2.0,
            total_vram_gb=14.62,
            recommended_gpu="1x NVIDIA A10G",
            recommended_instance="g5.2xlarge"
        )

def test_code_architect_tool_result_validator():
    """Verifies that empty code snippet is caught by field_validator."""
    # Valid code
    valid = CodeArchitectToolResult(
        iac_type="kubernetes",
        language="yaml",
        code_snippet="apiVersion: policy/v1\nkind: PodDisruptionBudget\n...",
        security_hardened=True,
        validation_checks=["PDB minAvailable: 2 verified"]
    )
    assert valid.security_hardened is True

    # Empty snippet must trigger ValidationError
    with pytest.raises(ValidationError):
        CodeArchitectToolResult(
            iac_type="terraform",
            language="hcl",
            code_snippet="   \n  ",
            security_hardened=True
        )

def test_research_tool_result_constraints():
    """Verifies ResearchToolResult validation and non-negative citation counts."""
    res = ResearchToolResult(
        query="EKS multi-AZ",
        citations_count=3,
        top_sources=["kubernetes_hardening.md"],
        key_findings=["Use topology spread constraints"],
        governance_rules=["Enforce minAvailable: 2"]
    )
    assert res.citations_count == 3
    assert len(res.top_sources) == 1

    with pytest.raises(ValidationError):
        ResearchToolResult(
            query="test",
            citations_count=-1  # Invalid: ge=0 constraint
        )

def test_agent_tool_registry_structured_calculate():
    """Verifies safe arithmetic parsing and Pydantic validation via AgentToolRegistry."""
    res = AgentToolRegistry.calculate_structured("8.03 * 0.5 + 2.0")
    assert isinstance(res, CalculatorToolResult)
    assert res.status == "success"
    assert abs(res.result - 6.015) < 0.001

    # Backward compatibility: raw string return
    raw = AgentToolRegistry.calculate("8.03 * 0.5 + 2.0")
    assert abs(float(raw) - 6.015) < 0.001

    # Error handling returns error status
    err_res = AgentToolRegistry.calculate_structured("/// invalid")
    assert err_res.status == "error"

@pytest.mark.asyncio
async def test_agent_orchestrator_execute_tool_structured():
    """Verifies agent_orchestrator.execute_tool yields structured_data payload."""
    result = await agent_orchestrator.execute_tool("calculator", "100 / 4 + 15")
    assert result["tool"] == "calculator"
    assert "structured_data" in result
    assert result["structured_data"]["result"] == 40.0
    assert result["structured_data"]["status"] == "success"

@pytest.mark.asyncio
async def test_multi_agent_structured_outputs():
    """Verifies that all three specialized agents generate verified Pydantic structured_data."""
    # 1. InfraCalculationAgent
    infra_agent = InfraCalculationAgent()
    subtask_infra = SubTask(
        id="task-1",
        title="Compute GPU Sizing",
        assigned_agent="infra_calculation",
        input_prompt="Calculate VRAM for Llama-3-8B 4-bit with 16 concurrency and 4096 context"
    )
    thought, output = await infra_agent.execute(subtask_infra, {})
    assert subtask_infra.structured_data is not None
    # Validate against schema
    sizing_result = InfraSizingToolResult(**subtask_infra.structured_data)
    assert sizing_result.concurrency == 16
    assert sizing_result.total_vram_gb > 0.0
    assert "NVIDIA" in sizing_result.recommended_gpu

    # 2. ResearchAgent
    research_agent = ResearchAgent()
    subtask_research = SubTask(
        id="task-2",
        title="Retrieve Governance Standards",
        assigned_agent="research",
        input_prompt="Kubernetes PodDisruptionBudget requirements"
    )
    thought, output = await research_agent.execute(subtask_research, {})
    assert subtask_research.structured_data is not None
    res_result = ResearchToolResult(**subtask_research.structured_data)
    assert res_result.citations_count >= 0
    assert len(res_result.governance_rules) > 0

    # 3. CodeArchitectAgent
    code_agent = CodeArchitectAgent()
    subtask_code = SubTask(
        id="task-3",
        title="Generate EKS and PDB Code",
        assigned_agent="code_architect",
        input_prompt="Generate Terraform EKS and Kubernetes PDB specs"
    )
    thought, output = await code_agent.execute(subtask_code, {"infra_calculation": output})
    assert subtask_code.structured_data is not None
    code_result = CodeArchitectToolResult(**subtask_code.structured_data)
    assert code_result.iac_type == "terraform"
    assert len(code_result.code_snippet) > 50
    assert code_result.security_hardened is True
    assert len(code_result.validation_checks) >= 3
