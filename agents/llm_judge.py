import json

from core.llm_client import call_llm
from core.prompt_utils import compact_result_for_judge
from prompts.prompts import judge_prompt


class LLMJudge:
    def evaluate(self, task: str, result: dict):
        prompt = judge_prompt(
            task=task,
            result=compact_result_for_judge(result),
        )
        try:
            response = call_llm(prompt, max_tokens=350, timeout=60)
        except Exception as exc:
            return {
                "score": 0.0,
                "verdict": "poor",
                "strengths": [],
                "weaknesses": [f"Judge failed: {exc}"],
            }

        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            parsed = {
                "score": 0.0,
                "verdict": "poor",
                "strengths": [],
                "weaknesses": ["Failed to parse judge response"],
            }

        return {
            "score": float(parsed.get("score", 0.0)),
            "verdict": parsed.get("verdict", "poor"),
            "strengths": parsed.get("strengths", []),
            "weaknesses": parsed.get("weaknesses", []),
        }
