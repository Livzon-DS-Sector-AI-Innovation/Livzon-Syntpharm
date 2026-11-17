"""LLM 服务模块 - 使用 core.llm 统一客户端"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

from app.core.llm import llm_client  # noqa: E402
from app.core.llm.exceptions import LLMOutputError, LLMProviderError, LLMRateLimitError  # noqa: E402


async def call_llm(prompt: str, system_prompt: str = "") -> dict[str, Any]:
    """调用 LLM API - 使用 core.llm 统一客户端"""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        return await llm_client.chat_json(messages)
    except (LLMOutputError, LLMProviderError, LLMRateLimitError) as e:
        logger.exception("LLM call failed")
        return {"error": f"AI 分析暂时不可用，请人工审核: {e}"}


def build_q3d_prompt(text: str) -> str:
    """构建 Q3D 元素识别 prompt"""
    return f"""你是一个制药工艺分析专家。请从以下药品合成工艺文本中提取所有需要评估的元素杂质。

## 任务
1. 识别文本中提到的所有元素（催化剂、试剂、设备来源等）
2. 确定每个元素的来源
3. 判断是否为有意添加（催化剂/试剂 vs 设备/杂质）

## 文本内容
{text}

## 输出格式
请输出 JSON 格式：
{{
  "elements": [
    {{
      "symbol": "元素符号（如 Pd, Ni, Co 等）",
      "source": "来源描述（如：钯碳催化剂、不锈钢反应器等）",
      "intentionally_added": true/false
    }}
  ]
}}

注意：
- 只输出 JSON，不要输出其他内容
- 如果文本中没有提到任何元素，返回 {{"elements": []}}
- symbol 必须是标准的元素符号
"""


async def extract_elements_with_llm(text: str) -> list[dict[str, Any]]:
    """使用 LLM 从文本中提取元素"""
    prompt = build_q3d_prompt(text)
    result = await call_llm(prompt)
    return result.get("elements", [])  # type: ignore[no-any-return]
