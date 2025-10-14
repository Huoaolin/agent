from typing import Dict, Any
from abc import ABC, abstractmethod


class BaseExecutor(ABC):
    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> Any:
        """执行工具

        :param params: 工具参数
        :return: 执行结果
        """
        pass