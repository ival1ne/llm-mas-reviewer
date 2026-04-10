from prompts.prompts import coder_prompt
from core.llm_client import call_llm
import json


def extract_json_text(raw_text: str) -> str:
    text = raw_text.strip()

    if text.startswith("```json"):
        text = text[len("```json"):].strip()
    elif text.startswith("```"):
        text = text[len("```"):].strip()

    if text.endswith("```"):
        text = text[:-3].strip()

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    return text


class Coder:
    def generate_code(self, task: str, step: str, context: dict):
        prompt = coder_prompt(
            task=task,
            step=step,
            context=context["steps"][-2:]
        )

        response = call_llm(prompt)
        cleaned_response = extract_json_text(response)

        try:
            parsed = json.loads(cleaned_response)

            if not isinstance(parsed, dict):
                raise ValueError("Parsed response is not a dict")

            parsed.setdefault("code", "")
            parsed.setdefault("summary", f"Completed: {step}")
            parsed.setdefault("decisions", [])
            parsed.setdefault("artifacts", [])

            if not isinstance(parsed["decisions"], list):
                parsed["decisions"] = []
            if not isinstance(parsed["artifacts"], list):
                parsed["artifacts"] = []

        except (json.JSONDecodeError, ValueError) as e:
            print("\n=== RAW LLM RESPONSE ===")
            print(response)
            print("=== END RAW RESPONSE ===\n")
            print(f"JSON parse error: {e}")

            parsed = {
                "code": response,
                "summary": f"Failed to parse JSON for step: {step}",
                "decisions": [],
                "artifacts": []
            }

        return parsed
