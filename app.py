# app.py
import sys
import os
import json
import gradio as gr
from OmniWorker.src.core.input_processor import InputProcessor
from OmniWorker.src.core.task_planner import TaskPlanner
from OmniWorker.src.core.task_executor import TaskExecutor
from OmniWorker.src.core.step_recorder import StepRecorder
from OmniWorker.src.core.interaction_handler import InteractionHandler
import threading
import glob

# 添加 OmniWorker 的路径到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'OmniWorker')))


class MockLogger:
    def __init__(self, log_file="/tmp/task_steps.txt"):
        self.log_file = log_file

    def error(self, message: str):
        print(f"[ERROR] {message}")
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"[ERROR] {message}\n")
            f.flush()

    def info(self, message: str):
        print(f"[INFO] {message}")
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"[INFO] {message}\n")
            f.flush()


def get_full_log(log_file_path):
    """读取整个日志文件内容"""
    try:
        if os.path.exists(log_file_path):
            with open(log_file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        return "loading..."
    except Exception as e:
        return f"读取日志失败: {str(e)}"


def process_query(query):
    processor = InputProcessor()
    task_desc = processor.process(query)
    task_planner = TaskPlanner()
    steps = task_planner.plan(query, task_desc)
    # steps = [
    #  '2. 根据目标读者确定报告的用途，如购车参考、竞品分析或市场趋势研究。',
    #  '3. 将结果写入到markdown文件里。',]

    step_recorder = StepRecorder("test_task")
    interaction_handler = InteractionHandler()
    executor = TaskExecutor(None, step_recorder, interaction_handler)
    output_dir = "./tasks"
    log_file_path = os.path.join(output_dir, str(executor.job_id), "task_steps.log")
    task_dir = os.path.join(output_dir, str(executor.job_id))
    os.makedirs(task_dir, exist_ok=True)

    state = {"current_step": 0, "results": {}, "steps": steps, "query": query}

    if os.path.exists(log_file_path):
        os.remove(log_file_path)

    # 后台执行任务
    def run_executor():
        for result in executor.execute(steps, state):
            # 可选：将结果写入 results.json
            with open(os.path.join(task_dir, "results.json"), 'w', encoding='utf-8') as f:
                f.write(result)
                f.flush()
            # 示例：生成一个 .md 文件（假设任务完成后生成）
            if "final_result" in json.loads(result):
                with open(os.path.join(task_dir, "final_report.md"), 'w', encoding='utf-8') as f:
                    f.write("# 任务报告\n" + result)

    threading.Thread(target=run_executor, daemon=True).start()
    return log_file_path, "\n".join(steps), task_dir  # 返回日志路径、steps 和任务目录


def poll_log(log_file_path, task_dir):
    """定时轮询读取日志并检查 .md 文件"""
    if not log_file_path or not task_dir:
        return "loading...", None

    full_log = get_full_log(log_file_path)

    # 检查任务目录下是否有 .md 文件
    md_files = glob.glob(os.path.join(task_dir, "*.md"))
    if md_files:
        return f"{full_log}", md_files[0]  # 返回第一个 .md 文件
    return f"{full_log}", None


def create_interface():
    with gr.Blocks(title="任务处理与文件下载") as demo:
        with gr.Row():
            input_text = gr.Textbox(label="请输入任务（如：帮我写一个目前国产电动汽车的精品分析，并生成MARKDOWN的报告给我）")
            submit_btn = gr.Button("提交")

        with gr.Row():
            output_text = gr.Textbox(label="任务执行日志", lines=10, max_lines=20)
            steps_text = gr.Textbox(label="任务步骤", lines=10, max_lines=20)

        download_file = gr.File(label="下载结果文件")

        log_file_state = gr.State(value="")
        task_dir_state = gr.State(value="")

        submit_btn.click(
            fn=process_query,
            inputs=[input_text],
            outputs=[log_file_state, steps_text, task_dir_state]  # 返回日志路径、steps 和任务目录
        ).then(
            fn=poll_log,
            inputs=[log_file_state, task_dir_state],
            outputs=[output_text, download_file],
            every=1  # 每秒轮询
        )

    return demo


if __name__ == "__main__":
    interface = create_interface()
    interface.launch(server_name="0.0.0.0", server_port=7862, debug=True)




# # app.py
# import sys
# import os
# import json
# import gradio as gr
# from OmniWorker.src.core.input_processor import InputProcessor
# from OmniWorker.src.core.task_planner import TaskPlanner
# from OmniWorker.src.core.task_executor import TaskExecutor
# from OmniWorker.src.core.step_recorder import StepRecorder
# from OmniWorker.src.core.interaction_handler import InteractionHandler
# import threading

# # 添加 OmniWorker 的路径到 sys.path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'OmniWorker')))


# class MockLogger:
#     def __init__(self, log_file="/tmp/task_steps.txt"):
#         self.log_file = log_file

#     def error(self, message: str):
#         print(f"[ERROR] {message}")
#         with open(self.log_file, 'a', encoding='utf-8') as f:
#             f.write(f"[ERROR] {message}\n")
#             f.flush()

#     def info(self, message: str):
#         print(f"[INFO] {message}")
#         with open(self.log_file, 'a', encoding='utf-8') as f:
#             f.write(f"[INFO] {message}\n")
#             f.flush()


# def get_full_log(log_file_path):
#     """读取整个日志文件内容"""
#     try:
#         if os.path.exists(log_file_path):
#             with open(log_file_path, 'r', encoding='utf-8') as f:
#                 return f.read().strip()
#         return "loading..."
#     except Exception as e:
#         return f"读取日志失败: {str(e)}"


# def process_query(query):
#     processor = InputProcessor()
#     task_desc = processor.process(query)
#     task_planner = TaskPlanner()
#     steps = task_planner.plan(query, task_desc)
#     step_recorder = StepRecorder("test_task")
#     interaction_handler = InteractionHandler()
#     executor = TaskExecutor(None, step_recorder, interaction_handler)  # logger 在 TaskExecutor 中初始化
#     output_dir = "./tasks"
#     log_file_path = os.path.join(output_dir, str(executor.job_id), "task_steps.log")
#     os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

#     state = {"current_step": 0, "results": {}, "steps": steps, "query": query}

#     if os.path.exists(log_file_path):
#         os.remove(log_file_path)

#     # 后台执行任务
#     def run_executor():
#         for result in executor.execute(steps, state):
#             with open(os.path.join(output_dir, str(executor.job_id), "results.json"), 'w', encoding='utf-8') as f:
#                 f.write(result)
#                 f.flush()

#     threading.Thread(target=run_executor, daemon=True).start()
#     # 返回日志文件路径和 steps
#     return log_file_path, "\n".join(steps)  # 将 steps 列表转为字符串，每步一行


# def poll_log(log_file_path):
#     """定时轮询读取整个日志文件并返回"""
#     if not log_file_path:
#         return "loading..."

#     full_log = get_full_log(log_file_path)
#     return f"\n{full_log}"


# def create_interface():
#     with gr.Blocks(title="任务处理与文件下载") as demo:
#         with gr.Row():
#             input_text = gr.Textbox(label="请输入任务（如：帮我写一个目前国产电动汽车的精品分析，并生成MARKDOWN的报告给我）")
#             submit_btn = gr.Button("提交")

#         with gr.Row():
#             # Steps 窗口
#             steps_text = gr.Textbox(label="任务步骤", lines=10, max_lines=20)
#             # 日志窗口
#             output_text = gr.Textbox(label="任务执行日志", lines=10, max_lines=20)

#         download_file = gr.File(label="下载结果文件")

#         log_file_state = gr.State(value="")

#         submit_btn.click(
#             fn=process_query,
#             inputs=[input_text],
#             outputs=[log_file_state, steps_text]  # 返回 log_file_path 和 steps
#         ).then(
#             fn=poll_log,
#             inputs=[log_file_state],
#             outputs=[output_text],
#             every=1  # 每秒轮询
#         )

#     return demo

# if __name__ == "__main__":
#     interface = create_interface()
#     interface.launch(server_name="0.0.0.0", server_port=7862, debug=True)
  


# # # app.py
# # import sys
# # import os
# # import json
# # import gradio as gr
# # from OmniWorker.src.core.input_processor import InputProcessor
# # from OmniWorker.src.core.task_planner import TaskPlanner
# # from OmniWorker.src.core.task_executor import TaskExecutor
# # from OmniWorker.src.core.step_recorder import StepRecorder
# # from OmniWorker.src.core.interaction_handler import InteractionHandler
# # import threading

# # # 添加 OmniWorker 的路径到 sys.path
# # sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'OmniWorker')))


# # class MockLogger:
# #     def __init__(self, log_file="/tmp/task_steps.txt"):
# #         self.log_file = log_file

# #     def error(self, message: str):
# #         print(f"[ERROR] {message}")
# #         with open(self.log_file, 'a', encoding='utf-8') as f:
# #             f.write(f"[ERROR] {message}\n")
# #             f.flush()

# #     def info(self, message: str):
# #         print(f"[INFO] {message}")
# #         with open(self.log_file, 'a', encoding='utf-8') as f:
# #             f.write(f"[INFO] {message}\n")
# #             f.flush()


# # def get_full_log(log_file_path):
# #     """读取整个日志文件内容"""
# #     try:
# #         if os.path.exists(log_file_path):
# #             with open(log_file_path, 'r', encoding='utf-8') as f:
# #                 return f.read().strip()  # 读取全部内容并去除首尾空白
# #         return "loading....."
# #     except Exception as e:
# #         return f"读取日志失败: {str(e)}"


# # def process_query(query):
# #     processor = InputProcessor()
# #     task_desc = processor.process(query)
# #     task_planner = TaskPlanner()
# #     steps = task_planner.plan(query, task_desc)
# #     step_recorder = StepRecorder("test_task")
# #     interaction_handler = InteractionHandler()
# #     executor = TaskExecutor(None, step_recorder, interaction_handler)  # logger 在 TaskExecutor 中初始化
# #     output_dir = "./tasks"
# #     log_file_path = os.path.join(output_dir, str(executor.job_id), "task_steps.log")
# #     os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

# #     state = {"current_step": 0, "results": {}, "steps": steps, "query": query}

# #     if os.path.exists(log_file_path):
# #         os.remove(log_file_path)

# #     # 后台执行任务
# #     def run_executor():
# #         for result in executor.execute(steps, state):
# #             # 将每次 yield 的结果写入文件（可选）
# #             with open(os.path.join(output_dir, str(executor.job_id), "results.json"), 'w', encoding='utf-8') as f:
# #                 f.write(result)
# #                 f.flush()

# #     threading.Thread(target=run_executor, daemon=True).start()
# #     return log_file_path


# # def poll_log(log_file_path):
# #     """定时轮询读取整个日志文件并返回"""
# #     if not log_file_path:
# #         return "等待任务开始..."

# #     full_log = get_full_log(log_file_path)
# #     return f"{full_log}"


# # def create_interface():
# #     with gr.Blocks(title="任务处理与文件下载") as demo:
# #         input_text = gr.Textbox(label="请输入任务（如：帮我写一个目前国产电动汽车的精品分析，并生成MARKDOWN的报告给我）")
# #         output_text = gr.Textbox(label="任务执行结果", lines=10)
# #         download_file = gr.File(label="下载结果文件")
# #         submit_btn = gr.Button("提交")

# #         log_file_state = gr.State(value="")

# #         submit_btn.click(
# #             fn=process_query,
# #             inputs=[input_text],
# #             outputs=[log_file_state]
# #         ).then(
# #             fn=poll_log,
# #             inputs=[log_file_state],
# #             outputs=[output_text],
# #             every=1  # 每秒轮询
# #         )

# #     return demo


# # if __name__ == "__main__":
# #     interface = create_interface()
# #     interface.launch(server_name="0.0.0.0", server_port=7862, debug=True)







# # # # # app.py
# # # # import sys
# # # # import os
# # # # import json
# # # # import gradio as gr
# # # # from OmniWorker.src.core.input_processor import InputProcessor
# # # # from OmniWorker.src.core.task_planner import TaskPlanner
# # # # from OmniWorker.src.core.task_executor import TaskExecutor
# # # # from OmniWorker.src.core.step_recorder import StepRecorder
# # # # from OmniWorker.src.core.interaction_handler import InteractionHandler
# # # # import threading
# # # # import time


# # # # # 添加 OmniWorker 的路径到 sys.path
# # # # sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'OmniWorker')))


# # # # class MockLogger:
# # # #     def __init__(self, log_file="/tmp/task_steps.txt"):
# # # #         self.log_file = log_file

# # # #     def error(self, message: str):
# # # #         print(f"[ERROR] {message}")
# # # #         with open(self.log_file, 'a', encoding='utf-8') as f:
# # # #             f.write(f"[ERROR] {message}\n")

# # # #     def info(self, message: str):
# # # #         print(f"[INFO] {message}")
# # # #         with open(self.log_file, 'a', encoding='utf-8') as f:
# # # #             f.write(f"[INFO] {message}\n")


# # # # def get_latest_log(log_file_path):
# # # #     """读取日志文件的最新一行"""
# # # #     try:
# # # #         if os.path.exists(log_file_path):
# # # #             with open(log_file_path, 'r', encoding='utf-8') as f:
# # # #                 lines = f.readlines()
# # # #                 if lines:
# # # #                     return lines[-1].strip()
# # # #         return "暂无日志"
# # # #     except Exception as e:
# # # #         return f"读取日志失败: {str(e)}"


# # # # def process_query(query):
# # # #     processor = InputProcessor()
# # # #     task_desc = processor.process(query)
# # # #     task_planner = TaskPlanner()
# # # #     steps = task_planner.plan(query, task_desc)
# # # #     logger = MockLogger()  # 指定日志文件
# # # #     step_recorder = StepRecorder("test_task")
# # # #     interaction_handler = InteractionHandler()
# # # #     executor = TaskExecutor(logger, step_recorder, interaction_handler)
# # # #     print(executor.job_id)
    
# # # #     output_dir = "./tasks"
# # # #     log_file_path = os.path.join(output_dir, str(executor.job_id), "task_steps.log")
# # # #     os.makedirs(os.path.dirname(log_file_path), exist_ok=True)  # 确保目录存在

# # # #     state = {"current_step": 0, "results": {}, "steps": steps, "query": query}

# # # #     # 清空之前的日志文件（可选）
# # # #     if os.path.exists(log_file_path):
# # # #         os.remove(log_file_path)

# # # #     # 在后台线程中执行任务
# # # #     def run_executor():
# # # #         for result in executor.execute(steps, state):
# # # #             pass  # 执行任务但不直接处理结果，交给轮询

# # # #     threading.Thread(target=run_executor, daemon=True).start()

# # # #     # 返回日志文件路径，用于轮询
# # # #     return log_file_path


# # # # def poll_log(log_file_path, previous_log_state):
# # # #     """定时轮询日志文件，返回最新日志"""
# # # #     if not log_file_path:
# # # #         return "等待任务开始...", previous_log_state
    
# # # #     latest_log = get_latest_log(log_file_path)
# # # #     if latest_log == previous_log_state["last_log"]:
# # # #         return previous_log_state["output"], previous_log_state  # 如果日志未变，不更新输出
# # # #     else:
# # # #         output = f"最新日志:\n{latest_log}"
# # # #         previous_log_state["last_log"] = latest_log
# # # #         previous_log_state["output"] = output
# # # #         return output, previous_log_state


# # # # def create_interface():
# # # #     with gr.Blocks(title="任务处理与文件下载") as demo:
# # # #         input_text = gr.Textbox(label="请输入任务（如：帮我写一个目前国产电动汽车的精品分析，并生成MARKDOWN的报告给我）")
# # # #         output_text = gr.Textbox(label="任务执行结果", lines=10)
# # # #         download_file = gr.File(label="下载结果文件")
# # # #         submit_btn = gr.Button("提交")

# # # #         # 隐藏状态，用于保存日志文件路径和上一次日志
# # # #         log_file_state = gr.State(value="")
# # # #         previous_log_state = gr.State(value={"last_log": "", "output": "等待任务开始..."})

# # # #         # 提交任务时触发
# # # #         submit_btn.click(
# # # #             fn=process_query,
# # # #             inputs=[input_text],
# # # #             outputs=[log_file_state]
# # # #         ).then(
# # # #             # 定时轮询日志，每秒更新一次
# # # #             fn=poll_log,
# # # #             inputs=[log_file_state, previous_log_state],
# # # #             outputs=[output_text, previous_log_state],
# # # #             every=1  # 每秒轮询一次
# # # #         )

# # # #     return demo

# # # # if __name__ == "__main__":
# # # #     interface = create_interface()
# # # #     interface.launch(server_name="0.0.0.0", server_port=7862, debug=True)








# # # # # app.py
# # # # import sys
# # # # import os
# # # # import json
# # # # import gradio as gr
# # # # from OmniWorker.src.core.input_processor import InputProcessor
# # # # from OmniWorker.src.core.task_planner import TaskPlanner
# # # # from OmniWorker.src.core.task_executor import TaskExecutor
# # # # from OmniWorker.src.core.step_recorder import StepRecorder
# # # # from OmniWorker.src.core.interaction_handler import InteractionHandler


# # # # # 添加 OmniWorker 的路径到 sys.path
# # # # sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'OmniWorker')))


# # # # class MockLogger:
# # # #     def __init__(self, log_file="/tmp/task_steps.txt"):
# # # #         self.log_file = log_file

# # # #     def error(self, message: str):
# # # #         print(f"[ERROR] {message}")
# # # #         with open(self.log_file, 'a', encoding='utf-8') as f:
# # # #             f.write(f"[ERROR] {message}\n")

# # # #     def info(self, message: str):
# # # #         print(f"[INFO] {message}")
# # # #         with open(self.log_file, 'a', encoding='utf-8') as f:
# # # #             f.write(f"[INFO] {message}\n")


# # # # def get_latest_log(log_file_path):
# # # #     """读取日志文件的最新一行"""
# # # #     try:
# # # #         if os.path.exists(log_file_path):
# # # #             with open(log_file_path, 'r', encoding='utf-8') as f:
# # # #                 lines = f.readlines()
# # # #                 if lines:
# # # #                     return lines[-1].strip()
# # # #         return "暂无日志"
# # # #     except Exception as e:
# # # #         return f"读取日志失败: {str(e)}"


# # # # def process_query(query):
# # # #     processor = InputProcessor()
# # # #     task_desc = processor.process(query)
# # # #     task_planner = TaskPlanner()
# # # #     steps = task_planner.plan(query, task_desc)
# # # #     logger = MockLogger()  # 指定日志文件
# # # #     step_recorder = StepRecorder("test_task")
# # # #     interaction_handler = InteractionHandler()
# # # #     executor = TaskExecutor(logger, step_recorder, interaction_handler)
# # # #     print(executor.job_id)
# # # #     output_dir = "./tasks"
# # # #     log_file_path = "./tasks/" + str(executor.job_id) + "/task_steps.log"

# # # #     state = {"current_step": 0, "results": {}, "steps": steps, "query": query}

# # # #     # 清空之前的日志文件（可选）
# # # #     if os.path.exists(log_file_path):
# # # #         os.remove(log_file_path)

# # # #     # 逐步执行任务并生成中间结果
# # # #     for result in executor.execute(steps, state):
# # # #         latest_log = get_latest_log(log_file_path)
# # # #         output = f"执行结果:\n{result}\n\n最新日志:\n{latest_log}"
# # # #         yield output, None

# # # #     # 所有步骤完成后生成文件
# # # #     output_file = os.path.join(output_dir, f"result_{query[:10]}.txt")
# # # #     with open(output_file, "w") as f:
# # # #         f.write(json.dumps(state["results"], ensure_ascii=False, indent=2))
# # # #     latest_log = get_latest_log(log_file_path)
# # # #     final_output = f"执行结果:\n{json.dumps(state['results'], ensure_ascii=False, indent=2)}\n\n最新日志:\n{latest_log}"
# # # #     yield final_output, output_file


# # # # def create_interface():
# # # #     with gr.Blocks(title="任务处理与文件下载") as demo:
# # # #         input_text = gr.Textbox(label="请输入任务（如：帮我写一个目前国产电动汽车的精品分析，并生成MARKDOWN的报告给我）")
# # # #         output_text = gr.Textbox(label="任务执行结果", lines=10)
# # # #         download_file = gr.File(label="下载结果文件")
# # # #         submit_btn = gr.Button("提交")
# # # #         submit_btn.click(
# # # #             fn=process_query,
# # # #             inputs=[input_text],
# # # #             outputs=[output_text, download_file]
# # # #         )
# # # #     return demo


# # # # if __name__ == "__main__":
# # # #     interface = create_interface()
# # # #     interface.launch(server_name="0.0.0.0", server_port=7862, debug=True)