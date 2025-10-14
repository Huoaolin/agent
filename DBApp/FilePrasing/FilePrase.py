from typing import List, Optional, Tuple
import os
import requests  # 用于调用外部服务，可以根据实际替换为其他通信方式
import uuid
from .File2MarkdownProcesser import PDFProcessor, WordProcessor, ImageProcessor, FileProcessor


# 文件处理器工厂
class FileProcessorFactory:
    @staticmethod
    def create_processor(file_path: str) -> FileProcessor:
        ext = os.path.splitext(file_path.lower())[1]
        if ext == ".pdf":
            return PDFProcessor()
        elif ext in [".doc", ".docx"]:
            return WordProcessor()
        elif ext in [".png", ".jpg", ".jpeg"]:
            return ImageProcessor()
        else:
            raise ValueError(f"Unsupported file type: {ext}")


# 文件处理管道（责任链）
class FileProcessingPipeline:
    def __init__(self):
        # 初始化一个空的责任链步骤列表
        self.steps = []

    def add_step(self, processor: FileProcessor):
        # 添加一个处理步骤到责任链中
        # 参数 processor: 一个文件处理器实例，类型为 FileProcessor
        self.steps.append(processor)

    def process(self, file_path: str) -> str:
        # 执行责任链中的所有处理步骤，依次处理文件
        # 参数 file_path: 需要处理的文件路径（字符串）
        # 返回值: 处理后的结果（字符串）
        result = None
        for step in self.steps:
            # 遍历责任链中的每个处理器，依次调用其 process 方法
            result = step.process(file_path)
        return result


# 使用示例
def process_file(file_path: str) -> str:
    # 定义一个文件处理函数，用于处理指定路径的文件
    # 参数 file_path: 需要处理的文件路径（字符串）
    # 返回值: 处理后的 Markdown 内容（字符串）

    # 创建一个文件处理器工厂实例
    factory = FileProcessorFactory()
    # 根据文件路径，通过工厂创建一个合适的处理器实例
    processor = factory.create_processor(file_path)
    # 创建一个文件处理管道实例（责任链）
    pipeline = FileProcessingPipeline()
    # 将处理器添加到管道的责任链中
    pipeline.add_step(processor)
    # 执行管道处理，获取 Markdown 内容
    pipeline.process(file_path)