import os
from datetime import datetime


class TaskManager:
    def __init__(self, jobID):  # 修改为接收 jobID
        self.task_id = jobID  # 使用传入的 jobID
        self.task_dir = f"./tasks/{self.task_id}"
        os.makedirs(self.task_dir, exist_ok=True)

    def save_result(self, filename, content, binary=False):
        mode = "wb" if binary else "w"
        with open(f"{self.task_dir}/{filename}", mode) as f:
            f.write(content)
        return f"{self.task_dir}/{filename}"

    def get_task_dir(self):
        return self.task_dir