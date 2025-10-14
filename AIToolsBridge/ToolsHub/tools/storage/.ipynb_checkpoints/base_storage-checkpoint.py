from abc import ABC, abstractmethod
from typing import Dict, Any
from ..tool_meta_info import ToolMetaInfo


class BaseStorage(ABC):
    @abstractmethod
    def load_tools(self) -> Dict[str, ToolMetaInfo]:
        """加载工具元数据并返回 ToolMetaInfo 对象字典"""
        pass

    @abstractmethod
    def save_tools(self, tools: Dict[str, ToolMetaInfo]) -> None:
        """保存工具元数据"""
        pass

    @abstractmethod
    def tool_exists(self, tool_id: str) -> bool:
        """检查工具是否已存在"""
        pass