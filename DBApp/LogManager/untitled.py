import logging
import os
from typing import Optional
import yaml

class LoggerManager:
    _instance = None

    def __new__(cls, config_path: Optional[str] = None):
        """单例模式，确保全局只有一个 LoggerManager 实例"""
        if cls._instance is None:
            cls._instance = super(LoggerManager, cls).__new__(cls)
            cls._instance._initialize(config_path)
        return cls._instance

    def _initialize(self, config_path: Optional[str]):
        """初始化日志配置"""
        self.logger = logging.getLogger("FileProcessingProject")
        self.logger.setLevel(logging.INFO)  # 默认级别

        # 清除已有处理器，避免重复添加
        if self.logger.handlers:
            self.logger.handlers.clear()

        # 默认配置：控制台输出
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # 如果提供了配置文件，则加载
        if config_path and os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                self._apply_config(config)

    def _apply_config(self, config: dict):
        """根据配置文件应用日志设置"""
        self.logger.setLevel(config.get("level", "INFO"))

        # 文件处理器
        if "file" in config:
            file_handler = logging.FileHandler(config["file"]["path"])
            file_handler.setLevel(config["file"].get("level", "INFO"))
            formatter = logging.Formatter(config["file"].get("format", "%(asctime)s - %(levelname)s - %(message)s"))
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def get_logger(self) -> logging.Logger:
        """获取全局日志实例"""
        return self.logger


# 示例配置文件（logging_config.yaml）
"""
logging:
  level: INFO
  file:
    path: ./logManager/logs/project.log
    level: DEBUG
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
"""