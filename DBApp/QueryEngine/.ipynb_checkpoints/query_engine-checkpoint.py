from .query_rewriter import QueryRewriter
from .query_executor import QueryExecutor


class QueryEngine:
    def __init__(self, storage_manager):
        self.rewriter = QueryRewriter(storage_manager)
        self.executor = QueryExecutor(storage_manager)

    def search(self, query: str, context: dict = None) -> list:
        """
        执行查询的主入口
        :param query: 用户输入的查询
        :param context: 查询上下文（如用户偏好）
        :return: 查询结果
        """
        query_plan = self.rewriter.rewrite(query, context)
        results = self.executor.execute(query_plan)
        return results