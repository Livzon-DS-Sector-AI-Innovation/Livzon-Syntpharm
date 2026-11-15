"""报告生成的进程内 LRU：解析结果与对象存储字节共用同一套有界语义。

键一律取自**不可变的存储键**（``doc-gen/{uuid4}/{name}``，模板换版会写新键），
内容只由键决定，所以多 worker 各持一份没有一致性问题；进程重启即空也不影响正确性。

为什么字节也要缓存：详情页清单接口每次都要取母本（以及成品）算位置，之前只缓存解析
结果，字节仍每次回源对象存储——生成中每 5 秒一次全量下载，换来的是完全相同的字节。
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from collections.abc import Callable

logger = logging.getLogger(__name__)

# 解析结果（段落下标、表格起点）都是小对象，容量按「同时打开几个任务」定
DEFAULT_CACHE_SIZE = 16
# 字节缓存要按内存算：单份上限 16MB、最多 6 份，最坏约 96MB/进程。
# 超过上限的文件（超大母本）直接回源，用下载时间换内存安全。
MAX_CACHED_BYTES = 16 * 1024 * 1024
BYTES_CACHE_SIZE = 6

_BYTES_CACHE: OrderedDict[str, bytes] = OrderedDict()


def lru_get[T](cache: OrderedDict[str, T], key: str) -> T | None:
    """取缓存并把命中项移到队尾（最近使用）。"""
    value = cache.get(key)
    if value is None:
        return None
    cache.move_to_end(key)
    return value


def lru_put[T](cache: OrderedDict[str, T], key: str, value: T, *, max_size: int = DEFAULT_CACHE_SIZE) -> None:
    """写入缓存并按容量淘汰最久未用的项。"""
    cache[key] = value
    cache.move_to_end(key)
    while len(cache) > max_size:
        cache.popitem(last=False)


def _put_bytes(key: str, data: bytes) -> None:
    """超大文件不缓存：缓存命中省下的下载时间不值得用内存换。"""
    if len(data) > MAX_CACHED_BYTES:
        logger.debug(
            "report-gen cache: 文件超过缓存额度，跳过缓存",
            extra={"cache_key": key, "size": len(data)},
        )
        return
    lru_put(_BYTES_CACHE, key, data, max_size=BYTES_CACHE_SIZE)


def load_bytes_cached(key: str, loader: Callable[[], bytes | None]) -> bytes | None:
    """按存储键读字节：命中则不回源（MinIO / 本地文件）。

    ``loader`` 返回 ``None``（文件不存在）时不缓存，避免把「暂时读不到」固化下来。
    """
    cached = lru_get(_BYTES_CACHE, key)
    if cached is not None:
        return cached
    data = loader()
    if data:
        _put_bytes(key, data)
    return data


def clear_bytes() -> None:
    _BYTES_CACHE.clear()


__all__ = [
    "BYTES_CACHE_SIZE",
    "DEFAULT_CACHE_SIZE",
    "MAX_CACHED_BYTES",
    "clear_bytes",
    "load_bytes_cached",
    "lru_get",
    "lru_put",
]
