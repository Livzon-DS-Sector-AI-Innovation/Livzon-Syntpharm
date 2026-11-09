"""Unified LLM client interface."""

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from .config import LLMConfigData, get_config, get_named_config
from .exceptions import LLMOutputError, LLMProviderError, LLMRateLimitError, LLMToolsUnsupportedError

# 端点拒绝 tools 时常见的错误文本片段（不同网关措辞差异较大，宁可多匹配几个）
_TOOLS_UNSUPPORTED_HINTS = (
    "tools",
    "tool_choice",
    "function",
    "response_format",
    "not supported",
    "unsupported",
    "does not support",
    "tool calling",
)


@dataclass(slots=True)
class LLMToolCall:
    """一次工具调用（arguments 已解析为 dict）。"""

    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    arguments_raw: str = ""
    parse_error: str | None = None


@dataclass(slots=True)
class LLMResponse:
    """tool-calling 调用的返回：正文 + 工具调用列表。"""

    content: str = ""
    tool_calls: list[LLMToolCall] = field(default_factory=list)
    finish_reason: str | None = None


class LLMClient:
    """Unified LLM client for all modules.

    Usage:
        from app.core.llm import llm_client

        result = await llm_client.chat([{"role": "user", "content": "Hello"}])
    """

    def __init__(self) -> None:
        # 连接池：按 config.id 缓存 httpx.AsyncClient，避免每次调用都重建 TCP+TLS 连接
        self._client_pool: dict[str, httpx.AsyncClient] = {}

    def _get_or_create_client(self, config: LLMConfigData) -> httpx.AsyncClient:
        """复用已有连接或创建新连接。同一 config 的所有调用共享一个 httpx client。"""
        client = self._client_pool.get(config.id)
        if client is not None and not client.is_closed:
            return client
        client = httpx.AsyncClient(
            base_url=config.api_base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=config.timeout_seconds,
        )
        self._client_pool[config.id] = client
        return client

    async def _get_client_and_config(
        self, config_type: str = "text", config_name: str | None = None
    ) -> tuple[httpx.AsyncClient, LLMConfigData]:
        """Get HTTP client and config.

        Args:
            config_type: "text" or "vision"
            config_name: Pin a specific config by name instead of the active one
                (endpoint and key come from that config too). Missing name falls
                back to the active config so a stale setting never breaks a flow.
        """
        config: LLMConfigData | None = None
        if config_name and config_name.strip():
            config = await get_named_config(config_name, config_type)
        if config is None:
            config = await get_config(config_type)

        client = self._get_or_create_client(config)
        return client, config

    async def chat(
        self,
        messages: list[dict[str, Any]],
        response_format: str | None = "json_object",
        temperature: float | None = None,
        max_tokens: int = 16384,
        config_type: str = "text",
        model_override: str | None = None,
        config_name: str | None = None,
    ) -> str:
        """Send a chat completion request and return the response text.

        Args:
            messages: List of message dicts with 'role' and 'content'
            response_format: "json_object" or None
            temperature: Override config temperature
            max_tokens: Max tokens in response
            config_type: "text" or "vision"
            model_override: Override model name (for fallback/primary switch)
            config_name: Pin a specific config (its endpoint, key and model)

        Returns:
            Response text from LLM

        Raises:
            LLMProviderError: If provider returns error
            LLMRateLimitError: If rate limit exceeded
        """
        client, config = await self._get_client_and_config(config_type, config_name)

        # Use config temperature if not overridden
        temp = temperature if temperature is not None else config.temperature

        # For json_object format, ensure "json" appears in the prompt
        msgs = [dict(m) for m in messages]
        if response_format == "json_object":
            last = msgs[-1]
            if isinstance(last.get("content"), str) and "json" not in last["content"].lower():
                last["content"] = last["content"] + "\n\n请以 JSON 格式返回结果。"

        body = {
            "model": model_override or config.model_name,
            "messages": msgs,
            "temperature": temp,
            "max_tokens": max_tokens,
        }
        if response_format:
            body["response_format"] = {"type": response_format}

        # Retry logic for transient errors (max 3 retries = 4 total attempts)
        # 注意：client 来自连接池（按 config 共享），重试后不可 aclose，否则破坏连接复用
        last_error: Exception | None = None
        for attempt in range(4):
            try:
                resp = await client.post("/chat/completions", json=body)

                if resp.status_code == 429:
                    raise LLMRateLimitError("Rate limit exceeded", status_code=429)

                if resp.is_error:
                    error_text = resp.text[:500]
                    raise LLMProviderError(
                        f"LLM API error: {resp.status_code} - {error_text}",
                        status_code=resp.status_code,
                        raw_response=error_text,
                    )

                data = resp.json()
                return data["choices"][0]["message"]["content"]  # type: ignore[no-any-return]

            except (LLMRateLimitError, httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
                last_error = e
                if attempt < 3:
                    # Exponential backoff: 1s, 2s, 4s
                    await asyncio.sleep(2**attempt)
                    continue
                raise

        # Should not reach here, but just in case
        if last_error:
            raise last_error
        raise LLMProviderError("LLM request failed after 4 attempts")

    async def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        *,
        temperature: float | None = None,
        max_tokens: int = 16384,
        config_type: str = "text",
        model_override: str | None = None,
        config_name: str | None = None,
        tool_choice: str = "auto",
    ) -> LLMResponse:
        """OpenAI 兼容的 tool calling 调用，返回正文与工具调用列表。

        刻意**不**发送 ``response_format``：部分网关不允许 ``tools`` 与
        ``json_object`` 同时出现。需要结构化结果时由业务侧从工具入参拿。

        Args:
            messages: 对话消息（含上一轮的 assistant/tool 消息时按 OpenAI 协议原样传入）
            tools: ``[{"type": "function", "function": {...}}]``
            temperature: 覆盖配置温度
            max_tokens: 最大输出 token
            config_type: "text" 或 "vision"
            model_override: 覆盖模型名
            config_name: 指定命名配置（端点、密钥、模型都取自该配置）
            tool_choice: "auto" / "none" / "required"

        Raises:
            LLMToolsUnsupportedError: 端点明确拒绝 tools（调用方可降级为 JSON 协议）
            LLMProviderError: 其他供应商错误
            LLMRateLimitError: 限流
        """
        client, config = await self._get_client_and_config(config_type, config_name)
        temp = temperature if temperature is not None else config.temperature

        body: dict[str, Any] = {
            "model": model_override or config.model_name,
            "messages": [dict(m) for m in messages],
            "temperature": temp,
            "max_tokens": max_tokens,
            "tools": tools,
            "tool_choice": tool_choice,
        }

        last_error: Exception | None = None
        for attempt in range(4):
            try:
                resp = await client.post("/chat/completions", json=body)

                if resp.status_code == 429:
                    raise LLMRateLimitError("Rate limit exceeded", status_code=429)

                if resp.is_error:
                    error_text = resp.text[:500]
                    if resp.status_code in (400, 404, 422) and _looks_like_tools_unsupported(error_text):
                        raise LLMToolsUnsupportedError(
                            f"endpoint does not support tool calling: {resp.status_code}",
                            status_code=resp.status_code,
                            raw_response=error_text,
                        )
                    raise LLMProviderError(
                        f"LLM API error: {resp.status_code} - {error_text}",
                        status_code=resp.status_code,
                        raw_response=error_text,
                    )

                return _parse_tool_response(resp.json())

            except (LLMRateLimitError, httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
                last_error = e
                if attempt < 3:
                    await asyncio.sleep(2**attempt)
                    continue
                raise

        if last_error:
            raise last_error
        raise LLMProviderError("LLM request failed after 4 attempts")

    async def chat_json(
        self,
        messages: list[dict[str, Any]],
        expected_keys: list[str] | None = None,
        temperature: float | None = None,
        config_type: str = "text",
        model_override: str | None = None,
        config_name: str | None = None,
    ) -> dict[str, Any]:
        """Chat + parse JSON response.

        Args:
            messages: List of message dicts
            expected_keys: Optional list of keys to validate
            temperature: Override config temperature
            config_type: "text" or "vision"
            model_override: Override model name (for fallback/primary switch)
            config_name: Pin a specific config (its endpoint, key and model)

        Returns:
            Parsed JSON dict

        Raises:
            LLMOutputError: If response is not valid JSON or missing keys
        """
        raw = await self.chat(
            messages,
            response_format="json_object",
            temperature=temperature,
            config_type=config_type,
            model_override=model_override,
            config_name=config_name,
        )
        return _parse_json_payload(raw, expected_keys)

    async def stream_json(
        self,
        messages: list[dict[str, Any]],
        *,
        expected_keys: list[str] | None = None,
        temperature: float | None = None,
        max_tokens: int = 16384,
        config_type: str = "text",
        model_override: str | None = None,
        config_name: str | None = None,
    ) -> Any:
        """流式请求 JSON：边流边给增量，流完给解析结果。

        yield 三类事件（调用方可以直接转成 SSE）：
        - ``{"type": "reasoning", "text": "..."}`` 思考增量，模型不透传时没有这类事件
        - ``{"type": "content", "text": "..."}`` 正文增量（JSON 文本片段）
        - ``{"type": "result", "data": dict, "raw": str}`` 完整解析结果，只在最后出现一次

        与 ``chat_json`` 的区别：不传 ``response_format``（流式下网关支持差异大），
        改用提示词兜底要求 JSON；解析仍走同一套清洗逻辑，避免两条链路行为不一致。
        """
        msgs = _with_json_hint(messages)
        parts: list[str] = []
        async for chunk in self.stream_chat(
            msgs,
            temperature=temperature,
            max_tokens=max_tokens,
            model_override=model_override,
            config_name=config_name,
            config_type=config_type,
        ):
            if chunk.get("type") == "content":
                parts.append(str(chunk.get("text") or ""))
            yield chunk

        raw = "".join(parts)
        if not raw.strip():
            raise LLMOutputError("LLM 流式响应为空，没有可解析的 JSON", raw)
        yield {"type": "result", "data": _parse_json_payload(raw, expected_keys), "raw": raw}

    async def chat_vision(
        self,
        text_prompt: str,
        image_urls: list[str],
        temperature: float | None = None,
        max_tokens: int = 16384,
    ) -> str:
        """Send a multimodal chat request with images.

        Args:
            text_prompt: Text prompt
            image_urls: List of image URLs (can be data: URIs or http URLs)
            temperature: Override config temperature
            max_tokens: Max tokens in response

        Returns:
            Response text from LLM
        """
        client, config = await self._get_client_and_config("vision")

        temp = temperature if temperature is not None else config.temperature

        content_parts = [{"type": "text", "text": text_prompt}]
        for url in image_urls:
            content_parts.append({"type": "image_url", "image_url": {"url": url}})  # type: ignore[dict-item]

        body = {
            "model": config.model_name,
            "messages": [{"role": "user", "content": content_parts}],
            "temperature": temp,
            "max_tokens": max_tokens,
        }

        resp = await client.post("/chat/completions", json=body)

        if resp.status_code == 429:
            raise LLMRateLimitError("Rate limit exceeded", status_code=429)

        if resp.is_error:
            error_text = resp.text[:500]
            raise LLMProviderError(
                f"Vision API error: {resp.status_code} - {error_text}",
                status_code=resp.status_code,
                raw_response=error_text,
            )

        data = resp.json()
        return data["choices"][0]["message"]["content"]  # type: ignore[no-any-return]

    async def chat_vision_json(
        self,
        text_prompt: str,
        image_urls: list[str],
        expected_keys: list[str] | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Vision chat + parse JSON response.

        Args:
            text_prompt: Text prompt
            image_urls: List of image URLs
            expected_keys: Optional list of keys to validate
            temperature: Override config temperature

        Returns:
            Parsed JSON dict
        """
        raw = await self.chat_vision(
            text_prompt,
            image_urls,
            temperature=temperature,
        )

        # Strip markdown code fences
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            for i, line in enumerate(lines):
                if not line.strip().startswith("```"):
                    cleaned = "\n".join(lines[i:])
                    break
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise LLMOutputError("Vision LLM response is not valid JSON", raw) from e

        # Coerce boolean strings
        for k, v in parsed.items():
            if isinstance(v, str) and v.lower() in ("true", "false"):
                parsed[k] = v.lower() == "true"

        if expected_keys:
            missing = [k for k in expected_keys if k not in parsed]
            if missing:
                raise LLMOutputError(f"Vision LLM response missing keys: {missing}", raw)

        return parsed  # type: ignore[no-any-return]

    async def embed(
        self,
        texts: list[str],
        *,
        model_override: str | None = None,
        config_name: str | None = None,
    ) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Uses the OpenAI-compatible ``/embeddings`` endpoint. The embedding model
        is resolved via ``config_name`` (looking for ``config_type="embedding"``)
        or falls back to ``model_override`` on the active text config.

        Args:
            texts: List of strings to embed
            model_override: Override model name on the active text config
            config_name: Pin a specific embedding config

        Returns:
            List of embedding vectors (list of floats)

        Raises:
            LLMProviderError: If provider returns error
            LLMRateLimitError: If rate limit exceeded
        """
        config = None
        if config_name and config_name.strip():
            config = await get_named_config(config_name, "embedding")
        if config is None:
            config = await get_config("text")

        client = self._get_or_create_client(config)
        body: dict[str, Any] = {
            "model": model_override or config.model_name,
            "input": texts,
        }
        resp = await client.post("/embeddings", json=body)

        if resp.status_code == 429:
            raise LLMRateLimitError("Embedding rate limit exceeded", status_code=429)
        if resp.is_error:
            error_text = resp.text[:500]
            raise LLMProviderError(
                f"Embedding API error: {resp.status_code} - {error_text}",
                status_code=resp.status_code,
                raw_response=error_text,
            )

        data = resp.json()
        # Sort by index to preserve input order
        items = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in items]

    async def aclose_all(self) -> None:
        """关闭连接池中所有缓存的 httpx client。应用关闭时调用。"""
        for client in self._client_pool.values():
            if not client.is_closed:
                await client.aclose()
        self._client_pool.clear()

    async def health_check(self) -> dict[str, Any]:
        """Check LLM connectivity.

        Returns:
            Dict with 'status' and optional 'detail'
        """
        try:
            config = await get_config("text")
            client = httpx.AsyncClient(
                base_url=config.api_base_url.rstrip("/"),
                headers={"Authorization": f"Bearer {config.api_key}"},
                timeout=5.0,
            )
            try:
                resp = await client.get("/models")
                return {
                    "status": "ok" if resp.is_success else "error",
                    "detail": f"HTTP {resp.status_code}",
                }
            finally:
                await client.aclose()
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int = 4096,
        model_override: str | None = None,
        config_name: str | None = None,
        config_type: str = "text",
    ) -> Any:
        """Stream chat completion tokens.

        Yields dicts with keys:
            - type: "reasoning" | "content"
            - text: the token text

        ``config_name`` 与 ``model_override`` 语义见 ``chat``：前者整份切换配置，
        后者只换模型名。流式请求的 httpx timeout 是「两帧之间的读间隔」，
        因此长文本不再受配置里那个总时长限制。
        """
        import json as json_module

        client, config = await self._get_client_and_config(config_type, config_name)
        temp = temperature if temperature is not None else config.temperature

        body = {
            "model": model_override or config.model_name,
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tokens,
            "stream": True,
        }

        async with client.stream("POST", "/chat/completions", json=body) as resp:
            if resp.status_code == 429:
                raise LLMRateLimitError("Rate limit exceeded", status_code=429)

            if resp.is_error:
                error_text = await resp.aread()
                raise LLMProviderError(
                    f"Stream API error: {resp.status_code} - {error_text.decode()[:500]}",
                    status_code=resp.status_code,
                )

            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue

                data = line[6:]  # Remove "data: " prefix
                if data == "[DONE]":
                    break

                try:
                    chunk = json_module.loads(data)
                    if not chunk.get("choices"):
                        continue

                    delta = chunk["choices"][0].get("delta", {})
                    reasoning = delta.get("reasoning_content")
                    content = delta.get("content")

                    if reasoning:
                        yield {"type": "reasoning", "text": reasoning}
                    if content:
                        yield {"type": "content", "text": content}
                except json_module.JSONDecodeError:
                    continue


