from agents.planner import Planner
from agents.coder import Coder
from core.memory_manager import Memory_manager

class Orchestrator():
    def __init__(self):
        self.coder = Coder()
        self.planner = Planner()

    def run(self, task: str):
        memory = Memory_manager(task)
        plan = self.planner.plan(task)
        memory.set_plan(plan)

        for i, step in enumerate(plan, start = 1):
            context = memory.get_state()
            coder_result = self.coder.generate_code(task, step, context)
            step_record = {
                "step_id": i,
                "step_title": step,
                "code": coder_result["code"],
                "summary": coder_result["summary"],
                "decisions": coder_result["decisions"],
                "artifacts": coder_result["artifacts"]
            }
            memory.save_steps(step_record)
        return memory.get_state()
