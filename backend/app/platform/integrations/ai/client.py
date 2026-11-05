"""业务侧 AI 适配层。

历史包袱：这里曾用 `httpx` 自建一套 OpenAI 兼容客户端（自带 api_key/base_url/model），
与 `app/core/llm/` 的全局单例 `llm_client` 形成两套 LLM 调用栈 —— 配置来源、密钥加密、
日志与重试都不一致。现在只保留**薄适配层**：所有请求都转给 `llm_client`，
本文件不再持有任何 API Key 与 HTTP 客户端。

保留 `chat_parsed` / `chat_vision_parsed` 两个方法是为了不打断 safety 插件的既有契约；
它们内部走 `llm_client.chat_json` / `chat_vision_json`，并把 `LLMOutputError`
翻译成插件约定的 `AIOutputError`。
"""

from __future__ import annotations

from typing import Any

from app.core.llm import llm_client
from app.core.llm.exceptions import LLMOutputError


class AIOutputError(Exception):
    """Raised when AI response cannot be parsed into expected structure."""

    def __init__(self, message: str, raw_response: str | None = None):
        self.message = message
        self.raw_response = raw_response
        super().__init__(message)

    def __str__(self) -> str:
        if self.raw_response:
            return f"{self.message} (raw: {self.raw_response[:200]})"
        return self.message


class AIService:
    """全局 `llm_client` 的业务侧适配器（不持有配置，不新建 HTTP 客户端）。"""

    async def close(self) -> None:
        """兼容历史的 `finally: await ai.close()` 调用。

        底层是全局单例 `llm_client`，由应用生命周期管理，这里不能真关，
        否则后续所有模块的 LLM 调用都会失败。
        """
        return None

    async def chat(
        self,
        messages: list[dict[str, Any]],
        response_format: str = "json_object",
        temperature: float = 0.1,
        max_tokens: int = 16384,
    ) -> str:
        """发送对话请求，返回文本响应。"""
        return await llm_client.chat(
            messages,
            response_format=response_format,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def chat_parsed(
        self,
        messages: list[dict[str, Any]],
        expected_keys: list[str],
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """对话 + 解析 JSON，并校验必需字段。"""
        try:
            return await llm_client.chat_json(
                messages,
                expected_keys=expected_keys,
                temperature=temperature,
            )
        except LLMOutputError as exc:
            raise AIOutputError(str(exc)) from exc

    async def chat_vision(
        self,
        text_prompt: str,
        image_urls: list[str],
        temperature: float = 0.1,
        max_tokens: int = 16384,
    ) -> str:
        """发送多模态（视觉）对话请求，返回文本响应。"""
        return await llm_client.chat_vision(
            text_prompt,
            image_urls,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def chat_vision_parsed(
        self,
        text_prompt: str,
        image_urls: list[str],
        expected_keys: list[str],
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """视觉对话 + 解析 JSON，并校验必需字段。"""
        try:
            return await llm_client.chat_vision_json(
                text_prompt,
                image_urls,
                expected_keys=expected_keys,
                temperature=temperature,
            )
        except LLMOutputError as exc:
            raise AIOutputError(str(exc)) from exc


__all__ = ["AIOutputError", "AIService"]
