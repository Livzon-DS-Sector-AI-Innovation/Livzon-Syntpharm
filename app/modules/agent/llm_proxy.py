from collections.abc import AsyncIterator
from typing import Any

import httpx
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.llm.config import get_config

SUPPORTED_FIELDS = {
    "messages",
    "tools",
    "tool_choice",
    "temperature",
    "max_tokens",
    "stream",
    "response_format",
    "parallel_tool_calls",
    "stop",
    "top_p",
}


async def list_active_text_models() -> dict[str, Any]:
    config = await get_config("text")
    return {
        "object": "list",
        "data": [
            {
                "id": "dazah-active-text",
                "object": "model",
                "owned_by": "dazah",
                "root": config.model_name,
            }
        ],
    }


async def forward_chat_completion(payload: dict[str, Any]) -> Any:
    config = await get_config("text")
    body = {key: value for key, value in payload.items() if key in SUPPORTED_FIELDS}
    body["model"] = config.model_name
    body.setdefault("temperature", config.temperature)
    url = config.api_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    timeout = httpx.Timeout(config.timeout_seconds)
    if body.get("stream"):
        return StreamingResponse(
            _stream_chat(url, headers, body, timeout),
            media_type="text/event-stream",
        )
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=body)
    if response.status_code >= 400:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, response.text[:1000])
    return response.json()


async def _stream_chat(
    url: str,
    headers: dict[str, str],
    body: dict[str, Any],
    timeout: httpx.Timeout,
) -> AsyncIterator[bytes]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, headers=headers, json=body) as response:
            if response.status_code >= 400:
                detail = await response.aread()
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY, detail.decode(errors="ignore")[:1000]
                )
            async for chunk in response.aiter_bytes():
                yield chunk
