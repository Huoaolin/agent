import json
from datetime import datetime
import os
# from .api_module import external_api, get_final_result  # 假设 api_module 在 gradio/ 下


class StepRecorder:
    """Persist execution traces to ``tasks/<job_id>/task_steps.log``."""

    def __init__(self, job_id: str, log_file: str = "task_steps.log") -> None:
        self.log_file = os.path.join("tasks", job_id, log_file)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def record(self, step: str, result: str) -> None:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "result": result,
        }
        with open(self.log_file, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def get_step_history(self) -> list[dict]:
        try:
            with open(self.log_file, "r", encoding="utf-8") as handle:
                return [json.loads(line) for line in handle.readlines()]
        except FileNotFoundError:
            return []