class Logger:
    def __init__(self, task_dir):
        self.log_file = f"{task_dir}/log.txt"

    def update(self, event):
        with open(self.log_file, "a") as f:
            f.write(f"{event}\n")