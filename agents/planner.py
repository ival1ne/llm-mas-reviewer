from prompts.prompts import planner_prompt
from core.llm_client import call_llm
class Planner():
    def plan(self, task: str):
        prompt = planner_prompt(task)
        response = call_llm(prompt)
        steps = []
        for line in response.splitlines():
            line = line.strip()
            if not line:
                continue
            if line[0].isdigit():
                parts = line.split(".", 1)
                if len(parts) == 2:
                    line = parts[1].strip()
            if line:
                steps.append(line)


        return steps
