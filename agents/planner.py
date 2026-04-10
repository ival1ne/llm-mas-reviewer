from prompts.prompts import planner_prompt
from core.llm_client import call_llm
import json
class Planner():
    def plan(self, task: str):
        prompt = planner_prompt(task)
        response = call_llm(prompt)

        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            parsed = {
                "requirements": [],
                "plan": []
            }

        return parsed
