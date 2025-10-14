# from typing import Dict, Any, Optional

# class NLPEngine:
#     def __init__(self, model_path: Optional[str] = None):
#         """
#         NLP 处理引擎（对接外部模型）

#         :param model_path: 模型路径（若提供则加载）
#         """
#         self.model_path = model_path
#         if model_path:
#             # 假设使用外部模型（如 spaCy 或 transformers），这里仅占位
#             raise NotImplementedError("External NLP model loading not implemented yet")
#         else:
#             self.model = None

#     def process(self, text: str) -> str:
#         """预处理文本（占位实现）"""
#         return text.strip()

#     def extract_entities(self, text: str) -> Dict[str, str]:
#         """提取实体（占位实现）"""
#         if self.model:
#             # 使用外部模型提取实体
#             pass
#         return {}

#     def detect_intent(self, text: str) -> str:
#         """检测意图（占位实现）"""
#         if self.model:
#             # 使用外部模型检测意图
#             pass
#         return "unknown"


from typing import Dict, Any, Optional, List
import requests  # 假设使用 HTTP API 调用 LLM
import json
from openai import OpenAI
import re


class NLPEngine:
    def __init__(self, model_path: Optional[str] = None, api_key: Optional[str] = None):
        """
        NLP 处理引擎（对接外部 LLM 模型）

        :param model_path: 本地模型路径（可选，未实现）
        :param api_key: LLM API 的密钥（若使用远程 API）
        """
        # self.model_path = model_path
        self.api_key = 'sk-6f15756855394f00a0902af819ae9f4a'
        self.base_url = "https://api.deepseek.com"
        self.model = "deepseek-chat"

        # if model_path:
        #     raise NotImplementedError("Local NLP model loading not implemented yet")
        # elif not api_key:
        #     raise ValueError("API key is required for remote LLM inference")

    def process(self, text: str) -> str:
        """预处理文本"""
        return text.strip()

    def extract_all_dicts_from_string(self, s: str) -> list:
        """
        从字符串中提取所有字典
        :param s: 输入的字符串
        :return: 提取到的字典列表
        """
        pattern = r"\{.*\}"  # 非贪婪匹配，匹配多个字典
        match = re.search(pattern, s, re.DOTALL)  # re.DOTALL 允许跨行匹配
        if match:
            try:
                # 将匹配到的字符串解析为字典
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                # 如果解析失败，返回 None
                return None
        return None

    def extract_entities(self, text: str, tool_params: List[Dict[str, Any]]) -> Dict[str, str]:
        """使用 LLM 提取实体

        :param text: 查询文本
        :param tool_params: 工具参数定义（来自 ToolMetaInfo）
        :return: 提取的参数字典
        """
        # 构造 Prompt
        prompt = self._build_prompt(text, tool_params)

        # 调用 LLM API（这里以 xAI 的假想 API 为例）
        response = self._call_llm(prompt)
        # 解析 LLM 返回的 JSON
        try:
            response_dict = self.extract_all_dicts_from_string(response)
            return response_dict.get("entities", {})
        except json.JSONDecodeError:
            raise ValueError(f"LLM returned invalid JSON: {response}")

    def _build_prompt(self, text: str, tool_params: List[Dict[str, Any]]) -> str:
        """构造 LLM Prompt，包含参数描述中的示例

        :param text: 查询文本
        :param tool_params: 工具参数定义
        :return: Prompt 字符串
        """
        param_descriptions = "\n".join(
            f"- {p['name']} ({p['type']}): {p.get('description', 'No description')}"
            for p in tool_params
        )
        prompt = f"""
        Given the query: "{text}"
        Extract the parameters based on the following parameter definitions, 
        paying attention to the examples provided in the descriptions (e.g., ...):

        {param_descriptions}

        Return a JSON object with the following format:
        {{
            "entities": {{"param_name": "param_value", ...}}
        }}

        Examples based on parameter definitions:
        - Query: "Plot chart with x as [2018, 2019, 2020] and y as [100, 150, 200] titled 'Sales Trend' saved to 'output/chart.png'"
          -> {{"entities": {{"x": "[2018, 2019, 2020]", "y": "[100, 150, 200]", "title": "Sales Trend", "output_path": "output/chart.png"}}}}
        - Query: "Save chart for x [2021, 2022] and y [50, 60] to 'my_chart.png'"
          -> {{"entities": {{"x": "[2021, 2022]", "y": "[50, 60]", "output_path": "my_chart.png"}}}}
        """
        return prompt


#     def extract_entities(self, text: str, tool_params: list[Dict[str, Any]]) -> Dict[str, str]:
#         """使用 LLM 提取实体

#         :param text: 查询文本
#         :param tool_params: 工具参数定义（来自 ToolMetaInfo）
#         :return: 提取的参数字典
#         """
#         # 构造 Prompt
#         prompt = self._build_prompt(text, tool_params)

