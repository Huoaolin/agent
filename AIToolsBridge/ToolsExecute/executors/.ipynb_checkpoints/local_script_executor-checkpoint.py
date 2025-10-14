import subprocess
import json
from typing import Dict, Any
from .base_executor import BaseExecutor


class LocalScriptExecutor(BaseExecutor):
    def __init__(self, script_path: str):
        """
        本地脚本执行策略

        :param script_path: 脚本路径
        """
        self.script_path = script_path

    def execute(self, params: Dict[str, Any]) -> Any:
        """执行本地脚本

        :param params: 脚本参数（JSON 格式传递）
        :return: 脚本输出（尝试解析为 JSON）
        """
        try:
            # 将参数转为 JSON 字符串
            params_json = json.dumps(params)

            result = subprocess.run(
                ["python", self.script_path, params_json],
                capture_output=True,
                text=True,
                check=True
            )
            # 尝试将输出解析为 JSON，若失败则返回原始字符串
            output = result.stdout.strip()
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                return output
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Script {self.script_path} failed: {e.stderr}")
        except Exception as e:
            raise RuntimeError(f"Failed to execute script {self.script_path}: {str(e)}")