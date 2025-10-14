import sqlite3
from typing import Dict
from .base_storage import BaseStorage
from ..tool_meta_info import ToolMetaInfo
from ..registry import ToolFactory
import json


class DbStorage(BaseStorage):
    def __init__(self, db_path: str):
        """
        初始化数据库存储

        :param db_path: 数据库文件路径（如 "tools.db"）
        """
        self.db_path = db_path
        self.factory = ToolFactory()
        self._initialize_db()

    def _initialize_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tools (
                    tool_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                )
            """)
            conn.commit()

    def load_tools(self) -> Dict[str, ToolMetaInfo]:
        """从数据库加载工具"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT tool_id, data FROM tools")
                rows = cursor.fetchall()
                return {
                    tool_id: self.factory.create_tool(json.loads(data))
                    for tool_id, data in rows
                }
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to load tools from database: {str(e)}")

    def save_tools(self, tools: Dict[str, ToolMetaInfo]) -> None:
        """将工具保存到数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # 清空表并重新插入
                cursor.execute("DELETE FROM tools")
                for tool_id, tool in tools.items():
                    tool_data = json.dumps(tool.to_dict())
                    cursor.execute(
                        "INSERT INTO tools (tool_id, data) VALUES (?, ?)",
                        (tool_id, tool_data)
                    )
                conn.commit()
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to save tools to database: {str(e)}")

    def tool_exists(self, tool_id: str) -> bool:
        """检查工具是否已存在"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM tools WHERE tool_id = ?", (tool_id,))
                return cursor.fetchone()[0] > 0
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to check tool existence: {str(e)}")