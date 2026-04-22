from prompts.prompts import coder_prompt
from core.llm_client import call_llm
import json
class Coder():

    def generate_code(self,task: str, step: str, context: dict):
        structured_context = {
            "recent_steps": [
                {
                    "step_id": prev_step.get("step_id"),
                    "step_title": prev_step.get("step_title"),
                    "summary": prev_step.get("summary", ""),
                    "decisions": prev_step.get("decisions", [])[:5],
                    "artifacts": prev_step.get("artifacts", [])[:5],
                }
                for prev_step in context["steps"][-2:]
            ],
            "decision_history": [
                {
                    "step_id": prev_step.get("step_id"),
                    "step_title": prev_step.get("step_title"),
                    "decisions": prev_step.get("decisions", [])[:5]
                }
                for prev_step in context["steps"][-4:]
            ],
            "requirements": context.get("requirements", [])[:8],
        }

        prompt = coder_prompt(
            task=task,
            step=step,
            context=json.dumps(structured_context, ensure_ascii=False, indent=2)
        )
        response = call_llm(prompt, max_tokens=1400, timeout=120)
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            parsed = {
                "code": response,
                "summary": f"Failed to parse JSON for step: {step}",
                "decisions": [],
                "artifacts": []
            }
        return parsed
