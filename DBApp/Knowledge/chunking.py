from .chunkStrategy import FixedLengthChunker, Chunker
import os
from typing import List
from .meta_chunk import Chunk

# 切片工厂
class ChunkerFactory:
    @staticmethod
    def create_chunker(strategy: str) -> Chunker:
        if strategy == "fixed_length":
            return FixedLengthChunker()
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")


# 切片任务
class ChunkingTask:
    def __init__(self, strategy: str = "fixed_length"):
        self.chunker = ChunkerFactory.create_chunker(strategy)

    def execute(self, temp_info) -> List[Chunk]:
        base_path = temp_info['temp_base_path']
        filename = temp_info['file_name']
        """执行切片任务"""
        folder_path = os.path.join(base_path, filename)
        md_file = os.path.join(folder_path, f"{filename}.md")

        if not os.path.exists(md_file):
            raise FileNotFoundError(f"Markdown file not found: {md_file}")

        try:
            with open(md_file, "r", encoding="utf-8") as f:
                markdown_text = f.read()
            chunks = self.chunker.split(markdown_text, md_file)
            return chunks

        except Exception as e:
            raise