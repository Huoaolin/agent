from typing import List, Dict, Any, Optional
from enum import Enum


# 定义工具类型枚举，便于扩展和管理
class ToolType(Enum):
    LOCAL_SCRIPT = "local_script"
    API = "api"
    DATABASE = "database"
    FILE = "file"  # 新增支持文件操作工具类型

    @classmethod
    def from_str(cls, type_str: str) -> "ToolType":
        try:
            return cls(type_str)
        except ValueError:
            raise ValueError(f"Invalid tool type: {type_str}")


class ToolMetaInfo:
    def __init__(
        self,
        tool_id: str,
        name: str,
        description: str,
        path_endpoint: str,
        params: List[Dict[str, Any]],
        response: Dict[str, str],
        tool_type: str,
        version: Optional[str] = "1.0"  # 新增版本号，便于工具升级管理
    ):
        """
        工具元信息类

        :param tool_id: 工具的唯一ID
        :param name: 工具名称
        :param description: 工具描述
        :param path_endpoint: 工具的路径（本地脚本）或端点（API）
        :param params: 工具参数列表，每个参数是一个字典，包含 name、type、value、required 和 optional description
        :param response: 工具的返回格式
        :param tool_type: 工具类型（如 "local_script", "api" 等）
        :param version: 工具版本号，默认 "1.0"
        """
        self.tool_id = self._validate_id(tool_id)
        self.name = self._validate_name(name)
        self.description = description or "No description provided"
        self.path_endpoint = self._validate_path_endpoint(path_endpoint, tool_type)
        self.params = self._validate_params(params)
        self.response = self._validate_response(response)
        self.tool_type = ToolType.from_str(tool_type)  # 使用枚举类型
        self.version = version

    @staticmethod
    def _validate_id(tool_id: str) -> str:
        if not tool_id or not isinstance(tool_id, str):
            raise ValueError("Tool ID must be a non-empty string")
        return tool_id

    @staticmethod
    def _validate_name(name: str) -> str:
        if not name or not isinstance(name, str):
            raise ValueError("Tool name must be a non-empty string")
        return name

    @staticmethod
    def _validate_path_endpoint(path_endpoint: str, tool_type: str) -> str:
        if not path_endpoint:
            raise ValueError(f"Tool of type '{tool_type}' must have a valid path_endpoint")
        return path_endpoint

    @staticmethod
    def _validate_params(params: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not isinstance(params, list):
            raise ValueError("Params must be a list")
        for param in params:
            if "name" not in param or "type" not in param or "description" not in param:
                raise ValueError(f"Parameter {param} must have 'name' and 'type' and 'description'")
            if param.get("required", False) and "value" not in param:
                param["value"] = None  # 为必填参数提供默认值 None
        return params

    @staticmethod
    def _validate_response(response: Dict[str, str]) -> Dict[str, str]:
        if not isinstance(response, dict):
            raise ValueError("Response must be a dictionary")
        return response

    def to_dict(self) -> Dict[str, Any]:
        """将工具信息转换为字典"""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "path_endpoint": self.path_endpoint,
            "params": self.params,
            "response": self.response,
            "tool_type": self.tool_type.value,  # 使用枚举值
            "version": self.version
        }

    def __repr__(self):
        return f"ToolMetaInfo(name={self.name}, type={self.tool_type.value}, version={self.version})"