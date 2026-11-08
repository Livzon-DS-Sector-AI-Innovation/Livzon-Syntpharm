"""提示词指纹：给配置页一个「现在跑的是哪版提示词」的可观测标识。

提示词目前是模块常量（``agent._SYSTEM_PROMPT`` / ``structure._SYSTEM_PROMPT``），
既没有版本号也没有落库字段。为了在不加迁移的前提下让运维看出「改没改」，
这里对提示词正文与工具清单做 sha256，取前 8 位作为指纹；任何一处文字改动都会变。

局限：指纹只代表**当前在用版本**，历史任务无法追溯当时用的是哪一版
（要做追溯就必须在任务表加列，属另一次迁移）。
"""

from __future__ import annotations

import hashlib

from app.modules.research.report_gen import agent, structure
from app.modules.research.report_gen.tools import TOOL_NAMES

_FINGERPRINT_LEN = 8
_SEPARATOR = "\x1f"


def _fingerprint(*parts: str) -> str:
    digest = hashlib.sha256(_SEPARATOR.join(parts).encode("utf-8")).hexdigest()
    return f"prm-{digest[:_FINGERPRINT_LEN]}"


def agent_prompt_version() -> str:
    """正文生成档：system prompt + JSON 协议模板 + 工具清单（工具名也是提示词的一部分）。"""
    return _fingerprint(agent._SYSTEM_PROMPT, agent._JSON_PROTOCOL_PROMPT, *TOOL_NAMES)


def structure_prompt_version() -> str:
    """结构识别档：只认母本槽位判定那段 system prompt。"""
    return _fingerprint(structure._SYSTEM_PROMPT)


__all__ = ["agent_prompt_version", "structure_prompt_version"]
