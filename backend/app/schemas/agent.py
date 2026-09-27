from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Literal

TaskStatus = Literal["pending", "running", "completed", "failed"]
AgentRole = Literal["planner", "infra_calculation", "research", "code_architect"]

class SubTask(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    assigned_agent: AgentRole
    status: TaskStatus = "pending"
    dependencies: List[str] = Field(default_factory=list)
    input_prompt: str
    thought: Optional[str] = None
    output: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None

class TaskPlan(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan_id: str
    goal: str
    tasks: List[SubTask] = Field(default_factory=list)
    estimated_steps: int = 1

class AgentEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: Literal["plan_created", "agent_start", "agent_thought", "agent_tool_call", "agent_finish"]
    plan_id: Optional[str] = None
    task_id: Optional[str] = None
    agent: Optional[str] = None
    title: Optional[str] = None
    thought: Optional[str] = None
    output: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
