from ..services.llm_service import LLMService
import json


# class TaskPlanner:
#     def __init__(self):
#         self.llm = LLMService()

#     def plan(self, task_desc: dict) -> list:
#         """根据任务描述生成步骤列表"""
#         prompt = (
#             f"根据以下任务描述，生成具体的执行步骤，每步一行：\n"
#             f"任务描述：{json.dumps(task_desc)}"
#         )
#         response = self.llm.call(prompt)
#         return [step.strip() for step in response.split("\n") if step.strip()]

class TaskPlanner:
    def __init__(self) -> None:
        self.llm = LLMService()

    def plan(self, query: str, task_desc: dict) -> list[str]:
        """根据任务描述生成详细的步骤列表。"""

        prompt = (
            "根据以下任务描述和粗略步骤，分析每个粗略步骤，并将其分解为更小的、详细的、可操作的子步骤。"
            "将所有子步骤以自然中文语言返回为一个单一的、连续编号的句子列表。\n"
            "任务描述: {query}\n"
            "粗略步骤: {task_desc}\n"
            "指导原则:\n"
            "- 逐一分析每个粗略步骤，并将其分解为逻辑清晰、顺序执行的子步骤。\n"
            "- 使用自然中文语言，为每个子步骤编号（例如 '1. 查询国产电动汽车品牌有哪些', '2. 搜索比亚迪的电动汽车型号'）。\n"
            "- 子步骤应比粗略步骤更具体，确保清晰且可执行，但不需要过于琐碎的操作细节。\n"
            "- 将所有粗略步骤的子步骤合并为一个平坦列表，编号连续递增。\n"
            "- 总步骤不要超过13个。"
        ).format(query=query, task_desc=task_desc)

        response = self.llm.call(prompt)

        steps = self._normalise_response(response)
        if not steps:
            return [
                f"1. 解析任务目标：{query}",
                "2. 调用必要的工具或接口以收集信息",
                "3. 汇总信息并准备最终输出",
            ]
        return steps

    def _normalise_response(self, response: str) -> list[str]:
        """Support both JSON-array and newline-delimited responses."""

        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            parsed = None

        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]

        return [line.strip() for line in response.splitlines() if line.strip()]