from core.orchestrator import Orchestrator
import json

def load_task(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_result(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

if __name__ == '__main__':
    task = load_task("tasks/tasks.json")
    orchestrator = Orchestrator()

    for task_data in task:
        result = orchestrator.run(task_data["task"])
        save_result("results/logs.json", result)
print("run Completed")
