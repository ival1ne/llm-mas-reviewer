class Memory_manager():
    def __init__(self, task: str):
        self.state = {
            "task" : task,
            "requirements" : [],
            "plan" : [],
            "steps" : []
        }

    def set_requirements(self, requirements : list[str]):
        self.state["requirements"] = requirements

    def set_plan(self, plan: list[str]):
        self.state["plan"] = plan

    def save_steps(self, step_data: dict):
        self.state["steps"].append(step_data)

    def get_state(self):
        return self.state
