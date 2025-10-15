from ..services.llm_service import LLMService
from typing import List
import json
import re


class InputProcessor:
    def __init__(self):
        self.llm = LLMService()

    def extract_json_list(self, raw_input_string: str) -> str:
        pattern = r'\[.*?\]'
        matches = re.findall(pattern, raw_input_string, re.DOTALL)
        if matches:
            return matches[0]
        print(f"未能在 LLM 输出中提取 JSON 列表: {raw_input_string}")
        return json.dumps(["用户输入理解错误，终止任务"])

    def process(self, query: str) -> List[str]:
        """Process user input into a list of actionable steps as plain text."""
        # 第一级解析：提取意图和粗粒度步骤
        coarse_result = self._parse_intent_and_coarse_steps(query)
        print("coarse_result", coarse_result)

        # 第二级解析：细化为详细的自然语言步骤
        detailed_steps = self._refine_to_detailed_steps(query, coarse_result)
        print("detailed_steps", detailed_steps)
        return detailed_steps

    def _parse_intent_and_coarse_steps(self, query: str) -> List[str]:
        """Parse the query to identify intent and break it into necessary steps in Chinese."""
        prompt = (
            "Analyze the following user input to identify the intent and break it into necessary actionable steps. "
            "Return the result as a JSON array of strings, where each string is a numbered step describing a clear action in Chinese:\n"
            "Input: '{query}'\n"
            "Guidelines:\n"
            "- Understand the user's intent (e.g., search, analyze, generate) and tailor the steps accordingly.\n"
            "- Break the task into logical, sequential steps that are specific and actionable.\n"
            "- Use natural Chinese language and number each step (e.g., '1. 打开浏览器', '2. 搜索信息').\n"
            "- Ensure the steps fully address the user's request.\n"
            "- Return the list in JSON format."
            "Example output:\n"

        ).format(query=query)

        response = self.llm.call(prompt, response_format={"type": "json_object"})
        response = self.extract_json_list(response)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return [f"1. 处理输入：{query}"]

    # def _refine_to_detailed_steps(self, query, coarse_result: List) -> List[str]:
    #     """Refine coarse steps into a detailed list of actionable steps in plain text."""
    #     prompt = (
    #         "Given the following task description, generate a list of detailed actionable steps in plain text. "
    #         "Each step should be a numbered sentence describing a clear action. "
    #         "Task: {target}\n"
    #         "Coarse steps: {coarse_steps}\n"
    #         "Guidelines:\n"
    #         "- Break the task into logical, detailed steps that can be executed sequentially.\n"
    #         "- Use natural Chinese language and number each step (e.g., '1. 打开浏览器', '2. 搜索信息').\n"
    #         "- Ensure the steps are specific and actionable, tailored to the task.\n"
    #         "- Return the list in JSON format."
    #     ).format(target=query, coarse_steps=coarse_result)
    #     response = self.llm.call(prompt, response_format={"type": "json_object"})
    #     response = self.extract_json_list(response)
    #     try:
    #         return json.loads(response)
    #     except json.JSONDecodeError:
    #         # 默认 fallback，返回简单的步骤列表
    #         return [
    #             f"1. Start processing the input: {coarse_result['target']}.",
    #             "2. Complete the task as requested."
    #         ]

    def _refine_to_detailed_steps(self, query: str, coarse_result: List) -> List[str]:
        """Refine coarse steps into a detailed list of actionable steps in plain text."""
        # prompt = (
        #     "Given the following task description and coarse steps, analyze each coarse step and break it into smaller, detailed actionable sub-steps. "
        #     "Return all sub-steps as a single flat list of numbered sentences in plain text, using natural Chinese language:\n"
        #     "Task: {target}\n"
        #     "Coarse steps: {coarse_steps}\n"
        #     "Guidelines:\n"
        #     "- Analyze each coarse step individually and decompose it into specific, logical sub-steps that can be executed sequentially.\n"
        #     "- Use natural Chinese language and number each sub-step (e.g., '1. 搜索比亚迪的车型', '2. 搜索蔚来的车型').\n"
        #     "- Ensure the sub-steps are detailed, actionable, and tailored to the task.\n"
        #     "- Combine all sub-steps into one flat list, maintaining a continuous numbering across all coarse steps.\n"
        #     "- For example:\n"
        #     "  - If a coarse step is '列出需要分析的国产电动汽车品牌和型号，例如比亚迪、蔚来、小鹏等', decompose it into:\n"
        #     "    '1. 搜索比亚迪的电动汽车型号。', '2. 搜索蔚来的电动汽车型号。', '3. 搜索小鹏的电动汽车型号。'\n"
        #     "  - If a coarse step is '确定关键性能指标，如续航里程、充电时间、最高速度、加速性能等', decompose it into:\n"
        #     "    '4. 搜索比亚迪某型号A的续航里程、充电时间、最高速度和加速性能。', '5. 搜索蔚来某型号B的续航里程、充电时间、最高速度和加速性能。', ...\n"
        #     "- Return the result as a JSON array of strings.\n"
        #     "Example output:\n"
        #     "[\n"
        #     "  \"1. 搜索比亚迪的电动汽车型号。\",\n"
        #     "  \"2. 搜索蔚来的电动汽车型号。\",\n"
        #     "  \"3. 搜索小鹏的电动汽车型号。\",\n"
        #     "  \"4. 搜索比亚迪某型号A的续航里程、充电时间、最高速度和加速性能。\",\n"
        #     "  \"5. 搜索蔚来某型号B的续航里程、充电时间、最高速度和加速性能。\"\n"
        #     "]"
        # ).format(target=query, coarse_steps=json.dumps(coarse_result))

        prompt = (
            "根据以下任务描述和粗略步骤，分析每个粗略步骤，并将其分解为更小的、详细的、可操作的子步骤。"
            "将所有子步骤以自然中文语言返回为一个单一的、连续编号的句子列表，要求步骤具体但不过于琐碎，保持在‘步骤级别’而非‘操作级别’。\n"
            "任务: {target}\n"
            "粗略步骤: {coarse_steps}\n"
            "指导原则:\n"
            "- 逐一分析每个粗略步骤，并将其分解为逻辑清晰、顺序执行的子步骤。\n"
            "- 使用自然中文语言，为每个子步骤编号（例如 '1. 搜索比亚迪的电动汽车型号', '2. 搜索蔚来的电动汽车型号'）。\n"
            "- 子步骤应比粗略步骤更具体，足够清晰可执行，但不需要细化到操作细节（如‘打开浏览器’或‘点击某链接’）。\n"
            "- 将所有粗略步骤的子步骤合并为一个平坦列表，编号连续递增。\n"
            "- 示例：\n"
            "  - 如果粗略步骤是 '列出需要分析的国产电动汽车品牌和型号，例如比亚迪、蔚来、小鹏等'，分解为：\n"
            "    '1. 搜索比亚迪的电动汽车型号。', '2. 搜索蔚来的电动汽车型号。', '3. 搜索小鹏的电动汽车型号。', '4. 整理并记录所有品牌的主要型号。'\n"
            "  - 如果粗略步骤是 '确定关键性能指标，如续航里程、充电时间、最高速度、加速性能等'，分解为：\n"
            "    '5. 查找比亚迪某型号A的关键性能指标。', '6. 查找蔚来某型号B的关键性能指标。', '7. 查找小鹏某型号C的关键性能指标。', '8. 汇总所有型号的性能数据。'\n"
            "- 确保子步骤是任务执行中的自然阶段，而不是具体的操作指令。\n"
            "返回结果格式为 JSON 字符串数组，例如：\n"
            "[\n"
            "  \"1. 搜索比亚迪的电动汽车型号。\",\n"
            "  \"2. 搜索蔚来的电动汽车型号。\",\n"
            "  \"3. 搜索小鹏的电动汽车型号。\",\n"
            "  \"4. 整理并记录所有品牌的主要型号。\"\n"
            "]"
        ).format(target=query, coarse_steps=json.dumps(coarse_result))

        response = self.llm.call(prompt, response_format={"type": "json_object"})
        response = self.extract_json_list(response)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # 默认 fallback，返回简单的步骤列表
            return [
                f"1. 开始处理输入：{query}。",
                "2. 按请求完成任务。"
            ]
