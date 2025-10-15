# TestAIToolsBridge/core/ToolAgent.py
import os
from typing import Any, Dict, Optional

from ..QueryParser.parser import QueryParserFactory
from ..ToolsExecute.services.param_handler import ParamHandler
from ..ToolsExecute.services.tool_executor import ToolExecutor
from ..ToolsHub.tools.registry import ToolRegistry
from ..ToolsHub.tools.storage.json_storage import JsonStorage


class ToolAgent:
    def __init__(
        self,
        storage_path: str = "AIToolsBridge/ToolsHub/ToolData/tools.json",
        *,
        api_key: Optional[str] = None,
        parser_type: Optional[str] = None,
    ):
        """
        初始化 ToolAgent

        :param storage_path: 工具存储路径（默认使用 JSON 存储）
        :param api_key: LLM API 密钥（用于 NLP 解析）
        """

        # 初始化工具注册和存储
        self.storage = JsonStorage(storage_path)
        self.registry = ToolRegistry(self.storage)

        # 初始化 NLP 解析器
        parser_choice = parser_type or os.getenv("TOOL_AGENT_PARSER", "rule_based")
        self.parser = QueryParserFactory.create_parser(
            parser_choice,
            self.registry,
            api_key=api_key,
        )

    def register_tool(self, tool_config: Dict[str, Any]):
        """注册工具

        :param tool_config: 工具配置字典
        """
        try:
            tool = self.registry.factory.create_tool(tool_config)
            self.registry.register_tool(tool)
        except Exception as e:
            raise
            
    def remove_tool(self, tool_id):
        """删除工具
        """
        try:
            self.registry.remove_tool(tool_id)
        except Exception as e:
            raise

    def process_query(self, query: str) -> Dict[str, Any]:
        """处理自然语言查询并返回结果

        :param query: 自然语言查询
        :return: 包含状态和结果的字典
        """

        try:
            # 解析查询,分析使用哪个工具,分析参数是什么
            parsed_result = self.parser.parse(query)
            tool_name = parsed_result["tool"]
            params = parsed_result["params"]

            print(f"将使用工具: {tool_name}")
            print(f"工具的入参: {params}")

            # 获取工具对象
            tool = next((t for t in self.registry.list_tools() if t.name == tool_name), None)
            if not tool:
                return {
                    "status": "error",
                    "message": f"No tool named '{tool_name}' found. Please register the tool or clarify your query.",
                    "available_tools": [t.name for t in self.registry.list_tools()]
                }

            # 处理参数
            param_handler = ParamHandler(tool.params)
            try:
                processed_params = param_handler.convert_params(params)
                param_handler.validate_params(processed_params)
            except ValueError as e:
                missing_params = [p["name"] for p in tool.params if p.get("required", False) and p["name"] not in params]
                return {
                    "status": "error",
                    "message": f"Missing or invalid parameters: {str(e)}. Required parameters: {missing_params}",
                    "tool": tool_name,
                    "required_params": [{"name": p["name"], "description": p.get("description", "No description")} for p in tool.params if p.get("required", False)]
                }

            # 执行工具
            executor = ToolExecutor(tool)
            result = executor.execute(processed_params)
            return {
                "status": "success",
                "tool": tool_name,
                "result": result
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error processing query: {str(e)}"
            }

    def list_tools(self):
        """列出所有注册的工具"""
        return [tool.name for tool in self.registry.list_tools()]


# # 示例使用
# if __name__ == "__main__":
#     agent = ToolAgent()
#     tools = [
#         {
#             "tool_id": "string_len_001",
#             "name": "string_length",
#             "description": "Calculate the length of a string",
#             "path_endpoint": "ToolsHub/ToolData/scripts/string_length.py",
#             "params": [{"name": "text", "type": "string", "required": True, "description": "The input string"}],
#             "response": {"result": "integer"},
#             "tool_type": "local_script"
#         }
#     ]
#     for tool in tools:
#         agent.register_tool(tool)

#     test_queries = [
#         "Get the length of string 'hello'",
#         "Get the length of string",
#         "Run unknown_tool with data 'test'"
#     ]
#     for query in test_queries:
#         result = agent.process_query(query)
#         print(f"Query: {query}")
#         print(f"Result: {result}")
#         print("-" * 50)