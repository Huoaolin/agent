from .task_manager import TaskManager
import os
from urllib.parse import urlparse
import requests
import json
import ast


class ResultStrategy:
    def handle(self, task_manager, data):
        pass


class TextStrategy(ResultStrategy):
    def handle(self, task_manager, data):
        return task_manager.save_result("result.txt", data)


class ImageStrategy(ResultStrategy):
    def handle(self, task_manager, data):
        return data  # data已是路径，直接返回


class FileStrategy(ResultStrategy):
    def handle(self, task_manager, data):
        return data  # data已是路径，直接返回


class ResultHandler:
    def __init__(self, task_manager, parser, controller):
        self.task_manager = task_manager
        self.parser = parser  # 用于调用 evaluate_current_task 和 evaluate_final_goal
        self.controller = controller  # 用于调用 find_most_relevant_link
        self.results = []  # 存储结果，之前在 Agent 中

    def save_result(self, action, current_state, save_to_file=True):
        """
        处理任务结果，可选择保存到文件或直接返回文本。
        Args:
            action (str): 任务类型 ("extract_text", "extract_image", "file")
            current_state (dict or str): 当前状态（对于图片，包含 'images' 字段的列表）
            save_to_file (bool): 是否保存到文件
        Returns:
            list or str: 处理后的结果（对于图片，返回文件路径列表；否则返回字符串）
        """
        task_dir = self.task_manager.get_task_dir()
        os.makedirs(task_dir, exist_ok=True)  # 确保任务目录存在

        # 如果 current_state 是字符串，解析为字典
        if isinstance(current_state, str):
            try:
                current_state = ast.literal_eval(current_state)
            except (ValueError, SyntaxError):
                print(f"警告: current_state 解析失败: {current_state}")
                current_state = {"images": [{"extracted": current_state}]}  # 假设它是单个 URL

        # 如果 self.result 存在，始终保存到文件
        if hasattr(self, 'results') and self.results and save_to_file:
            result_file_path = os.path.join(task_dir, "result.txt")
            with open(result_file_path, "w", encoding="utf-8") as f:
                f.write(str(self.results))

        if action == "extract_text":
            if save_to_file:
                file_path = os.path.join(task_dir, "extracted_text.txt")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(str(current_state))
                return file_path
            return str(current_state)

        elif action == "extract_image":
            if not isinstance(current_state, dict) or "images" not in current_state:
                return "无效的图片结果"

            image_list = current_state.get("images", [])
            if not image_list:
                return "没有提取到图片"

            # 保存所有图片并返回文件路径列表
            file_paths = []
            for idx, image_info in enumerate(image_list):
                image_url = image_info.get("extracted", "")
                if not image_url or not isinstance(image_url, str):
                    file_paths.append(f"图片 {idx+1}: URL 无效")
                    continue

                # 检查 image_url 是否是 URL
                parsed_url = urlparse(image_url)
                if parsed_url.scheme in ["http", "https"]:
                    try:
                        response = requests.get(image_url, stream=True, timeout=10)
                        response.raise_for_status()

                        # 从 URL 中提取文件名
                        base_name = os.path.basename(parsed_url.path)
                        name, ext = os.path.splitext(base_name)
                        if not ext:  # 如果没有扩展名
                            file_name = f"{name}_{idx+1}.png" if name else f"downloaded_image_{idx+1}.png"
                        else:
                            file_name = f"{name}_{idx+1}{ext}" if name else f"downloaded_image_{idx+1}.jpg"

                        file_path = os.path.join(task_dir, file_name)
                        with open(file_path, "wb") as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        file_paths.append(file_path)
                    except requests.RequestException as e:
                        file_paths.append(f"图片 {idx+1} 下载失败: {str(e)}")
                else:
                    # 如果是本地路径，检查是否存在
                    if os.path.exists(image_url):
                        file_paths.append(image_url)
                    else:
                        file_paths.append(f"图片 {idx+1}: 路径无效")
            return file_paths  # 返回所有图片的文件路径列表
        return str(current_state)  # 默认返回当前状态的字符串形式

    async def handle_extract_text_result(self, current_state, task, tasks, previous_state):
        """处理 extract_text 任务的结果，判断是否满足目标并更新任务列表"""
        satisfied, _ = self.parser.evaluate_current_task(current_state, task)
        print(f"***评估提取结果: satisfied={satisfied}")
        # 如果满足目标，直接返回当前任务列表
        if satisfied:
            print("***提取结果满足目标，无需进一步操作")
            self.results.append(current_state)
            return tasks
        # 如果不满足目标，直接使用 find_most_relevant_link
        relevant_url = await self.controller.find_most_relevant_link(task["value"], previous_state)
        print("***提取结果不满足目标，尝试寻找相关链接:", relevant_url)
        if relevant_url:
            print(f"***找到相关链接: {relevant_url}")
            # 添加 open_page 任务
            tasks.insert(0, {
                "action": "open_page",
                "value": relevant_url,
                "type": "text",
                "sub_goal": f"Open page to extract {task['value']}"
            })
            # 重新添加 extract_text 任务
            tasks.insert(1, task)
            print(f"***更新任务列表: {tasks[:2]}")
        else:
            print("***未找到相关链接，跳过")
        return tasks

    async def handle_extract_image_result(self, current_state, task, tasks, previous_state):
        """处理 extract_image 任务的结果，判断是否满足目标并更新任务列表"""
        satisfied, _ = self.parser.evaluate_current_task(current_state, task)
        print(f"***评估提取结果: satisfied={satisfied}")
        # 如果满足目标，直接返回当前任务列表
        if satisfied:
            print("***提取结果满足目标，无需进一步操作")
            self.results.append(current_state)
            return tasks
        # 如果不满足目标，直接使用 find_most_relevant_link
        relevant_url = await self.controller.find_most_relevant_link(task["value"], previous_state)
        print("***提取结果不满足目标，尝试寻找相关链接:", relevant_url)
        if relevant_url:
            print(f"***找到相关链接: {relevant_url}")
            # 添加 open_page 任务
            tasks.insert(0, {
                "action": "open_page",
                "value": relevant_url,
                "type": "text",
                "sub_goal": f"Open page to extract {task['value']}"
            })
            # 重新添加 extract_image 任务
            tasks.insert(1, task)
            print(f"***更新任务列表: {tasks[:2]}")
        else:
            print("***未找到相关链接，跳过")
        return tasks

    async def check_final_goal_and_reset_tasks(self, final_state, tasks, attempts, max_attempts, user_input):
        satisfied, next_tasks = self.parser.evaluate_final_goal(user_input, self.results)
        print(f"***最终目标评估: satisfied={satisfied}, next_tasks={next_tasks}")
        if not satisfied and next_tasks and attempts < max_attempts - 1:
            tasks = next_tasks
            attempts += 1
            print(f"***最终目标不满足，重置任务: {tasks}")
        else:
            if satisfied:
                print("***最终目标已满足，任务完成")
            elif attempts >= max_attempts - 1:
                print(f"***达到最大尝试次数 ({max_attempts})，未能完全满足需求")
            else:
                print("***无新任务可规划，退出")
        return tasks, attempts