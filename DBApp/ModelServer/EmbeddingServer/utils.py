import requests
import json
import numpy as np


def embedding_encode(prompts, embedding_url="http://36.137.165.26:11435/v1/embeddings",  # 更新为 curl 中的地址
                 model="bge-m3",  # 更新为 curl 中的模型
                 api_key="gpustack_1806ac6f7f3e4818_e46a40b068509a2a07740411672e4e45"):

    """调用嵌入服务生成嵌入向量"""
    headers = {
        "Content-Type": "application/json",
    }
    # 如果提供了 API 密钥，添加 Authorization 头
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # payload 与 curl 请求一致，input 是一个列表
    payload = {
        "model": model,
        "input": [prompts]  # 将单一 content 包装成列表
    }

    response = requests.post(embedding_url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        # 根据 OpenAI 兼容接口规范，嵌入结果通常在 'data' 字段中
        response_json = response.json()
        embeddings = [item["embedding"] for item in response_json.get("data", [])]
        if embeddings:
            return embeddings[0]  # 返回第一个嵌入向量
        raise ValueError("No embeddings returned in response")
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")