def _with_json_hint(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """流式请求没有 response_format，用提示词兜底要求 JSON（与 chat 的行为一致）。"""
    msgs = [dict(m) for m in messages]
    if not msgs:
        return msgs
    last = msgs[-1]
    if isinstance(last.get("content"), str) and "json" not in last["content"].lower():
        last["content"] = last["content"] + "\n\n请以 JSON 格式返回结果。"
    return msgs


def _parse_json_payload(raw: str, expected_keys: list[str] | None = None) -> dict[str, Any]:
    """把模型输出的 JSON 文本解析成 dict。

    ``chat_json`` 与 ``stream_json`` 共用这一段：两条链路如果各写一份清洗逻辑，
    出现「非流式能解析、流式解析不了」这类问题时很难定位。
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        for i, line in enumerate(lines):
            if not line.strip().startswith("```"):
                cleaned = "\n".join(lines[i:])
                break
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise LLMOutputError("LLM response is not valid JSON", raw) from e

    # Handle array responses - merge into single dict
    if isinstance(parsed, list):
        if len(parsed) == 0:
            raise LLMOutputError("LLM returned empty list", raw)
        if isinstance(parsed[0], dict):
            merged: dict[str, Any] = {}
            for item in parsed:
                for k, v in item.items():
                    if k in merged and isinstance(v, str):
                        merged[k] = merged[k] + "；" + v
                    else:
                        merged[k] = v
            parsed = merged
        else:
            parsed = {"_raw": raw}

    if not isinstance(parsed, dict):
        raise LLMOutputError("LLM response is not a JSON object", raw)

    # Coerce boolean strings
    for k, v in parsed.items():
        if isinstance(v, str) and v.lower() in ("true", "false"):
            parsed[k] = v.lower() == "true"

    # Validate expected keys
    if expected_keys:
        missing = [k for k in expected_keys if k not in parsed]
        if missing:
            raise LLMOutputError(f"LLM response missing keys: {missing}", raw)

    return parsed


def _looks_like_tools_unsupported(error_text: str) -> bool:
    """判断 400/422 是否因为端点不支持 tools，而不是参数本身写错。"""
    lowered = error_text.lower()
    return any(hint in lowered for hint in _TOOLS_UNSUPPORTED_HINTS)


def _parse_tool_response(data: dict[str, Any]) -> LLMResponse:
    """把供应商返回规范化成 ``LLMResponse``；单个 tool_call 参数坏掉不影响其他调用。"""
    try:
        message = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMOutputError(
            "LLM response missing choices/message", json.dumps(data, ensure_ascii=False)[:500]
        ) from exc

    content = message.get("content")
    calls: list[LLMToolCall] = []
    for index, item in enumerate(message.get("tool_calls") or []):
        function = item.get("function") or {}
        name = str(function.get("name") or "").strip()
        raw_arguments = function.get("arguments")
        if isinstance(raw_arguments, dict):
            arguments = raw_arguments
            arguments_raw = json.dumps(raw_arguments, ensure_ascii=False)
            parse_error = None
        else:
            arguments_raw = str(raw_arguments or "")
            arguments, parse_error = _load_arguments(arguments_raw)
        calls.append(
            LLMToolCall(
                id=str(item.get("id") or f"call_{index}"),
                name=name,
                arguments=arguments,
                arguments_raw=arguments_raw,
                parse_error=parse_error,
            )
        )

    finish_reason = None
    try:
        finish_reason = data["choices"][0].get("finish_reason")
    except (KeyError, IndexError, TypeError):
        finish_reason = None

    return LLMResponse(
        content=str(content or ""),
        tool_calls=calls,
        finish_reason=str(finish_reason) if finish_reason else None,
    )


def _load_arguments(raw: str) -> tuple[dict[str, Any], str | None]:
    """解析工具入参；模型偶尔返回空串或非对象 JSON，保留原文供上层记录。"""
    text = raw.strip()
    if not text:
        return {}, None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        return {}, f"arguments 不是合法 JSON: {exc.msg}"
    if not isinstance(parsed, dict):
        return {}, "arguments 不是 JSON 对象"
    return parsed, None


# Global singleton instance
llm_client = LLMClient()
