def coder_prompt(task: str, step: str, context: dict):
    return f"""
You are a backend coding agent.

Your job is to implement ONLY the current step of the task.

Task:
{task}

Current step:
{step}

Previous steps:
{context}

Target stack:
- Python
- FastAPI
- PostgreSQL

Return ONLY valid JSON.
Do not use markdown.
Do not wrap the response in triple backticks.
Do not add explanations before or after JSON.

Use exactly this JSON schema:
{{
  "code": "string",
  "summary": "string",
  "decisions": ["string"],
  "artifacts": ["string"]
}}

Field requirements:
- "code": code for the current step
- "summary": short summary of what was implemented
- "decisions": architectural/implementation decisions made in this step
- "artifacts": files, modules, endpoints, or components created/modified in this step
"""


def planner_prompt(task: str):
    return f"""
    You are a software planning agent.
    Break the following backend development task into 3 to 6 implementation steps.

    Task:
    {task}

    Return only a numbered list of steps.
    """
