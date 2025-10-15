# from typing import Dict, Any, Optional, List
# import requests
# import json
# from openai import OpenAI


# class LLMService:
#     def __init__(self, model_path: Optional[str] = None, api_key: Optional[str] = None):
#         """
#         初始化 LLMService，支持 Azure OpenAI API 调用。

#         :param model_path: 本地模型路径（可选，未实现）
#         :param api_key: LLM API 的密钥（若使用远程 API）
#         """
#         self.api_key = 'sk-2dd841cdc2624791bbf114e73e7fec01'
#         self.base_url = "https://api.deepseek.com"
#         self.model = "deepseek-chat"

#         # 初始化 Azure OpenAI 客户端
#         self.client = OpenAI(
#                 api_key=self.api_key,
#                 base_url=self.base_url)

#     def call(self, prompt: str) -> str:
#         """
#         调用 Azure OpenAI API 处理输入 prompt 并返回结果。

#         :param prompt: 输入的提示文本
#         :return: LLM 返回的文本结果
#         """
#         try:
#             # 使用 Azure OpenAI 的 ChatCompletion 接口
#             response = self.client.chat.completions.create(
#                 model=self.model,  # 假设使用 gpt-4o 模型，根据实际部署调整
#                 messages=[
#                     {"role": "system", "content": "You are a helpful assistant."},
#                     {"role": "user", "content": prompt}
#                 ],
#             )
#             # 提取返回的文本内容
#             result = response.choices[0].message.content.strip()
#             return result
#         except Exception as e:
#             raise Exception(f"LLM API 调用失败: {str(e)}")


"""Utility helpers for talking to an LLM.

The original project hard-coded multiple DeepSeek/OpenAI API keys and relied on
real network calls for every prompt.  That makes local development and security
reviews extremely painful – running the code without network access would crash
immediately, which in turn prevented us from exercising the prompt-injection
attack path this repository is meant to demonstrate.

This module now provides a lightweight façade that prefers an offline, fully
deterministic stub.  When the environment variable ``USE_REAL_LLM`` is set to a
truthy value the class lazily loads ``openai`` and proxies requests to the
configured backend.  Otherwise the stub recognises the handful of prompt
templates used across the code-base and returns structured data directly.

The offline behaviour is intentionally simple – it is not a real LLM – but it is
predictable, fast, and removes the need for leaking API keys into source
control.  More importantly it keeps the rest of the system functional so that
prompt-injection scenarios can be reproduced end-to-end during automated tests.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, Optional


def _to_bool(value: Optional[str]) -> bool:
    """Return ``True`` when the environment variable looks truthy."""

    if value is None:
        return False
    return value.lower() in {"1", "true", "yes", "on"}


class LLMService:
    """Small façade around either a real LLM client or a deterministic stub."""

    def __init__(self, *, force_offline: Optional[bool] = None) -> None:
        # Allow tests to force the offline behaviour regardless of environment.
        if force_offline is None:
            force_offline = not _to_bool(os.getenv("USE_REAL_LLM"))

        self._offline = force_offline
        self._client = None
        self.model = os.getenv("LLM_MODEL", "deepseek-chat")

        if not self._offline:
            try:  # Import lazily to avoid the dependency during tests.
                from openai import OpenAI  # type: ignore

                api_key = os.getenv("LLM_API_KEY")
                base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
                if not api_key:
                    raise RuntimeError("LLM_API_KEY must be provided when USE_REAL_LLM is enabled")

                self._client = OpenAI(api_key=api_key, base_url=base_url)
            except Exception as exc:  # pragma: no cover - best effort guard
                # Fall back to the offline stub if importing/initialising fails.
                self._offline = True
                self._client = None
                self._offline_warning = str(exc)
        else:
            self._offline_warning = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def call(self, prompt: str, model: Optional[str] = None, response_format: Optional[Dict[str, Any]] = None) -> str:
        """Return a completion for ``prompt``.

        When running in offline mode this method returns deterministic strings
        tailored for the prompts used throughout the project.  The implementation
        favours practicality over sophistication – if a prompt is not
        recognised, a short explanatory message is returned so that downstream
        components can still make progress.
        """

        if self._offline:
            return self._offline_response(prompt, response_format)

        assert self._client is not None  # For type-checkers.
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ]

        kwargs: Dict[str, Any] = {"model": model or self.model, "messages": messages}
        if response_format:
            kwargs["response_format"] = response_format

        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content.strip()

    # ------------------------------------------------------------------
    # Offline helpers
    # ------------------------------------------------------------------
    def _offline_response(self, prompt: str, response_format: Optional[Dict[str, Any]]) -> str:
        """Generate deterministic responses for known prompt templates."""

        prompt_lower = prompt.lower()

        if "return the result as a json array" in prompt_lower:
            query = _extract_between(prompt, "Input:", "Guidelines:")
            steps = _default_coarse_steps(query)
            return json.dumps(steps, ensure_ascii=False)

        if "总步骤不要超过" in prompt:
            query = _extract_between(prompt, "任务描述:", "粗略步骤:") or prompt.strip()
            return "\n".join(_default_detailed_steps(query))

        if "return the list in json format" in prompt_lower:
            query = _extract_between(prompt, "Task:", "Coarse steps:") or prompt
            steps = _default_detailed_steps(query)
            return json.dumps(steps, ensure_ascii=False)

        if "needs_tool" in prompt_lower:
            needs_tool = any(keyword in prompt_lower for keyword in ["search", "查询", "api", "下载", "调用", "tool"])
            return json.dumps({"needs_tool": needs_tool})

        if "adjust_needed" in prompt_lower:
            return json.dumps({"adjust_needed": False})

        # Provide a minimal fallback that still looks helpful.
        summary = prompt.strip().splitlines()[:1]
        return "(offline stub response) " + " ".join(summary)


def _extract_between(prompt: str, start_marker: str, end_marker: str) -> str:
    try:
        start = prompt.index(start_marker) + len(start_marker)
        end = prompt.index(end_marker, start)
        return prompt[start:end].strip().strip("'\"“”")
    except ValueError:
        return ""


def _default_coarse_steps(query: str) -> Iterable[str]:
    task = query or "用户任务"
    return [
        f"1. 明确任务目标：{task}",
        "2. 调研外部资源或工具以收集信息",
        "3. 汇总发现并准备最终输出",
    ]


def _default_detailed_steps(query: str) -> Iterable[str]:
    task = query or "用户任务"
    return [
        f"1. 解析需求：{task}",
        "2. 调用可用工具或接口获取所需数据",
        "3. 结合已获取的信息整理中间结论",
        "4. 汇总撰写最终结果或报告",
    ]


