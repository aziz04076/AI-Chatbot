import pytest
from app.services.multi_agent.planner import planner_agent
from app.services.multi_agent.agents import InfraCalculationAgent, ResearchAgent, CodeArchitectAgent
from app.services.multi_agent.orchestrator import multi_agent_orchestrator
from app.schemas.agent import SubTask

def test_planner_complexity_detection():
    # Simple query should not trigger complex multi-agent plan
    assert not planner_agent.is_complex_query("hello")
    assert not planner_agent.is_complex_query("what is kubernetes")

    # Complex multi-domain query should trigger multi-agent plan
    complex_query = "Design a high-availability EKS cluster with 16 concurrent Llama-3-8B streams, calculate VRAM and compute cost, and generate Terraform and K8s PDB manifests."
    assert planner_agent.is_complex_query(complex_query)

def test_planner_subtask_generation():
    query = "Calculate VRAM for 16 concurrency in vLLM and generate Terraform EKS module with zero-downtime deployment."
    plan = planner_agent.create_plan(query)

    assert plan.plan_id.startswith("plan-")
    assert len(plan.tasks) >= 2
    assigned_roles = [t.assigned_agent for t in plan.tasks]
    assert "infra_calculation" in assigned_roles
    assert "code_architect" in assigned_roles

@pytest.mark.asyncio
async def test_infra_calculation_agent():
    agent = InfraCalculationAgent()
    task = SubTask(
        id="task-1",
        title="VRAM Calculation",
        assigned_agent="infra_calculation",
        input_prompt="Calculate VRAM requirement for Llama-3-8B with 4-bit AWQ and 16 concurrency and 4096 context."
    )
    thought, output = await agent.execute(task, {})
    assert "VRAM" in thought or "parameters" in thought
    assert "KV Cache" in output
    assert "Model Weights VRAM" in output
    assert "Recommended Cloud Instance" in output

@pytest.mark.asyncio
async def test_research_agent():
    agent = ResearchAgent()
    task = SubTask(
        id="task-2",
        title="Architecture Research",
        assigned_agent="research",
        input_prompt="Kubernetes production hardening and PodDisruptionBudget best practices."
    )
    thought, output = await agent.execute(task, {})
    assert len(thought) > 0
    assert "Operational Guidelines" in output or "PodDisruptionBudget" in output

@pytest.mark.asyncio
async def test_code_architect_agent():
    agent = CodeArchitectAgent()
    task = SubTask(
        id="task-3",
        title="Code Synthesis",
        assigned_agent="code_architect",
        input_prompt="Write Terraform EKS and Kubernetes PDB manifest."
    )
    thought, output = await agent.execute(task, {"infra_calculation": "Recommended instance: g5.2xlarge"})
    assert "Terraform" in output
    assert "PodDisruptionBudget" in output
    assert "minAvailable: 2" in output

@pytest.mark.asyncio
async def test_orchestrator_streaming_events():
    query = "Design an EKS cluster with 16 concurrent Llama-3-8B streams and calculate VRAM."
    events = []
    async for event in multi_agent_orchestrator.execute_plan_stream(query, force_plan=True):
        events.append(event)

    event_types = [e.type for e in events]
    assert "plan_created" in event_types
    assert "agent_start" in event_types
    assert "agent_thought" in event_types
    assert "agent_finish" in event_types
