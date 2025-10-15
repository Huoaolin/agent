from typing import Dict, List, Optional, Any
from difflib import SequenceMatcher
from .tool_meta_info import ToolMetaInfo, ToolType
from .storage.base_storage import BaseStorage


class ToolFactory:
    """工具工厂类，用于创建工具实例"""
    @staticmethod
    def create_tool(tool_info: Dict[str, Any]) -> ToolMetaInfo:
        """
        根据工具信息创建 ToolMetaInfo 实例
        :param tool_info: 工具信息字典
        :return: ToolMetaInfo 实例
        """
        return ToolMetaInfo(
            tool_id=tool_info["tool_id"],
            name=tool_info["name"],
            description=tool_info["description"],
            path_endpoint=tool_info["path_endpoint"],
            params=tool_info["params"],
            response=tool_info["response"],
            tool_type=tool_info["tool_type"],
            version=tool_info.get("version", "1.0")
        )


class ToolRegistry:
    def __init__(self, storage: BaseStorage):
        """
        工具注册类，用于注册和管理工具。

        :param storage: 存储策略实例
        """
        self.factory = ToolFactory()  # 引入工厂模式
        self.storage = storage
        self.tools: Dict[str, ToolMetaInfo] = self._load_tools()

    def _load_tools(self) -> Dict[str, ToolMetaInfo]:
        """从存储加载工具并转换为 ToolMetaInfo 对象"""
        raw_tools = self.storage.load_tools()
        return {tool_id: self.factory.create_tool(tool_info) for tool_id, tool_info in raw_tools.items()}

    # def register_tool(self, tool: ToolMetaInfo):
    #     """
    #     注册工具
    #     :param tool: ToolMetaInfo 对象
    #     """
    #     if self.storage.tool_exists(tool.tool_id):
    #         raise ValueError(f"Tool with ID {tool.tool_id} already exists")
    #     if tool.name in [t.name for t in self.tools.values()]:
    #         raise ValueError(f"Tool with name {tool.name} already exists")
    #     self.tools[tool.tool_id] = tool
    #     self.storage.save_tools({tool_id: tool.to_dict() for tool_id, tool in self.tools.items()})
    
    def register_tool(self, tool: ToolMetaInfo) -> Dict[str, Any]:
        """
        注册工具

        :param tool: ToolMetaInfo 对象
        :return: 注册结果字典，包含状态和提示信息
        """
        # 检查工具 ID 是否已存在
        if self.storage.tool_exists(tool.tool_id):
            return {
                "status": "warning",
                "message": f"Tool with ID '{tool.tool_id}' already exists. Skipping registration."
            }

        # 检查工具名称是否已存在
        if tool.name in [t.name for t in self.tools.values()]:
            return {
                "status": "warning",
                "message": f"Tool with name '{tool.name}' already exists. Skipping registration."
            }

        # 注册工具并保存
        self.tools[tool.tool_id] = tool
        self.storage.save_tools({tool_id: tool.to_dict() for tool_id, tool in self.tools.items()})
        return {
            "status": "success",
            "message": f"Tool '{tool.name}' (ID: {tool.tool_id}) registered successfully."
        }

    def get_tool(self, tool_id: str) -> Optional[ToolMetaInfo]:
        """
        根据工具ID获取工具

        :param tool_id: 工具ID
        :return: Tool 对象，如果未找到则返回 None
        """
        return self.tools.get(tool_id)

    def find_tools_by_name(self, name: str) -> List[ToolMetaInfo]:
        """
        根据工具名称查找工具

        :param name: 工具名称
        :return: 匹配的工具列表
        """
        return [tool for tool in self.tools.values() if tool.name == name]

    def find_tools_by_description(self, query: str, top_n: int = 1) -> List[ToolMetaInfo]:
        """
        根据工具描述与查询的相似度查找工具

        :param query: 查询字符串
        :param top_n: 返回最匹配的前 N 个工具
        :return: 匹配的工具列表
        """
        if not self.tools:
            return []

        scored_tools = [
            (
                SequenceMatcher(None, tool.description.lower(), query.lower()).ratio(),
                tool,
            )
            for tool in self.tools.values()
        ]
        scored_tools.sort(key=lambda item: item[0], reverse=True)
        return [tool for score, tool in scored_tools[:top_n] if score > 0]

    def list_tools(self) -> List[ToolMetaInfo]:
        """
        列出所有已注册的工具

        :return: 所有工具列表
        """
        return list(self.tools.values())

    def remove_tool(self, tool_id: str):
        """
        移除工具

        :param tool_id: 工具ID
        """
        if tool_id in self.tools:
            del self.tools[tool_id]
            self.storage.save_tools({tool_id: tool.to_dict() for tool_id, tool in self.tools.items()})

    def get_tools_by_type(self, tool_type: str) -> List[ToolMetaInfo]:
        """
        根据工具类型查找工具

        :param tool_type: 工具类型（如 "local_script", "api"）
        :return: 匹配的工具列表
        """
        try:
            target_type = ToolType.from_str(tool_type)
            return [tool for tool in self.tools.values() if tool.tool_type == target_type]
        except ValueError:
            return []