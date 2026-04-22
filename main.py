from core.orchestrator import Orchestrator
from agents.llm_judge import LLMJudge
import argparse
import json
import os

def load_task(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_result(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_existing_result(path: str):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def resolve_log_path(reviewer_mode: str) -> str:
    if reviewer_mode == "no_review":
        return "results/no_review_logs.json"
    if reviewer_mode == "adaptive":
        return "results/adaptive_logs.json"
    if reviewer_mode == "heavy":
        return "results/heavy_logs.json"
    if reviewer_mode == "lightweight":
        return "results/lightweight_logs.json"
    raise ValueError(
        "Unsupported reviewer mode. Use 'no_review', 'lightweight', 'heavy' or 'adaptive'."
    )

def build_task_level_summary(run_logs: list[dict]) -> list[dict]:
    task_summaries = []
    for item in run_logs:
        judge = item.get("judge") or {}
        timing = item["result"].get("timing", {})
        adaptive_heavy_steps = sum(
            1
            for step in item["result"].get("steps", [])
            if (step.get("review") or {}).get("path") == "lightweight_then_heavy"
        )
        task_summaries.append(
            {
                "task_id": item.get("task_id"),
                "total_seconds": timing.get("total_seconds"),
                "review_seconds": timing.get("review_seconds"),
                "judge_score": judge.get("score"),
                "judge_verdict": judge.get("verdict"),
                "adaptive_heavy_steps": adaptive_heavy_steps,
            }
        )
    return task_summaries

def update_comparison_log(
    comparison_path: str,
    reviewer_mode: str,
    tasks_path: str,
    summary: dict,
    run_logs: list[dict],
) -> None:
    comparison_data = load_existing_result(comparison_path)
    comparison_data.setdefault("tasks_path", tasks_path)
    comparison_data.setdefault("modes", {})
    comparison_data["tasks_path"] = tasks_path
    comparison_data["modes"][reviewer_mode] = {
        "summary": summary,
        "tasks": build_task_level_summary(run_logs),
    }
    save_result(comparison_path, comparison_data)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reviewer",
        choices=["no_review", "lightweight", "heavy", "adaptive"],
        default="lightweight",
        help="Reviewer algorithm to use for the run.",
    )
    parser.add_argument(
        "--max-regenerations",
        type=int,
        default=1,
        help="Maximum number of reviewer-triggered regenerations per step.",
    )
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Run LLM-as-a-judge on final outputs.",
    )
    parser.add_argument(
        "--tasks",
        default="tasks/tasks.json",
        help="Path to the task list JSON file.",
    )
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    tasks = load_task(args.tasks)
    log_path = resolve_log_path(args.reviewer)
    comparison_path = "results/comparison_logs.json"
    run_logs = []
    judge = LLMJudge() if args.judge else None

    for task_data in tasks:
        orchestrator = Orchestrator(
            reviewer_mode=args.reviewer,
            max_regenerations=args.max_regenerations,
        )
        result = orchestrator.run(task_data["task"])
        judge_result = judge.evaluate(task_data["task"], result) if judge else None
        run_logs.append(
            {
                "task_id": task_data.get("id"),
                "reviewer_mode": args.reviewer,
                "judge": judge_result,
                "result": result,
            }
        )

    summary = {
        "reviewer_mode": args.reviewer,
        "tasks_count": len(run_logs),
        "avg_total_seconds": round(
            sum(item["result"]["timing"]["total_seconds"] for item in run_logs)
            / len(run_logs),
            3,
        )
        if run_logs
        else 0.0,
        "avg_review_seconds": round(
            sum(item["result"]["timing"]["review_seconds"] for item in run_logs)
            / len(run_logs),
            3,
        )
        if run_logs
        else 0.0,
        "avg_judge_score": round(
            sum(item["judge"]["score"] for item in run_logs if item["judge"] is not None)
            / len([item for item in run_logs if item["judge"] is not None]),
            3,
        )
        if any(item["judge"] is not None for item in run_logs)
        else None,
        "adaptive_heavy_trigger_rate": round(
            sum(
                1
                for item in run_logs
                for step in item["result"].get("steps", [])
                if (step.get("review") or {}).get("path") == "lightweight_then_heavy"
            )
            / max(
                1,
                sum(len(item["result"].get("steps", [])) for item in run_logs),
            ),
            3,
        )
        if args.reviewer == "adaptive"
        else None,
    }

    save_result(log_path, {"summary": summary, "runs": run_logs})
    update_comparison_log(
        comparison_path=comparison_path,
        reviewer_mode=args.reviewer,
        tasks_path=args.tasks,
        summary=summary,
        run_logs=run_logs,
    )
    print(f"Run completed. Logs saved to {log_path}")
