"""JsonFormatter 对 `extra=` 业务字段的落地（PR #188 审计 Category 6）。

背景：AGENTS.md 要求日志「始终包含上下文」并给了 ``extra={"module": ...}`` 的示例，
但 ``module`` 是 LogRecord 的保留属性，实际输出时会抛 KeyError；而且 JsonFormatter
原来只输出固定字段，调用方传的 extra 全被丢掉，加了也无法按字段过滤/聚合。
"""

import json
import logging
from typing import Any

import pytest

from app.core.logging_config import JsonFormatter

LOGGER_NAME = "app.modules.safety.service.hazard"


def _record(*, args: tuple[Any, ...] = ("x",), **extra: Any) -> logging.LogRecord:
    record = logging.LogRecord(
        name=LOGGER_NAME,
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hi %s",
        args=args,
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_extra_fields_are_flattened_into_json() -> None:
    entry = json.loads(JsonFormatter().format(_record(hazard_no="HZ-1", verify_level=2)))

    assert entry["hazard_no"] == "HZ-1"
    assert entry["verify_level"] == 2


def test_fixed_fields_are_not_overwritten_by_extra() -> None:
    entry = json.loads(JsonFormatter().format(_record(hazard_no="HZ-2")))

    assert entry["msg"] == "hi x"
    assert entry["level"] == "INFO"
    assert entry["logger"] == LOGGER_NAME
    assert entry["module"] == "safety"
    assert entry["rid"] == "-"
    assert "args" not in entry and "pathname" not in entry and "lineno" not in entry


def test_non_serializable_extra_falls_back_to_str() -> None:
    entry = json.loads(JsonFormatter().format(_record(target=object())))

    assert isinstance(entry["target"], str)


def test_reserved_log_record_key_raises_when_logging() -> None:
    """记录 AGENTS.md 禁止用 module 作 extra 键的原因（保留属性冲突）。"""

    class _Collector(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - 不应到达
            raise AssertionError("不应生成记录")

    logger = logging.getLogger("tests.reserved_extra")
    logger.handlers = [_Collector()]
    logger.setLevel(logging.INFO)
    logger.propagate = False

    with pytest.raises(KeyError, match="module"):
        logger.info("boom", extra={"module": "safety"})
