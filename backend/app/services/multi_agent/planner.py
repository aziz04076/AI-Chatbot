import uuid
import logging
from typing import Optional
from app.schemas.agent import TaskPlan, SubTask

logger = logging.getLogger("NexusAI-Planner")

class PlannerAgent:
    """
    Decomposes complex architectural queries into coordinated subtask DAG plans.
    """
    def is_complex_query(self, query: str) -> bool:
        """Determines if query warrants multi-agent decomposition."""
        lower = query.lower()
        # Multi-intent triggers
        has_sizing = any(w in lower for w in ["vram", "sizing", "calculate", "memory", "concurrency", "cost"])
        has_infra = any(w in lower for w in ["eks", "kubernetes", "k8s", "cluster", "pdb", "pod", "node", "terraform"])
        has_code = any(w in lower for w in ["code", "manifest", "yaml", "terraform", "generate", "write"])
        has_research = any(w in lower for w in ["best practice", "zero-trust", "architecture", "design", "how to", "security"])

        # If query combines 2 or more distinct aspects
        aspects = sum([bool(has_sizing), bool(has_infra), bool(has_code), bool(has_research)])
        return aspects >= 2 or len(query.split()) > 15

    def create_plan(self, query: str) -> TaskPlan:
        """Constructs an execution plan with assigned specialized agents."""
        plan_id = f"plan-{uuid.uuid4().hex[:8]}"
        lower = query.lower()
        tasks = []

        has_calc = any(w in lower for w in ["calculate", "vram", "memory", "sizing", "concurrency", "cost", "kv cache"])
        has_code = any(w in lower for w in ["terraform", "yaml", "manifest", "k8s", "kubernetes", "code", "deploy"])
        has_research = any(w in lower for w in ["architecture", "best practice", "security", "zero-trust", "vllm", "design"])

        step_idx = 1
        calc_task_id = None
        research_task_id = None

        # 1. Calculation Subtask if required
        if has_calc:
            calc_task_id = f"task-{step_idx}"
            tasks.append(SubTask(
                id=calc_task_id,
                title="GPU VRAM & KV Cache Sizing Analysis",
                assigned_agent="infra_calculation",
                status="pending",
                dependencies=[],
                input_prompt=query
            ))
            step_idx += 1

        # 2. Research Subtask
        if has_research or not has_code:
            research_task_id = f"task-{step_idx}"
            tasks.append(SubTask(
                id=research_task_id,
                title="Cloud Architecture & Governance Benchmarking",
                assigned_agent="research",
                status="pending",
                dependencies=[],
                input_prompt=query
            ))
            step_idx += 1

        # 3. Code Generation Subtask (depends on calculation if present)
        if has_code or (not has_calc and not has_research):
            code_task_id = f"task-{step_idx}"
            deps = [calc_task_id] if calc_task_id else []
            tasks.append(SubTask(
                id=code_task_id,
                title="Production Infrastructure as Code Synthesis",
                assigned_agent="code_architect",
                status="pending",
                dependencies=deps,
                input_prompt=query
            ))
            step_idx += 1

        # Fallback if no specific trigger fired
        if not tasks:
            tasks.append(SubTask(
                id="task-1",
                title="Domain Knowledge Architecture Evaluation",
                assigned_agent="research",
                status="pending",
                dependencies=[],
                input_prompt=query
            ))

        return TaskPlan(
            plan_id=plan_id,
            goal=query,
            tasks=tasks,
            estimated_steps=len(tasks)
        )

planner_agent = PlannerAgent()
