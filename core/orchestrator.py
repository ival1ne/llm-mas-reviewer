from time import perf_counter
from typing import Any, Optional, TypedDict

from agents.adaptive_reviewer import AdaptiveReviewer
from agents.coder import Coder
from agents.heavy_reviewer import HeavyReviewer
from agents.lightweight_reviewer import LightweightReviewer
from agents.planner import Planner


class WorkflowState(TypedDict):
    task: str
    reviewer_mode: str
    requirements: list[str]
    plan: list[str]
    steps: list[dict[str, Any]]
    current_step_index: int
    current_step: str
    candidate_output: dict[str, Any]
    review_result: Optional[dict[str, Any]]
    should_regenerate: bool
    current_retry_count: int
    max_regenerations: int
    planning_seconds: float
    current_generation_seconds: float
    current_review_seconds: float
    current_step_started_at: float
    run_started_at: float
    total_generation_seconds: float
    total_review_seconds: float


class Orchestrator:
    def __init__(self, reviewer_mode: str = "lightweight", max_regenerations: int = 1):
        self.coder = Coder()
        self.planner = Planner()
        self.reviewer_mode = reviewer_mode
        self.max_regenerations = max_regenerations
        self.reviewer = self._build_reviewer(reviewer_mode)
        self.graph = self._build_graph()

    def run(self, task: str):
        started_at = perf_counter()
        initial_state: WorkflowState = {
            "task": task,
            "reviewer_mode": self.reviewer_mode,
            "requirements": [],
            "plan": [],
            "steps": [],
            "current_step_index": 0,
            "current_step": "",
            "candidate_output": {},
            "review_result": None,
            "should_regenerate": False,
            "current_retry_count": 0,
            "max_regenerations": self.max_regenerations,
            "planning_seconds": 0.0,
            "current_generation_seconds": 0.0,
            "current_review_seconds": 0.0,
            "current_step_started_at": 0.0,
            "run_started_at": started_at,
            "total_generation_seconds": 0.0,
            "total_review_seconds": 0.0,
        }
        final_state = self.graph.invoke(initial_state)
        total_seconds = perf_counter() - started_at
        return {
            "task": final_state["task"],
            "reviewer_mode": final_state["reviewer_mode"],
            "requirements": final_state["requirements"],
            "plan": final_state["plan"],
            "steps": final_state["steps"],
            "timing": {
                "planning_seconds": round(final_state["planning_seconds"], 3),
                "generation_seconds": round(final_state["total_generation_seconds"], 3),
                "review_seconds": round(final_state["total_review_seconds"], 3),
                "total_seconds": round(total_seconds, 3),
            },
        }

    def _build_graph(self):
        try:
            from langgraph.graph import END, START, StateGraph
        except ImportError as exc:
            raise ImportError(
                "LangGraph is missing. Install langgraph to run the orchestrator."
            ) from exc

        graph_builder = StateGraph(WorkflowState)
        graph_builder.add_node("plan_task", self._plan_task_node)
        graph_builder.add_node("generate_step", self._generate_step_node)
        graph_builder.add_node("review_step", self._review_step_node)
        graph_builder.add_node("save_step", self._save_step_node)

        graph_builder.add_edge(START, "plan_task")
        graph_builder.add_conditional_edges(
            "plan_task",
            self._route_after_plan,
            {
                "generate_step": "generate_step",
                "end": END,
            },
        )
        graph_builder.add_conditional_edges(
            "generate_step",
            self._route_after_generation,
            {
                "review_step": "review_step",
                "save_step": "save_step",
            },
        )
        graph_builder.add_conditional_edges(
            "review_step",
            self._route_after_review,
            {
                "generate_step": "generate_step",
                "save_step": "save_step",
            },
        )
        graph_builder.add_conditional_edges(
            "save_step",
            self._route_after_save,
            {
                "generate_step": "generate_step",
                "end": END,
            },
        )

        return graph_builder.compile()

    def _plan_task_node(self, state: WorkflowState) -> WorkflowState:
        started_at = perf_counter()
        plan = self.planner.plan(state["task"])
        return {
            **state,
            "requirements": plan.get("requirements", []),
            "plan": plan.get("plan", []),
            "planning_seconds": perf_counter() - started_at,
        }

    def _generate_step_node(self, state: WorkflowState) -> WorkflowState:
        step = state["plan"][state["current_step_index"]]
        context = {
            "task": state["task"],
            "reviewer_mode": state["reviewer_mode"],
            "requirements": state["requirements"],
            "plan": state["plan"],
            "steps": state["steps"],
        }
        step_started_at = state["current_step_started_at"] or perf_counter()
        started_at = perf_counter()
        candidate_output = self.coder.generate_code(state["task"], step, context)
        generation_seconds = perf_counter() - started_at
        return {
            **state,
            "current_step": step,
            "candidate_output": candidate_output,
            "review_result": None,
            "should_regenerate": False,
            "current_generation_seconds": generation_seconds,
            "current_step_started_at": step_started_at,
            "total_generation_seconds": state["total_generation_seconds"] + generation_seconds,
        }

    def _review_step_node(self, state: WorkflowState) -> WorkflowState:
        if self.reviewer is None:
            return state

        context = {
            "task": state["task"],
            "reviewer_mode": state["reviewer_mode"],
            "requirements": state["requirements"],
            "plan": state["plan"],
            "steps": state["steps"],
        }
        started_at = perf_counter()
        review_result = self.reviewer.review(
            state["task"],
            state["current_step"],
            context,
            state["candidate_output"],
        )
        review_seconds = perf_counter() - started_at
        should_regenerate = (
            review_result.get("recommendation") == "regenerate"
            and state["current_retry_count"] < state["max_regenerations"]
        )
        return {
            **state,
            "review_result": review_result,
            "should_regenerate": should_regenerate,
            "current_retry_count": state["current_retry_count"] + int(should_regenerate),
            "current_review_seconds": review_seconds,
            "total_review_seconds": state["total_review_seconds"] + review_seconds,
        }

    def _save_step_node(self, state: WorkflowState) -> WorkflowState:
        candidate_output = state["candidate_output"]
        step_record = {
            "step_id": state["current_step_index"] + 1,
            "step_title": state["current_step"],
            "code": candidate_output.get("code", ""),
            "summary": candidate_output.get("summary", ""),
            "decisions": candidate_output.get("decisions", []),
            "artifacts": candidate_output.get("artifacts", []),
            "review": state["review_result"],
            "attempts": state["current_retry_count"] + 1,
            "timing": {
                "generation_seconds": round(state["current_generation_seconds"], 3),
                "review_seconds": round(state["current_review_seconds"], 3),
                "total_step_seconds": round(
                    perf_counter() - state["current_step_started_at"], 3
                ),
            },
        }
        steps = [*state["steps"], step_record]

        return {
            **state,
            "steps": steps,
            "current_step_index": state["current_step_index"] + 1,
            "current_step": "",
            "candidate_output": {},
            "review_result": None,
            "should_regenerate": False,
            "current_retry_count": 0,
            "current_generation_seconds": 0.0,
            "current_review_seconds": 0.0,
            "current_step_started_at": 0.0,
        }

    def _route_after_plan(self, state: WorkflowState) -> str:
        return "generate_step" if state["plan"] else "end"

    def _route_after_generation(self, state: WorkflowState) -> str:
        return "save_step" if state["reviewer_mode"] == "no_review" else "review_step"

    def _route_after_review(self, state: WorkflowState) -> str:
        return "generate_step" if state["should_regenerate"] else "save_step"

    def _route_after_save(self, state: WorkflowState) -> str:
        return "generate_step" if state["current_step_index"] < len(state["plan"]) else "end"

    def _build_reviewer(self, reviewer_mode: str):
        if reviewer_mode == "adaptive":
            return AdaptiveReviewer()
        if reviewer_mode == "heavy":
            return HeavyReviewer()
        if reviewer_mode == "lightweight":
            return LightweightReviewer()
        if reviewer_mode == "no_review":
            return None
        raise ValueError(
            "Unsupported reviewer mode. Use 'no_review', 'lightweight', 'heavy' or 'adaptive'."
        )
