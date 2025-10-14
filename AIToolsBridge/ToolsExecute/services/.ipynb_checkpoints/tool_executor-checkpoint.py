from typing import Dict, Any
from ..executors.local_script_executor import LocalScriptExecutor
from ..executors.api_executor import ApiExecutor
from ..executors.db_executor import DbExecutor
from ..executors.file_executor import FileExecutor
# from ..ToolsHub.tools.tool_meta_info import ToolMetaInfo


class ToolExecutor:
    def __init__(self, tool):
        """
        工具执行类

        :param tool: ToolMetaInfo 对象（从 ToolsHub 获取）
        """
        self.tool = tool

    def _validate_required_params(self, params: Dict[str, Any]):
        """
        检查用户提供的参数是否满足必填要求

        :param params: 用户提供的参数
        """
        for param in self.tool.params:
            if param.get("required", False) and param["name"] not in params:
                raise ValueError(f"Required parameter '{param['name']}' is missing")

    def execute(self, params: Dict[str, Any]) -> Any:
        """
        执行工具

        :param params: 工具参数
        :return: 工具执行结果
        """
        self._validate_required_params(params)

        # 工厂模式选择执行器
        if self.tool.tool_type.value == "local_script":
            executor = LocalScriptExecutor(self.tool.path_endpoint)
        elif self.tool.tool_type.value == "api":
            executor = ApiExecutor(self.tool.path_endpoint)
        elif self.tool.tool_type.value == "database":
            executor = DbExecutor(self.tool.path_endpoint)
        elif self.tool.tool_type.value == "file":
            executor = FileExecutor(self.tool.path_endpoint)
        else:
            raise ValueError(f"Unsupported tool type: {self.tool.tool_type}")

        return executor.execute(params)