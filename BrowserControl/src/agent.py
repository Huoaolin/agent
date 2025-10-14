from .task_parser import TaskParser
from .browser_controller import BrowserController
from .result_handler import ResultHandler
from .logger import Logger
from .task_manager import TaskManager
from datetime import datetime
# from .api_module import external_api, get_final_result  # 假设 api_module 在 gradio/ 下



# class Agent:
#     def __init__(self):
#         self.task_manager = TaskManager()
#         self.parser = TaskParser()
#         self.controller = BrowserController()
#         self.result_handler = ResultHandler(self.task_manager, self.parser, self.controller)  # 传递 parser 和 controller
#         self.logger = Logger(self.task_manager.get_task_dir())
#         self.controller.add_observer(self.logger)
#         self.user_input = None

#     async def run(self, user_input):
#         self.user_input = user_input
#         print(f"初始输入: {user_input}")
#         await self.controller.start()
#         if not self.controller.page:
#             print("浏览器初始化失败，退出")
#             return []
#         tasks = self.parser.parse(self.user_input)
#         print("****分解出的任务步骤****")
#         print("tasks", tasks)
#         print("****分解出的任务步骤****")
#         results = await self.process_tasks(tasks)
#         await self.controller.close()
#         return results

class Agent:
    def __init__(self, jobID=None):  # 添加 jobID 参数，默认为 None
        self.jobID = jobID if jobID else datetime.now().strftime("%Y%m%d_%H%M%S")  # 如果未提供 jobID，则生成默认值
        self.task_manager = TaskManager(self.jobID)  # 将 jobID 传递给 TaskManager
        self.parser = TaskParser()
        self.controller = BrowserController()
        self.result_handler = ResultHandler(self.task_manager, self.parser, self.controller)
        self.logger = Logger(self.task_manager.get_task_dir())
        self.controller.add_observer(self.logger)
        self.user_input = None

    async def run(self, user_input):
        self.user_input = user_input
        print(f"初始输入: {user_input}")
        await self.controller.start()
        if not self.controller.page:
            print("浏览器初始化失败，退出")
            return []
        tasks = self.parser.parse(self.user_input)
        print("****分解出的任务步骤****")
        print("tasks", tasks)
        print("****分解出的任务步骤****")
        results = await self.process_tasks(tasks)
        await self.controller.close()
        return results

    async def process_tasks(self, tasks):
        current_state = ""
        max_attempts = 2
        attempts = 0
        while tasks and attempts < max_attempts:
            print("--------------------------------")
            print("--------------------------------")
            task = tasks.pop(0)

            print(f"当前尝试次数: {attempts + 1}/{max_attempts}")
            print("***当前任务：", task)
            # 执行任务并更新状态
            previous_state = current_state
            current_state = await self.execute_and_update_state(task, current_state)
            print(f"***当前状态: {current_state[:200]}...")
            # 如果任务是 extract_text 或 extract_image，交给 ResultHandler 处理
            if task["action"] == "extract_text":
                tasks = await self.result_handler.handle_extract_text_result(current_state, task, tasks, previous_state)
                self.result_handler.save_result(task["action"], current_state, save_to_file=False)
            elif task["action"] == "extract_image":
                tasks = await self.result_handler.handle_extract_image_result(current_state, task, tasks, previous_state)
                self.result_handler.save_result(task["action"], current_state, save_to_file=False)
            # 当任务列表为空时，检查最终目标
            if not tasks:
                tasks, attempts = await self.result_handler.check_final_goal_and_reset_tasks(
                    current_state, tasks, attempts, max_attempts, self.user_input
                )
        return self.result_handler.results  # 返回 ResultHandler 中的结果

    async def execute_and_update_state(self, task, current_state):
        try:
            state = await self.execute_task(task)
            if state is None:
                raise ValueError(f"Task {task['action']} returned None")
            else:
                print(f"***执行 {task['action']} 完成，继续后续任务")
            return str(state)
        except Exception as e:
            print(f"任务 {task['action']} 执行失败: {e}")
            return f"Error: {str(e)}"

    async def execute_task(self, task):
        try:
            if task["action"] == "open_page":
                return await self.controller.open_page(task["value"])
            elif task["action"] == "search":
                return await self.controller.search(task["value"])
            elif task["action"] == "click_element":
                return await self.controller.click_element(task["value"])
            elif task["action"] == "extract_text":
                return await self.controller.extract_text(task["value"])
            elif task["action"] == "extract_image":
                return await self.controller.extract_image(task["value"])
            elif task["action"] == "find_most_relevant_link":
                return await self.controller.find_most_relevant_link(task["value"])
            elif task["action"] == "take_screenshot":
                return await self.controller.take_screenshot(f"{task['value']}.png")
            elif task["action"] == "download_file":
                return await self.controller.download_file(task["value"], "downloaded_file")
            elif task["action"] == "done":
                return self.result_handler.process(task["action"], task["value"], save_to_file=False)
        except Exception as e:
            print(f"执行任务 {task['action']} 时出错: {e}")
            raise e