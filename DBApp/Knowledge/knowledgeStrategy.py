from abc import ABC, abstractmethod
from .meta_chunk import Chunk
from typing import Dict
import requests
import json
import numpy as np
from ..ModelServer.EmbeddingServer.utils import embedding_encode


# 抽象知识提取器
class KnowledgeExtractor(ABC):
    @abstractmethod
    def extract(self, chunk: Chunk) -> Dict[str, str]:
        """从 Chunk 中提取知识并返回结果"""
        pass


# 关键词提取器
class KeywordExtractor(KnowledgeExtractor):
    def extract(self, chunk: Chunk) -> Dict[str, str]:
        words = chunk.content.split()
        # 简单过滤：长度大于3且为字母的词
        keywords = [word for word in words if len(word) > 3 and word.isalpha()]
        result = {"keywords": ", ".join(keywords[:5])}  # 取前5个关键词
        return result


# 图片引用提取器
class ImageRefExtractor(KnowledgeExtractor):
    def extract(self, chunk: Chunk) -> Dict[str, str]:
        image_refs = []
        for line in chunk.content.split("\n"):
            if line.startswith("![") and "](" in line:
                ref = line.split("](")[1].rstrip(")")
                image_refs.append(ref)
        if image_refs:
            chunk.metadata.image_refs = image_refs
            result = {"image_refs": ", ".join(image_refs)}
            return result
        return {}


# 自定义信息提取器
class CustomInfoExtractor(KnowledgeExtractor):
    def extract(self, custom_up_info: dict) -> Dict[str, str]:
        # 检查 custom_info 是否为字典
        if not isinstance(custom_up_info, dict):
            return {}
        # 定义重要字段列表，可以根据需求调整
        important_fields = ["CustomID", "ResourceFileName", "DBName", "file_name"]  # 示例字段，可自定义
        extracted_data = {}
        # 提取重要字段
        for field in important_fields:
            if field in custom_up_info["temp_info"]:
                extracted_data[field] = str(custom_up_info["temp_info"][field])  # 转换为字符串确保一致性
            if field in custom_up_info["save_info"]:
                extracted_data[field] = str(custom_up_info["save_info"][field])  # 转换为字符串确保一致性
        return extracted_data


# 自定义信息提取器
class ContextEmbeddingExtractor(KnowledgeExtractor):

    def extract(self, chunk: Chunk) -> Dict[str, str]:
        """从 chunk 中提取信息并生成嵌入向量"""
        # 生成嵌入向量
        embedding_vector = embedding_encode(chunk.content)
        # 更新 chunk 的 metadata
        result = {}
        if embedding_vector is not None:
            # 如果需要存储到 metadata，可以取消注释
            result = {"embedding": embedding_vector}  # 返回嵌入向量列表
        return result if result else {}

