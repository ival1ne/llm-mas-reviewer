import json


def trim_text(text: str, limit: int = 1200) -> str:
    if not text:
        return ""
    return text if len(text) <= limit else text[:limit] + "\n...[truncated]"


def compact_candidate_output(candidate_output: dict) -> dict:
    return {
        "summary": candidate_output.get("summary", ""),
        "decisions": candidate_output.get("decisions", [])[:8],
        "artifacts": candidate_output.get("artifacts", [])[:8],
        "code_excerpt": trim_text(candidate_output.get("code", ""), 1200),
    }


def compact_steps(steps: list[dict], limit: int = 2) -> list[dict]:
    compacted = []
    for step in steps[-limit:]:
        compacted.append(
            {
                "step_id": step.get("step_id"),
                "step_title": step.get("step_title"),
                "summary": step.get("summary", ""),
                "decisions": step.get("decisions", [])[:6],
                "artifacts": step.get("artifacts", [])[:6],
                "review": {
                    "aligned": step.get("review", {}).get("aligned")
                    if step.get("review")
                    else None,
                    "score": step.get("review", {}).get("score")
                    if step.get("review")
                    else None,
                    "recommendation": step.get("review", {}).get("recommendation")
                    if step.get("review")
                    else None,
                },
            }
        )
    return compacted


def compact_result_for_judge(result: dict) -> str:
    compact_result = {
        "task": result.get("task"),
        "reviewer_mode": result.get("reviewer_mode"),
        "requirements": result.get("requirements", [])[:8],
        "plan": result.get("plan", [])[:8],
        "steps": compact_steps(result.get("steps", []), limit=3),
        "timing": result.get("timing", {}),
    }
    return json.dumps(compact_result, ensure_ascii=False, indent=2)
