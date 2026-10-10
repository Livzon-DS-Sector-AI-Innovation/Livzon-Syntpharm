"""槽位取值状态与占位文本约定。

这些常量和 Word 无关，纯文本，因此不会引入样式改动；同时它们也是「生成说明」与
前端统计的共同语言。
"""

from __future__ import annotations

import re

STATUS_OK = "ok"
STATUS_DRAFT = "ai_draft"
STATUS_PENDING = "pending"
STATUS_CONFLICT = "conflict"
STATUS_MANUAL = "manual_only"
STATUS_ANCHOR_UNRESOLVED = "anchor_unresolved"
STATUS_OVERFLOW = "layout_overflow"
STATUS_FAILED = "ai_failed"
# 值已按 AI 结果写入，但依据只经模糊匹配核对（存在排版/OCR 差异），需人工确认
STATUS_NEEDS_VERIFY = "needs_verify"

PENDING_PREFIX = "[待补充："
DRAFT_PREFIX = "【AI草稿，需确认】"
CONFLICT_MARK = "[待补充：材料冲突，见生成说明]"
IMAGE_PLACEHOLDER = "[图片占位：{label}，请人工插入]"

_PENDING_RE = re.compile(r"^\[待补充：(?P<reason>.*)\]$")


def pending(reason: str = "材料未提供") -> str:
    """生成待补充占位文本。"""
    return f"{PENDING_PREFIX}{reason}]"


def is_pending(text: str) -> bool:
    """文本是否为待补充占位。"""
    return text.startswith(PENDING_PREFIX)


def pending_reason(text: str) -> str:
    """从占位文本中取原因，非占位返回空串。"""
    match = _PENDING_RE.match(text.strip())
    return match.group("reason") if match else ""


def with_draft_prefix(text: str) -> str:
    """AI 草稿前缀（幂等）。"""
    if not text or text.startswith(DRAFT_PREFIX) or is_pending(text):
        return text
    return f"{DRAFT_PREFIX}{text}"


def strip_draft_prefix(text: str) -> str:
    """去掉 AI 草稿前缀。"""
    return text[len(DRAFT_PREFIX) :] if text.startswith(DRAFT_PREFIX) else text


__all__ = [
    "CONFLICT_MARK",
    "DRAFT_PREFIX",
    "IMAGE_PLACEHOLDER",
    "PENDING_PREFIX",
    "STATUS_ANCHOR_UNRESOLVED",
    "STATUS_CONFLICT",
    "STATUS_DRAFT",
    "STATUS_FAILED",
    "STATUS_MANUAL",
    "STATUS_OK",
    "STATUS_OVERFLOW",
    "STATUS_PENDING",
    "STATUS_NEEDS_VERIFY",
    "is_pending",
    "pending",
    "pending_reason",
    "strip_draft_prefix",
    "with_draft_prefix",
]
