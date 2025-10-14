





import re
from typing import Dict, Any, List, Optional
import subprocess
import requests
import json

# ------------------------------
# 工具注册与管理子系统
# ------------------------------

class ToolRegistry:
    def __init__(self):
        # 工具元信息存储
        self.tools = {}

    def register_tool(self, tool_name: str, tool_meta: Dict[str, Any]):
        """注册工具"""
        self.tools[tool_name] = tool_meta

    def get_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """根据工具名称获取工具元信息"""
        return self.tools.get(tool_name)

    def find_tools_by_query(self, query: str) -> List[str]:
        """根据查询匹配工具"""
        matched_tools = []
        for tool_name, meta in self.tools.items():
            if re.search(meta["description"], query, re.IGNORECASE):
                matched_tools.append(tool_name)
        return matched_tools


# ------------------------------
# 工具调用与执行子系统
# ------------------------------

class ToolExecutor:
    def execute(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """执行工具"""
        tool_meta = registry.get_tool(tool_name)
        if not tool_meta:
            raise ValueError(f"Tool {tool_name} not found")

        tool_type = tool_meta["type"]
        if tool_type == "local_script":
            return self._execute_local_script(tool_meta["path"], params)
        elif tool_type == "api":
            return self._call_api(tool_meta["endpoint"], params)
        else:
            raise ValueError(f"Unsupported tool type: {tool_type}")

    def _execute_local_script(self, script_path: str, params: Dict[str, Any]) -> str:
        """执行本地脚本"""
        try:
            result = subprocess.run(
                ["python", script_path, json.dumps(params)],
                capture_output=True,
                text=True
            )
            return result.stdout
        except Exception as e:
            raise RuntimeError(f"Failed to execute local script: {e}")

    def _call_api(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """调用API"""
        try:
            response = requests.post(endpoint, json=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise RuntimeError(f"Failed to call API: {e}")


# ------------------------------
# 查询解析与工具匹配子系统
# ------------------------------

class QueryParser:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def parse_query(self, query: str) -> Dict[str, Any]:
        """解析查询并匹配工具"""
        matched_tools = self.registry.find_tools_by_query(query)
        if not matched_tools:
            raise ValueError("No matching tools found for the query")

        # 简单参数提取（示例：从查询中提取数字作为参数）
        params = {"input": query}
        return {
            "tools": matched_tools,
            "params": params
        }


# ------------------------------
# 结果标准化与返回子系统
# ------------------------------

class ResultFormatter:
    def format_result(self, tool_name: str, raw_output: Any) -> Dict[str, Any]:
        """标准化工具输出"""
        return {
            "tool_name": tool_name,
            "result": raw_output,
            "status": "success"
        }

    def format_error(self, error_message: str) -> Dict[str, Any]:
        """标准化错误信息"""
        return {
            "tool_name": "unknown",
            "result": None,
            "status": "error",
            "error": error_message
        }


# ------------------------------
# AIToolsBridge 主系统
# ------------------------------

class AIToolsBridge:
    def __init__(self):
        self.registry = ToolRegistry()
        self.executor = ToolExecutor()
        self.parser = QueryParser(self.registry)
        self.formatter = ResultFormatter()

    def register_tool(self, tool_name: str, tool_meta: Dict[str, Any]):
        """注册工具"""
        self.registry.register_tool(tool_name, tool_meta)

    def process_query(self, query: str) -> Dict[str, Any]:
        """处理查询并返回结果"""
        try:
            # 解析查询并匹配工具
            parsed_query = self.parser.parse_query(query)
            tool_name = parsed_query["tools"][0]  # 选择第一个匹配的工具
            params = parsed_query["params"]

            # 调用工具
            raw_output = self.executor.execute(tool_name, params)

            # 标准化结果
            return self.formatter.format_result(tool_name, raw_output)
        except Exception as e:
            # 处理错误
            return self.formatter.format_error(str(e))


# ------------------------------
# 示例工具定义
# ------------------------------

# 本地脚本工具
local_script_tool = {
    "type": "local_script",
    "description": "A tool to calculate the length of a string",
    "path": "tools/string_length.py"  # 假设本地有一个脚本
}

# API 工具
api_tool = {
    "type": "api",
    "description": "A tool to translate text to another language",
    "endpoint": "https://api.example.com/translate"
}

# ------------------------------
# 示例运行
# ------------------------------

if __name__ == "__main__":
    # 初始化 AIToolsBridge
    bridge = AIToolsBridge()

    # 注册工具
    bridge.register_tool("string_length", local_script_tool)
    bridge.register_tool("translate", api_tool)

    # 处理查询
    query = "Calculate the length of this string"
    result = bridge.process_query(query)
    print(json.dumps(result, indent=2))
    
    

    
    
TestAIToolsBridge
├── infos_df.py                # 数据处理工具（保留）
├── __init__.py
├── QueryParser               # 新增：自然语言指令解析模块
│   ├── __init__.py
│   ├── parser.py            # 解析自然语言为工具调用和参数
│   └── nlp_engine.py        # NLP处理逻辑（可选对接外部模型）
├── ToolsHub                  # 工具管理和注册
│   ├── __init__.py
│   ├── ToolData
│   │   ├── scripts         # 本地脚本存储
│   │   └── tools.json      # 工具元数据
│   └── tools
│       ├── __init__.py
│       ├── registry.py     # 工具注册中心
│       └── storage
│           ├── base_storage.py   # 抽象存储基类
│           ├── json_storage.py   # JSON存储实现
│           └── db_storage.py     # 新增：支持数据库存储（可选）
├── ToolsExecute              # 工具执行层
│   ├── __init__.py
│   ├── executors
│   │   ├── base_executor.py      # 抽象执行器基类
│   │   ├── api_executor.py       # API工具执行器
│   │   ├── script_executor.py    # 本地脚本执行器
│   │   ├── db_executor.py        # 新增：数据库工具执行器
│   │   └── file_executor.py      # 新增：文件处理执行器
│   └── services
│       ├── __init__.py
│       ├── tool_executor.py      # 工具执行调度器
│       └── param_handler.py      # 新增：参数处理模块
├── Utils                     # 新增：通用工具模块
│   ├── __init__.py
│   ├── logger.py            # 日志模块
│   └── error_handler.py     # 错误处理模块
└── TestAIToolsBridge.ipynb   # 测试笔记本（保留）