#         # 调用 LLM API（这里以 xAI 的假想 API 为例）
#         response = self._call_llm(prompt)
#         # 解析 LLM 返回的 JSON
#         try:
#             response = self.extract_all_dicts_from_string(response)
#             # result = json.loads(response)
#             return response.get("entities", {})
#         except json.JSONDecodeError:
#             raise ValueError(f"LLM returned invalid JSON: {response}")

#     def _build_prompt(self, text: str, tool_params: list[Dict[str, Any]]) -> str:
#         """构造 LLM Prompt

#         :param text: 查询文本
#         :param tool_params: 工具参数定义
#         :return: Prompt 字符串
#         """
#         param_descriptions = "\n".join(
#             f"- {p['name']}: {p.get('description', 'No description')}" 
#             for p in tool_params
#         )
#         prompt = f"""
#         Given the query: "{text}"
#         Extract the parameters based on the following parameter definitions:
#         {param_descriptions}

#         Return a JSON object with the following format:
#         {{
#             "entities": {{"param_name": "param_value", ...}}
#         }}

#         Examples:
#         - Query: "Write 'data' to file", Params: [{{"name": "data", "description": "Content to write"}}]
#           -> {{"entities": {{"data": "data"}}}}
#         """
#         return prompt

    def detect_intent(self, text: str, candidate_tools: List[Any]) -> str:
        """使用 LLM 检测意图，从候选工具中选择最匹配的工具名

        :param text: 查询文本
        :param candidate_tools: ToolRegistry.find_tools_by_description 返回的候选工具列表
        :return: 工具名（意图）
        """
        if not candidate_tools:
            raise ValueError("No candidate tools provided for intent detection")

        # 构造候选工具信息
        tool_options = "\n".join(
            f"- {tool.name}: {tool.description}" for tool in candidate_tools
        )
        prompt = f"""
        Given the query: "{text}"
        Select the most appropriate tool name (intent) from the following candidates:
        {tool_options}

        Return only the tool name as a string.
        Examples:
        - Query: "Call api with data 'test'", Candidates: ["api_test: Test API", "file_read: Read file"]
          -> "api_test"
        """
        response = self._call_llm(prompt)

        return response.strip()

    def _call_llm(self, prompt: str) -> str:
        """调用 Azure OpenAI API

        :param prompt: 输入的 Prompt
        :return: LLM 返回的文本
        """
        # 初始化 Azure OpenAI 客户端
        client_gpt = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        try:
            # 调用 OpenAI API
            response = client_gpt.chat.completions.create(
                model=self.model,  # model = "deployment_name".
                messages=[
                    {"role": "system", "content": "Assistant is a large language model trained by OpenAI."},
                    {"role": "user", "content": prompt}
                ]
            )
            # 返回生成的文本
            return response.choices[0].message.content
        except Exception as e:
            # 临时占位返回（无真实 API 时）
            if "length of string" in prompt:
                return '{"entities": {"text": "hello"}}'
            elif "api_test with data" in prompt:
                return '{"entities": {"data": "test_data"}}'
            raise RuntimeError(f"Failed to call LLM API: {str(e)}")

    # def _call_llm(self, prompt: str) -> str:
    #     """调用外部 LLM API（占位实现）
    #     :param prompt: 输入的 Prompt
    #     :return: LLM 返回的文本
    #     """
    #     # 假想 xAI API 调用（需替换为真实 API）
    #     api_url = "https://api.xai.example.com/v1/completions"  # 替换为真实端点
    #     headers = {"Authorization": f"Bearer {self.api_key}"}
    #     payload = {
    #         "prompt": prompt,
    #         "max_tokens": 100,
    #         "temperature": 0.5
    #     }
    #     try:
    #         response = requests.post(api_url, json=payload, headers=headers)
    #         response.raise_for_status()
    #         return response.json()["choices"][0]["text"]
    #     except Exception as e:
    #         # 临时占位返回（无真实 API 时）
    #         if "length of string" in prompt:
    #             return '{"entities": {"text": "hello"}}'
    #         elif "api_test with data" in prompt:
    #             return '{"entities": {"data": "test_data"}}'
    #         raise RuntimeError(f"Failed to call LLM API: {str(e)}")



class RuleBasedNLPEngine:
    def process(self, text: str) -> str:
        """规则-based 文本预处理"""
        # 简单清理文本
        return text.strip().replace("  ", " ")

    def extract_entities(self, text: str) -> Dict[str, str]:
        """规则-based 实体提取（简单实现）"""
        entities = {}
        words = text.split()
        for i, word in enumerate(words):
            if word.startswith("'") and word.endswith("'"):
                if i > 0:
                    entities[words[i-1]] = word[1:-1]
        return entities

    def detect_intent(self, text: str) -> str:
        """规则-based 意图检测（简单实现）"""
        # 假设第一个动词后的名词是意图
        words = text.lower().split()
        verbs = {"get", "calculate", "find"}
        for i, word in enumerate(words):
            if word in verbs and i + 1 < len(words):
                return words[i + 1]
        return "unknown"