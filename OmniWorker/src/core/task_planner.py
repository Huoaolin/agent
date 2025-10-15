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
    def __init__(self):
        self.llm = LLMService()

    def plan(self, query, task_desc: dict) -> list:
        """根据任务描述生成详细的步骤列表"""
        # 将输入的粗略步骤从 task_desc 中提取出来
        # coarse_steps = task_desc.get("coarse_steps", [])

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
            "- 示例：\n"
            "  - 如果粗略步骤是 '列出当前市场上主要的国产电动汽车品牌，如比亚迪、蔚来、小鹏、理想等'，分解为：\n"
            "    '1. 查询国产电动汽车品牌有哪些。', '2. 确认比亚迪是否为主流品牌。', '3. 确认蔚来是否为主流品牌。', '4. 确认小鹏是否为主流品牌。', '5. 确认理想是否为主流品牌。', '6. 整理并列出主要品牌清单。'\n"
            "  - 如果粗略步骤是 '为每个品牌收集其最新或最受欢迎的电动汽车型号'，分解为：\n"
            "    '7. 查询比亚迪的最新或最受欢迎的电动汽车型号。', '8. 查询蔚来的最新或最受欢迎的电动汽车型号。', '9. 查询小鹏的最新或最受欢迎的电动汽车型号。', '10. 查询理想的最新或最受欢迎的电动汽车型号。', '11. 汇总各品牌的型号清单。'\n"
            "- 返回结果为纯文本，每行一个子步骤，带有编号。\n"
            "- 竞品分析可以考虑搜索产品图片"
            "- 生成markdown的时候，考虑把图片加到markdown里"
            "- 总步骤不要超过13个。"
        ).format(query=query, task_desc=task_desc)

        response = self.llm.call(prompt)
        steps = [step.strip() for step in response.split("\n") if step.strip()]
        if not steps:
            steps = [
                f"1. 解析任务目标：{query}",
                "2. 调用必要的工具或接口以收集信息",
                "3. 汇总信息并准备最终输出",
            ]
        return steps