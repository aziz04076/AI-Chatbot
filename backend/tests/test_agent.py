import pytest
from app.services.agent_service import agent_orchestrator, AgentToolRegistry

def test_calculator_tool():
    res = AgentToolRegistry.calculate("8.03 * 0.5 + 2.0")
    val = float(res)
    assert abs(val - 6.015) < 0.001

def test_agent_tool_detection():
    # Calculation detection
    plan = agent_orchestrator.detect_tool_need("Calculate 16 * 1024 / 8")
    assert plan is not None
    assert plan["tool"] == "calculator"

    # Knowledge retrieval detection
    plan_k8s = agent_orchestrator.detect_tool_need("What is the best practice for kubernetes pod disruption?")
    assert plan_k8s is not None
    assert plan_k8s["tool"] == "knowledge_retriever"
