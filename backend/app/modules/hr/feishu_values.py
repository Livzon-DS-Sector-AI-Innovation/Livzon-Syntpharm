"""Shared readers for raw Feishu payload values.

Feishu returns i18n objects for text fields and strings for numbers. The org
and personnel mirrors both need the same tolerant coercion, so it lives here
instead of being copied into each domain module.
"""

from __future__ import annotations

from typing import Any


def text_value(value: Any) -> str:
    """Read an i18n text object or a plain string as display text."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        default = value.get("default_value")
        if isinstance(default, str):
            return default.strip()
        i18n = value.get("i18n_value")
        if isinstance(i18n, dict):
            for key in ("zh_cn", "zh-CN", "en_us"):
                candidate = i18n.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
        for key in ("name", "text", "value"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return ""


def int_value(value: Any) -> int:
    """Read an int-like value, defaulting to 0."""
    if value is None or value == "":
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def optional_int_value(value: Any) -> int | None:
    """Read an int-like value, keeping ``None`` for empty/invalid input."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
