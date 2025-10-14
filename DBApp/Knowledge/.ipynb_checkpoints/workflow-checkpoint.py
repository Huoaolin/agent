from abc import ABC, abstractmethod
from .meta_chunk import Chunk
from typing import List
from .knowledgeExtraction import ExtractionTask
from .chunking import ChunkingTask


# 抽象任务
class Task(ABC):
    @abstractmethod
    def execute(self, input_data: any) -> any:
        pass


# 任务链
class TaskChain:
    def __init__(self):
        self.tasks: List[Task] = []

    def add_task(self, task: Task):
        self.tasks.append(task)

    def run(self, custom_up_info) -> List[Chunk]:
        result = None
        temp_info = custom_up_info["temp_info"]
        save_info = custom_up_info["save_info"]
        for task in self.tasks:
            if result is None:
                result = task.execute(temp_info)  # 第一个任务需要文件名和路径
            else:
                result = task.execute(result, custom_up_info)  # 后续任务使用前一任务的输出
        return result


# 主流程
class KnowledgeExtractionWorkflow:
    def process(self, custom_up_info) -> List[Chunk]:
        chain = TaskChain()
        # 分片任务
        chunking_task = ChunkingTask(strategy="fixed_length")
        chain.add_task(chunking_task)
        # 知识提取任务
        extraction_task = ExtractionTask(strategies=["keywords", "image_refs", "custom_info", "embedding"])
        chain.add_task(extraction_task)
        # maby 向量化等...
        return chain.run(custom_up_info)
