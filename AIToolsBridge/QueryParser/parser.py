from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from .nlp_engine import RuleBasedNLPEngine, NLPEngine
from ..ToolsHub.tools.registry import ToolRegistry


class QueryParser(ABC):
    @abstractmethod
    def parse(self, query: str) -> Dict[str, Any]:
        """解析自然语言查询为工具调用和参数

        :param query: 自然语言指令
        :return: 结构化数据，如 {"tool": "tool_name", "params": {"key": "value"}}
        """
        pass


class RuleBasedParser(QueryParser):
    def __init__(self, tool_registry: ToolRegistry):
        """
        基于规则的解析器

        :param tool_registry: 工具注册实例，用于查询可用工具
        """
        self.tool_registry = tool_registry
        self.nlp_engine = RuleBasedNLPEngine()

    def parse(self, query: str) -> Dict[str, Any]:
        """基于规则解析查询"""
        # 使用 NLP 引擎预处理查询
        processed_query = self.nlp_engine.process(query)

        # 提取工具名（简单规则：假设第一个动词后的名词是工具名）
        tools = self.tool_registry.list_tools()
        tool_name = None
        for tool in tools:
            if tool.name.lower() in processed_query.lower():
                tool_name = tool.name
                break

        if not tool_name:
            # 尝试通过描述匹配工具
            matched_tools = self.tool_registry.find_tools_by_description(query, top_n=1)
            if matched_tools:
                tool_name = matched_tools[0].name
            else:
                raise ValueError(f"No tool found matching query: {query}")

        # 获取工具元信息
        tool = next(t for t in tools if t.name == tool_name)

        # 提取参数
        params = {}
        for param in tool.params:
            param_name = param["name"]
            # 简单规则：查找参数名后的值
            param_start = processed_query.lower().find(param_name.lower())
            if param_start != -1:
                param_value = processed_query[param_start + len(param_name):].strip().split()[0]
                # 处理引号包裹的值（如 'hello'）
                if param_value.startswith("'") and param_value.endswith("'"):
                    param_value = param_value[1:-1]
                params[param_name] = param_value

        return {"tool": tool_name, "params": params}


# class NLPModelParser(QueryParser):
#     def __init__(self, tool_registry: ToolRegistry, model_path: Optional[str] = None):
#         """
#         基于 NLP 模型的解析器

#         :param tool_registry: 工具注册实例
#         :param model_path: 外部 NLP 模型路径（可选）
#         """
#         self.tool_registry = tool_registry
#         self.nlp_engine = NLPEngine(model_path)

#     def parse(self, query: str) -> Dict[str, Any]:
#         """基于 NLP 模型解析查询"""
#         entities = self.nlp_engine.extract_entities(query)
#         intent = self.nlp_engine.detect_intent(query)

#         # 假设意图对应工具名
#         tool_name = intent
#         tools = self.tool_registry.list_tools()
#         tool = next((t for t in tools if t.name == tool_name), None)
#         if not tool:
#             raise ValueError(f"No tool found for intent: {intent}")

#         # 提取参数
#         params = {}
#         for param in tool.params:
#             param_name = param["name"]
#             if param_name in entities:
#                 params[param_name] = entities[param_name]

#         return {"tool": tool_name, "params": params}


# class NLPModelParser(QueryParser):
#     def __init__(self, tool_registry: ToolRegistry, model_path: Optional[str] = None, api_key: Optional[str] = None):
#         """
#         基于 NLP 模型的解析器

#         :param tool_registry: 工具注册实例
#         :param model_path: 外部 NLP 模型路径（可选）
#         :param api_key: LLM API 密钥（可选）
#         """
#         self.tool_registry = tool_registry
#         self.nlp_engine = NLPEngine(model_path, api_key)

#     def parse(self, query: str) -> Dict[str, Any]:
#         """基于 NLP 模型解析查询"""
#         # 先检测意图（工具名）
#         intent = self.nlp_engine.detect_intent(query)
#         # 查找对应的工具
#         tools = self.tool_registry.list_tools()
#         tool = next((t for t in tools if t.name == intent), None)
#         if not tool:
#             raise ValueError(f"No tool found for intent: {intent}")

#         # 提取参数（传入工具参数定义）
#         entities = self.nlp_engine.extract_entities(query, tool.params)

#         return {"tool": intent, "params": entities}


class NLPModelParser(QueryParser):
    def __init__(self, tool_registry: ToolRegistry, model_path: Optional[str] = None, api_key: Optional[str] = None):
        """
        基于 NLP 模型的解析器

        :param tool_registry: 工具注册实例
        :param model_path: 外部 NLP 模型路径（可选）
        :param api_key: LLM API 密钥（可选）
        """
        self.tool_registry = tool_registry
        self.nlp_engine = NLPEngine(model_path, api_key)

    def parse(self, query: str) -> Dict[str, Any]:
        """基于 NLP 模型解析查询"""
        # 使用 find_tools_by_description 获取候选工具
        candidate_tools = self.tool_registry.find_tools_by_description(query, top_n=3)  # 取前 3 个最相似工具

        if not candidate_tools:
            raise ValueError(f"No tools found matching query: {query}")

        # 从候选工具中检测意图
        intent = self.nlp_engine.detect_intent(query, candidate_tools)

        # 查找对应的工具
        tool = next((t for t in self.tool_registry.list_tools() if t.name == intent), None)
        if not tool:
            raise ValueError(f"Detected intent '{intent}' does not match any registered tool")
        # 提取参数
        entities = self.nlp_engine.extract_entities(query, tool.params)
        return {"tool": intent, "params": entities}



class QueryParserFactory:
    @staticmethod
    def create_parser(parser_type: str, tool_registry: ToolRegistry, model_path: Optional[str] = None, api_key: Optional[str] = None) -> QueryParser:
        """创建解析器实例

        :param parser_type: 解析器类型 ("rule_based" 或 "nlp_model")
        :param tool_registry: 工具注册实例
        :param model_path: NLP 模型路径（可选）
        :return: QueryParser 实例
        """
        if parser_type == "rule_based":
            return RuleBasedParser(tool_registry)
        elif parser_type == "nlp_model":
            return NLPModelParser(tool_registry, model_path, api_key)
        else:
            raise ValueError(f"Unknown parser type: {parser_type}")