import json

from core.llm_client import call_llm
from core.prompt_utils import compact_candidate_output, compact_steps
from prompts.prompts import heavy_reviewer_prompt


class HeavyReviewer:
    def review(self, task: str, step: str, context: dict, candidate_output: dict):
        prompt = heavy_reviewer_prompt(
            task=task,
            step=step,
            requirements=json.dumps(
                context.get("requirements", []), ensure_ascii=False, indent=2
            ),
            context=json.dumps(
                compact_steps(context.get("steps", []), limit=2),
                ensure_ascii=False,
                indent=2,
            ),
            candidate_output=json.dumps(
                compact_candidate_output(candidate_output), ensure_ascii=False, indent=2
            ),
        )
        try:
            response = call_llm(prompt)
        except Exception:
            response = ""

        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            parsed = {
                "aligned": False,
                "score": 0.0,
                "issues": ["Failed to parse heavy reviewer response"],
                "recommendation": "revise",
            }

        return {
            "reviewer_type": "heavy",
            "aligned": bool(parsed.get("aligned", False)),
            "score": float(parsed.get("score", 0.0)),
            "issues": parsed.get("issues", []),
            "recommendation": parsed.get("recommendation", "revise"),
        }
