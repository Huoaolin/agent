import logging


class Logger:
    def __init__(self, name: str = "TaskExecutor", log_level=logging.WARNING):
        """
        初始化日志记录器。

        :param name: 日志记录器的名称。
        :param log_level: 日志级别（默认为 WARNING）。
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # 控制台日志处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def info(self, message: str):
        """
        记录信息日志。
        """
        self.logger.info(message)

    def warning(self, message: str):
        """
        记录警告日志。
        """
        self.logger.warning(message)

    def error(self, message: str):
        """
        记录错误日志。
        """
        self.logger.error(message)