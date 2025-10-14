import json
from datetime import datetime
import os
# from .api_module import external_api, get_final_result  # 假设 api_module 在 gradio/ 下


class StepRecorder:
    def __init__(self, job_id: str, log_file: str = "task_steps.log"):
        """
        初始化步骤记录器。
        :param job_id: 任务的唯一标识符，用于生成日志文件路径。
        :param log_file: 日志文件名称，默认值为 "task_steps.log"。
        """
        # 使用 "task" 作为根目录，拼接 job_id 和 log_file，例如 "task/123e4567-e89b-12d3-a456-426614174000/task_steps.log"
        self.log_file = os.path.join("tasks", job_id, log_file)
        # 确保目录存在
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def record(self, step: str, result: str):
        """
        记录步骤的执行过程和结果。

        :param step: 当前步骤的描述。
        :param result: 操作的结果。
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "result": result,
        }
        # _ = external_api(f"{step} - {result}")
        with open(self.log_file, "a") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def get_step_history(self) -> list[dict]:
        """
        获取所有步骤的历史记录。

        :return: 步骤历史记录的列表。
        """
        try:
            with open(self.log_file, "r") as f:
                return [json.loads(line) for line in f.readlines()]
        except FileNotFoundError:
            return []