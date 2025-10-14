import requests
from typing import Dict, Any
from .base_executor import BaseExecutor


class ApiExecutor(BaseExecutor):
    def __init__(self, endpoint: str):
        """
        API 执行策略

        :param endpoint: API 端点
        """
        self.endpoint = endpoint

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """调用 API

        :param params: API 参数（支持 method 指定请求方法，默认 POST）
        :return: API 响应结果
        """
        try:
            method = params.pop("method", "POST").upper()
            if method == "GET":
                response = requests.get(self.endpoint, params=params)
            elif method == "POST":
                response = requests.post(self.endpoint, json=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to call API at {self.endpoint}: {str(e)}")