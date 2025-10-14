from typing import Dict, Any
from .base_executor import BaseExecutor


class FileExecutor(BaseExecutor):
    def __init__(self, file_path: str):
        """
        文件处理执行策略

        :param file_path: 文件路径
        """
        self.file_path = file_path

    def execute(self, params: Dict[str, Any]) -> Any:
        """执行文件操作

        :param params: 文件操作参数，必须包含 "mode"（"read", "write", "append"），可选 "data"（写入内容）
        :return: 文件内容（读取时）或操作状态
        """
        mode = params.get("mode")
        if not mode:
            raise ValueError("Missing required parameter 'mode' for file execution")

        try:
            if mode == "read":
                with open(self.file_path, "rb") as f:
                    return f.read()  # 返回二进制数据
            elif mode in ("write", "append"):
                data = params.get("data", b"")
                if isinstance(data, str):
                    data = data.encode("utf-8")
                with open(self.file_path, "wb" if mode == "write" else "ab") as f:
                    f.write(data)
                return {"status": "success", "bytes_written": len(data)}
            else:
                raise ValueError(f"Unsupported file mode: {mode}")
        except Exception as e:
            raise RuntimeError(f"File operation failed on {self.file_path}: {str(e)}")