import sqlite3
from typing import Dict, Any
from .base_executor import BaseExecutor


class DbExecutor(BaseExecutor):
    def __init__(self, db_path: str):
        """
        数据库执行策略

        :param db_path: 数据库文件路径（如 "tools.db"）
        """
        self.db_path = db_path

    def execute(self, params: Dict[str, Any]) -> Any:
        """执行数据库查询

        :param params: 查询参数，必须包含 "query"（SQL 语句），可选 "params"（参数化查询值）
        :return: 查询结果（列表或字典）
        """
        query = params.get("query")
        if not query:
            raise ValueError("Missing required parameter 'query' for database execution")
        
        query_params = params.get("params", [])
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row  # 返回字典形式的结果
                cursor = conn.cursor()
                cursor.execute(query, query_params)
                if query.strip().upper().startswith("SELECT"):
                    return [dict(row) for row in cursor.fetchall()]
                conn.commit()
                return {"status": "success", "affected_rows": cursor.rowcount}
        except sqlite3.Error as e:
            raise RuntimeError(f"Database query failed: {str(e)}")