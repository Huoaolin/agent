import json
from pathlib import Path
from typing import Dict, Any
from .base_storage import BaseStorage
from ..tool_meta_info import ToolMetaInfo
from ..registry import ToolFactory


class JsonStorage(BaseStorage):
    def __init__(self, file_path: str):
        """
        初始化 JSON 存储

        :param file_path: JSON 文件路径
        """
        self.file_path = Path(file_path)
        self.factory = ToolFactory()  # 使用工厂创建工具实例

    # def load_tools(self) -> Dict[str, ToolMetaInfo]:
    #     """从 JSON 文件加载工具"""
    #     if not self.file_path.exists():
    #         return {}
    #     try:
    #         with open(self.file_path, "r", encoding="utf-8") as f:
    #             tools_data = json.load(f)
    #             if not isinstance(tools_data, dict):
    #                 raise ValueError("JSON file content must be a dictionary")
    #             return {
    #                 tool_id: self.factory.create_tool(tool_data)
    #                 for tool_id, tool_data in tools_data.items()
    #             }
    #     except (json.JSONDecodeError, ValueError) as e:
    #         raise ValueError(f"Failed to load tools from {self.file_path}: {str(e)}")
    
    def load_tools(self) -> Dict[str, Dict[str, Any]]:
        """从 JSON 文件加载工具（返回原始字典）"""
        if not self.file_path.exists():
            return {}
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)  # 返回原始字典，而非 ToolMetaInfo 对象

    def save_tools(self, tools: Dict[str, ToolMetaInfo]) -> None:
        """将工具保存到 JSON 文件"""
        try:
            # 确保目录存在
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            # tools_data = {tool_id: tool.to_dict() for tool_id, tool in tools.items()}
            tools_data = {tool_id: tool for tool_id, tool in tools.items()}
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(tools_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise RuntimeError(f"Failed to save tools to {self.file_path}: {str(e)}")

    def tool_exists(self, tool_id: str) -> bool:
        """检查工具是否已存在"""
        tools = self.load_tools()
        return tool_id in tools