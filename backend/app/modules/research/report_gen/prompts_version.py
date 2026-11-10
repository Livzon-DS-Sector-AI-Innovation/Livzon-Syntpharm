"""提示词指纹：给配置页一个「现在跑的是哪版提示词」的可观测标识。

提示词在 P2 之后已集中到 ``prompts.py`` 并支持库内整段覆盖，但仍然是「一段文字」而不是
带版本号的制品。为了不加迁移就能看出「改没改」，这里对生效文本 + 工具清单做 sha256，
取前 8 位作为指纹；任何一处文字改动都会变。

局限：指纹只代表**当前在用版本**，历史任务无法追溯当时用的是哪一版
（要做追溯就必须在任务表加列，属另一次迁移）。

注意：默认常量用函数内延迟导入，避免 ``structure -> prompts_version -> structure`` 的循环导入。
"""

from __future__ import annotations

import hashlib

from app.modules.research.report_gen.prompts import (
    AGENT_JSON_PROTOCOL_PROMPT,
    AGENT_SYSTEM_PROMPT,
    STRUCTURE_SYSTEM_PROMPT,
)
from app.modules.research.report_gen.tools import TOOL_NAMES

_FINGERPRINT_LEN = 8
_SEPARATOR = "\x1f"


def _fingerprint(*parts: str) -> str:
    digest = hashlib.sha256(_SEPARATOR.join(parts).encode("utf-8")).hexdigest()
    return f"prm-{digest[:_FINGERPRINT_LEN]}"


def agent_prompt_version(prompt: str | None = None) -> str:
    """正文生成档：system prompt + JSON 协议模板 + 工具清单（工具名也是提示词的一部分）。

    ``prompt`` 传实际生效的正文（库里覆盖过的），不传则用内置常量：配置页要看到的是
    「现在真正在跑的这段文字」，而不是代码里的默认值。
    """
    return _fingerprint(prompt or AGENT_SYSTEM_PROMPT, AGENT_JSON_PROTOCOL_PROMPT, *TOOL_NAMES)


def structure_prompt_version(prompt: str | None = None) -> str:
    """结构识别档：只认母本槽位判定那段 system prompt（同样跟随库里的覆盖值）。"""
    return _fingerprint(prompt or STRUCTURE_SYSTEM_PROMPT)


__all__ = ["agent_prompt_version", "structure_prompt_version"]
