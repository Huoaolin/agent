from abc import ABC, abstractmethod
import uuid
from .meta_chunk import Chunk, Metadata
from typing import List


# 抽象切片器
class Chunker(ABC):
    @abstractmethod
    def split(self, markdown_text: str, source_file: str) -> List[Chunk]:
        """将 Markdown 文本切分为 Chunk"""
        pass


# 固定长度切片器
class FixedLengthChunker(Chunker):
    def __init__(self, chunk_size: int = 512):
        self.chunk_size = chunk_size

    def split(self, markdown_text: str, source_file: str) -> List[Chunk]:
        chunks = []
        lines = markdown_text.split("\n")
        current_chunk = ""
        offset_start = 0

        for line in lines:
            if len(current_chunk) + len(line) > self.chunk_size:
                if current_chunk:
                    metadata = Metadata(
                        id=str(uuid.uuid4()),
                        source_file=source_file,
                        chunk_type="text",
                        storage_location="",
                        offset_start=offset_start,
                        offset_end=offset_start + len(current_chunk)
                    )
                    chunks.append(Chunk(content=current_chunk.strip(), metadata=metadata))
                current_chunk = line
                offset_start += len(current_chunk) + 1
            else:
                current_chunk += "\n" + line if current_chunk else line
        if current_chunk:
            metadata = Metadata(
                id=str(uuid.uuid4()),
                source_file=source_file,
                chunk_type="text",
                storage_location="",
                offset_start=offset_start,
                offset_end=offset_start + len(current_chunk)
            )
            chunks.append(Chunk(content=current_chunk.strip(), metadata=metadata))

        return chunks