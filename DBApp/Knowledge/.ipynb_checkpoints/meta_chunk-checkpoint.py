from dataclasses import dataclass
from typing import Dict, List, Optional


# 元数据定义
@dataclass
class Metadata:
    id: str                     # 唯一标识符
    source_file: str            # 源文件路径
    chunk_type: str             # Chunk 类型（"text" 或 "image"）
    storage_location: str       # 存储位置（预留）
    offset_start: int           # 起始偏移量
    offset_end: int             # 结束偏移量
    extracted_info: Dict[str, str] = None  # 提取信息（默认空，由后续提取填充）
    image_refs: Optional[List[str]] = None  # 图片引用（默认空）
    embeddingVector: List = None

    def __post_init__(self):
        if self.extracted_info is None:
            self.extracted_info = {}

# Chunk 定义
@dataclass
class Chunk:
    content: str        # Chunk 内容
    metadata: Metadata  # 元数据