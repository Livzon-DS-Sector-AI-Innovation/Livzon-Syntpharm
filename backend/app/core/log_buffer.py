"""运行日志内存环形缓冲（供「系统运维 → 日志管理」查看）。

不落盘：只保留最近 N 条（默认 2000），重启清空——避免磁盘压力
（本机磁盘长期紧张）。若后续需要持久化/下载，再接入
`app.core.logging_config` 的文件输出并改为读文件。
"""

import itertools
import logging
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.logging_config import request_id_var

_MAX_RECORDS = 2000
_TZ = ZoneInfo("Asia/Shanghai")

_lock = threading.Lock()
_buffer: deque["LogRecordItem"] = deque(maxlen=_MAX_RECORDS)
_seq_counter = itertools.count(1)


@dataclass(frozen=True)
class LogRecordItem:
    seq: int
    timestamp: str
    level: str
    logger: str
    message: str
    request_id: str


class LogBufferHandler(logging.Handler):
    """把日志记录写入内存环形缓冲（绝不抛异常，避免影响业务）。"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            item = LogRecordItem(
                seq=next(_seq_counter),
                timestamp=datetime.fromtimestamp(record.created, tz=_TZ).strftime("%Y-%m-%d %H:%M:%S"),
                level=record.levelname,
                logger=record.name,
                message=record.getMessage(),
                request_id=str(getattr(record, "request_id", "-")),
            )
            with _lock:
                _buffer.append(item)
        except Exception:  # noqa: BLE001 - 日志处理器不允许向上抛
            self.handleError(record)


class _RequestIdFilter(logging.Filter):
    """把 ContextVar 里的 request_id 注入日志记录（与 audit 中间件联动）。"""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_var.get()
        return True


def install_log_buffer(level: int = logging.INFO) -> None:
    """挂载内存缓冲 handler 到 root logger（幂等）。"""
    root = logging.getLogger()
    for handler in root.handlers:
        if isinstance(handler, LogBufferHandler):
            return
    handler = LogBufferHandler()
    handler.setLevel(level)
    handler.addFilter(_RequestIdFilter())
    root.addHandler(handler)


def query_logs(level: str = "", keyword: str = "", limit: int = 500) -> list[LogRecordItem]:
    """按级别 / 关键词过滤，返回最近 limit 条（时间倒序，最新在前）。"""
    with _lock:
        items = list(_buffer)

    if level:
        wanted = {value.strip().upper() for value in level.split(",") if value.strip()}
        items = [item for item in items if item.level in wanted]
    if keyword:
        kw = keyword.lower()
        items = [item for item in items if kw in item.message.lower() or kw in item.logger.lower()]

    return list(reversed(items[-limit:]))


def clear_logs() -> int:
    with _lock:
        count = len(_buffer)
        _buffer.clear()
    return count


def buffer_size() -> int:
    with _lock:
        return len(_buffer)
