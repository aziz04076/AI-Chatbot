import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
from app.schemas.agent import TaskPlan, SubTask, AgentEvent
from app.services.multi_agent.planner import planner_agent
from app.services.multi_agent.agents import (
    InfraCalculationAgent,
    ResearchAgent,
    CodeArchitectAgent,
    BaseAgent
)
from app.core.rbac import can_execute_tool

logger = logging.getLogger("NexusAI-Orchestrator")

class MultiAgentOrchestrator:
    """
    Coordinates multi-agent planning, subtask dispatching, and streaming lifecycle events.
    """
    def __init__(self):
        self.planner = planner_agent
        self.agents: Dict[str, BaseAgent] = {
            "infra_calculation": InfraCalculationAgent(),
            "research": ResearchAgent(),
            "code_architect": CodeArchitectAgent()
        }

    async def execute_plan_stream(
        self,
        query: str,
        force_plan: bool = False,
        user_role: str = "operator"
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Executes multi-agent plan and yields real-time progress events with RBAC enforcement.
        """
        is_complex = force_plan or self.planner.is_complex_query(query)
        if not is_complex:
            # Simple query passes through
            return

        plan: TaskPlan = self.planner.create_plan(query)
        logger.info(f"Generated Multi-Agent Plan [{plan.plan_id}] with {len(plan.tasks)} subtasks for: {query} (user_role: {user_role})")

        # 1. Emit plan_created event
        yield AgentEvent(
            type="plan_created",
            plan_id=plan.plan_id,
            title=f"Plan formulated ({len(plan.tasks)} subtasks)",
            data={"plan": plan.model_dump()}
        )

        context: Dict[str, Any] = {}

        # 2. Sequential/Parallel execution respecting dependencies
        for task in plan.tasks:
            agent = self.agents.get(task.assigned_agent)
            if not agent:
                continue

            # RBAC Permission Check
            allowed, denial_reason = can_execute_tool(user_role, task.assigned_agent)
            if not allowed:
                task.status = "failed"
                task.output = denial_reason
                task.thought = f"Access check failed: Role '{user_role}' unauthorized for '{task.assigned_agent}'."
                yield AgentEvent(
                    type="agent_finish",
                    plan_id=plan.plan_id,
                    task_id=task.id,
                    agent=agent.name,
                    output=denial_reason,
                    data={"task": task.model_dump(), "error": "forbidden", "role": user_role}
                )
                continue

            # Update status to running & emit agent_start
            task.status = "running"
            yield AgentEvent(
                type="agent_start",
                plan_id=plan.plan_id,
                task_id=task.id,
                agent=agent.name,
                title=task.title,
                data={"assigned_agent": task.assigned_agent}
            )

            # Simulated reasoning delay for realistic live visualization
            await asyncio.sleep(0.35)

            # Execute Worker Agent
            try:
                thought, output = await agent.execute(task, context)
                task.thought = thought
                task.output = output
                task.status = "completed"

                # Store in context for dependent downstream agents
                context[task.assigned_agent] = output

                # Emit agent_thought
                yield AgentEvent(
                    type="agent_thought",
                    plan_id=plan.plan_id,
                    task_id=task.id,
                    agent=agent.name,
                    thought=thought
                )

                await asyncio.sleep(0.2)

                # Emit agent_finish
                yield AgentEvent(
                    type="agent_finish",
                    plan_id=plan.plan_id,
                    task_id=task.id,
                    agent=agent.name,
                    output=output,
                    data={"task": task.model_dump(), "structured_data": task.structured_data}
                )

            except Exception as e:
                logger.error(f"Error in {agent.name}: {e}")
                task.status = "failed"
                task.output = f"Subtask error: {e}"
                yield AgentEvent(
                    type="agent_finish",
                    plan_id=plan.plan_id,
                    task_id=task.id,
                    agent=agent.name,
                    output=task.output,
                    data={"task": task.model_dump(), "error": str(e)}
                )

    def extract_context_summary(self, plan: TaskPlan) -> str:
        """Assembles completed subtask outputs into a prompt injection block for synthesis."""
        sections = []
        for task in plan.tasks:
            if task.status == "completed" and task.output:
                sections.append(f"### Subtask Output [{task.assigned_agent.upper()}]:\n{task.output}")
        return "\n\n".join(sections)

multi_agent_orchestrator = MultiAgentOrchestrator()
