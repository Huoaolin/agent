import json
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
            if method not in {"GET", "POST"}:
                raise ValueError(f"Unsupported HTTP method: {method}")

            if method == "GET":
                query = "&".join(f"{key}={value}" for key, value in params.items())
                url = f"{self.endpoint}?{query}" if params else self.endpoint
                request = Request(url, method="GET")
            else:
                data = json.dumps(params).encode("utf-8")
                request = Request(self.endpoint, data=data, method="POST", headers={"Content-Type": "application/json"})

            with urlopen(request, timeout=10) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload)
        except (HTTPError, URLError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Failed to call API at {self.endpoint}: {exc}")
