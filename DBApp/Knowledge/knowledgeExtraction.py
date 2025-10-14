from .knowledgeStrategy import KnowledgeExtractor, KeywordExtractor, ImageRefExtractor, CustomInfoExtractor, ContextEmbeddingExtractor
from .meta_chunk import Chunk
from typing import List
from typing import List, Dict


# 提取工厂
class ExtractorFactory:
    @staticmethod
    def create_extractor(strategy: str) -> KnowledgeExtractor:
        if strategy == "keywords":
            return KeywordExtractor()
        elif strategy == "image_refs":
            return ImageRefExtractor()
        elif strategy == "custom_info":
            return CustomInfoExtractor()
        elif strategy == "embedding":
            return ContextEmbeddingExtractor()
        else:
            raise ValueError(f"Unknown extraction strategy: {strategy}")


class ExtractionTask:
    """负责执行知识提取任务的类，支持多种提取策略"""
    def __init__(self, strategies: List[str] = None):
        """
        初始化提取任务，创建对应的提取器实例。
        Args:
            strategies: 提取策略列表，默认为 ["keywords"]。
        """
        # 如果未提供 strategies，默认使用 ["keywords"]
        strategies = strategies or ["keywords"]
        self.extractors = [ExtractorFactory.create_extractor(strategy) for strategy in strategies]

    def execute(self, chunks: List[Chunk], custom_up_info: Dict = None) -> List[Chunk]:
        """
        执行知识提取任务，将提取结果存储到 chunk 的 metadata 中。

        Args:
            chunks: 输入的 Chunk 对象列表。
            custom_info: 可选的自定义信息字典，供 CustomInfoExtractor 使用。

        Returns:
            处理后的 Chunk 列表。

        Raises:
            ValueError: 如果 CustomInfoExtractor 需要 custom_info 但未提供。
            Exception: 提取过程中发生其他错误。
        """
        try:
            for chunk in chunks:
                # 初始化提取结果字典
                extracted_info = {}

                # 对每个提取器分别处理
                for extractor in self.extractors:
                    # 用户信息提取
                    if isinstance(extractor, CustomInfoExtractor):
                        if custom_up_info is None:
                            raise ValueError("custom_info is required for CustomInfoExtractor")
                        extracted_info.update(extractor.extract(custom_up_info))
                    # context向量化
                    elif isinstance(extractor, ContextEmbeddingExtractor):
                        # ContextEmbeddingExtractor 直接更新 chunk.metadata
                        chunk.metadata.embeddingVector = extractor.extract(chunk)
                    # 其他提取（keywords，图片路径等）
                    else:
                        # 其他提取器将结果合并到 extracted_info
                        extracted_info.update(extractor.extract(chunk))

                # 将提取的信息存储到 chunk.metadata.extracted_info
                if extracted_info:
                    chunk.metadata.extracted_info = extracted_info

            return chunks

        except Exception as e:
            raise RuntimeError(f"Error during extraction task execution: {str(e)}") from e