from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()


class LLMCall:
    def __init__(self):
        self.api_key = 'sk-61f58010fd3e43bebe727d4b3536ccfe'
        self.base_url = "https://api.deepseek.com"
        self.model = "deepseek-chat"
        # 初始化 OpenAI 客户端（兼容 DeepSeek API）
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def call(self, prompt, model=None, response_format=None):
        """
        调用 LLM 并返回结果。

        Args:
            prompt (str): 输入提示词
            model (str, optional): 使用的模型，默认为实例中的 self.model
            response_format (dict, optional): 响应格式，默认不指定

        Returns:
            str: LLM 返回的原始结果
        """
        try:
            # 如果未指定 model，则使用默认的 self.model
            model = model or self.model
            # 设置消息
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
            # 如果提供了 response_format，则使用它
            kwargs = {"model": model, "messages": messages}
            if response_format:
                kwargs["response_format"] = response_format

            # 调用 DeepSeek API
            response = self.client.chat.completions.create(**kwargs)
            # 提取返回的文本内容
            result = response.choices[0].message.content.strip()
            return result
        except Exception as e:
            raise Exception(f"LLM API 调用失败: {str(e)}")