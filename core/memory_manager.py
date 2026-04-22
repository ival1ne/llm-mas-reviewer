class Memory_manager():
    def __init__(self, task: str):
        self.state = {
            "task" : task,
            "reviewer_mode": None,
            "requirements" : [],
            "plan" : [],
            "steps" : []
        }

    def set_reviewer_mode(self, reviewer_mode: str):
        self.state["reviewer_mode"] = reviewer_mode

    def set_requirements(self, requirements : list[str]):
        self.state["requirements"] = requirements

    def set_plan(self, plan: list[str]):
        self.state["plan"] = plan

    def save_steps(self, step_data: dict):
        self.state["steps"].append(step_data)

    def get_state(self):
        return self.state
