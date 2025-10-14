class QueryExecutor:
    def __init__(self, storage_manager: StorageManager):
        self.storage_manager = storage_manager

    def execute(self, query_plan: Dict) -> List:
        """
        执行查询计划
        :param query_plan: 从 QueryRewriter 生成的查询计划
        :return: 查询结果
        """
        results = []
        for storage_type in query_plan["storage_targets"]:
            result = self._execute_on_storage(storage_type, query_plan["parameters"])
            results.extend(result)
        return self._merge_results(results)

    def _execute_on_storage(self, storage_type: str, parameters: Dict) -> List:
        """
        在指定存储上执行查询
        """
        if storage_type == "es":
            # 调用 ESStorage 的查询方法
            return self.storage_manager.query(storage_type, parameters.get("vector", []))
        elif storage_type == "file":
            # 调用 FileStorage 的查询方法
            return self.storage_manager.query(storage_type, parameters.get("keywords", []))
        elif storage_type == "sql":
            # 调用 SQLStorage 的查询方法
            return self.storage_manager.query(storage_type, parameters.get("sql_query", ""))
        return []

    def _merge_results(self, results: List) -> List:
        """
        合并多个存储的查询结果
        """
        # 示例：去重、排序等
        return results