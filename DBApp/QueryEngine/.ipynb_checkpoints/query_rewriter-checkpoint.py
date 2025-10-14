from typing import Dict, List
from Storage.storage import StorageManager


class QueryRewriter:
    def __init__(self, storage_manager: StorageManager):
        self.storage_manager = storage_manager
        self.storage_types = ["es", "file", "sql"]  # 可扩展

    def rewrite(self, query: str, context: Dict = None) -> Dict:
        """
        改写查询并生成查询计划
        :param query: 用户输入的查询
        :param context: 查询上下文（如用户偏好、历史查询）
        :return: 查询计划，包含存储类型和查询参数
        """
        # 1. 解析查询意图
        query_type, keywords = self._parse_query(query)

        # 2. 判断存储位置
        storage_targets = self._route_query(query_type, keywords, context)

        # 3. 生成查询参数
        query_plan = self._generate_query_plan(query_type, keywords, storage_targets)

        return query_plan

    def _parse_query(self, query: str) -> tuple:
        """
        解析查询意图（示例逻辑）
        :return: (query_type, keywords)
        """
        # 示例：判断是精确查询还是语义搜索
        if query.startswith("SELECT"):
            return "sql", query
        elif "similar to" in query.lower():
            return "semantic", query
        else:
            return "keyword", query.split()

    def _route_query(self, query_type: str, keywords: List, context: Dict) -> List[str]:
        """
        判断数据存储位置
        :return: 可能的存储类型列表
        """
        # 示例逻辑：根据查询类型和上下文路由
        if query_type == "sql":
            return ["sql"]
        elif query_type == "semantic":
            return ["es"]
        else:
            return ["es", "file"]  # 默认搜索 ES 和文件

    def _generate_query_plan(self, query_type: str, keywords: List, storage_targets: List[str]) -> Dict:
        """
        生成查询计划
        :return: 查询计划
        """
        query_plan = {
            "query_type": query_type,
            "storage_targets": storage_targets,
            "parameters": {}
        }
        if query_type == "sql":
            query_plan["parameters"] = {"sql_query": keywords}
        elif query_type == "semantic":
            query_plan["parameters"] = {"vector": self._embed_query(keywords)}
        else:
            query_plan["parameters"] = {"keywords": keywords}
        return query_plan

    def _embed_query(self, keywords: List) -> List[float]:
        """
        将查询转换为向量（调用 ModelServer/EmbeddingServer）
        """
        # 假设调用 EmbeddingServer 的 utils.py
        pass