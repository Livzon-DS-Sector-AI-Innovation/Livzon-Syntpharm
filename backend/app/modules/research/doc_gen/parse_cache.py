"""解析结果缓存：同一份文件（内容哈希相同）跨任务复用解析产物。

为什么缓存解析：解析（尤其扫描件 OCR / 视觉兜底）是最贵的确定性步骤，而结果只由
「文件内容 + 解析器版本」决定——同一份资料被多个任务反复使用时没有理由重复解析。

稳定性契约（与全链路一致）：
- 表缺失 / DB 异常一律降级为「没有缓存」，且本进程内不再重试（部署未跑迁移时
  不会每个文件都刷错误日志）；
- 读写都用**独立 session**：解析阶段是多协程并发的，绝不能在共享的执行 session 上
  穿插操作（这是本模块已踩过的坑）；
- 缓存是旁路数据：命中计数失败不影响命中本身，写入失败不影响任务。
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Sequence
from typing import Any

from app.modules.research.doc_gen.models import DocGenParseCache
from app.modules.research.doc_gen.parsing import TextBlock

logger = logging.getLogger(__name__)

# 解析器版本：解析行为（库 / 兜底链 / 输出形态）发生变更时递增，旧缓存随之作废
PARSER_VERSION = "1"

# 进程内熔断：表不存在或 DB 连续失败后不再反复尝试
_unavailable = False


def content_hash(data: bytes) -> str:
    """文件内容 SHA-256（缓存键的一部分）。"""
    return hashlib.sha256(data).hexdigest()


def _mark_unavailable(exc: BaseException) -> None:
    global _unavailable
    _unavailable = True
    logger.warning("解析缓存不可用，本进程内不再尝试", extra={"error": type(exc).__name__})


def _block_payload(block: TextBlock) -> dict[str, Any]:
    return {"page": block.page, "index": block.index, "text": block.text, "kind": block.kind}


def _block_of(item: Any, file_id: str) -> TextBlock:
    return TextBlock(
        file_id=file_id,
        page=int(item.get("page") or 1),
        index=int(item.get("index") or 0),
        text=str(item.get("text") or ""),
        kind=str(item.get("kind") or "paragraph"),
    )


async def load_blocks(file_id: str, data: bytes) -> tuple[list[TextBlock], list[str], int] | None:
    """按文件内容取缓存；未命中或缓存不可用返回 None。

    返回 ``(blocks, warnings, page_count)``，blocks 的 ``file_id`` 用调用方的稳定标识回填。
    """
    if _unavailable:
        return None
    digest = content_hash(data)
    try:
        from sqlalchemy import select, update

        from app.core.database import async_session_factory

        async with async_session_factory() as session:
            row = (
                await session.execute(
                    select(DocGenParseCache).where(
                        DocGenParseCache.content_hash == digest,
                        DocGenParseCache.parser_version == PARSER_VERSION,
                        DocGenParseCache.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()
            if row is None:
                return None
            blocks = [_block_of(item, file_id) for item in (row.blocks or []) if isinstance(item, dict)]
            warnings = [str(item) for item in (row.warnings or [])]
            page_count = int(row.page_count or 0)
            try:  # 命中计数是观测信息，失败不影响命中结果
                await session.execute(
                    update(DocGenParseCache).where(DocGenParseCache.id == row.id).values(hits=row.hits + 1)
                )
                await session.commit()
            except Exception:  # noqa: BLE001
                await session.rollback()
    except Exception as exc:  # noqa: BLE001 - 缓存不可用只降级
        _mark_unavailable(exc)
        return None
    if not blocks:
        return None
    return blocks, warnings, page_count


async def save_blocks(
    data: bytes,
    blocks: Sequence[TextBlock],
    warnings: Sequence[str],
    page_count: int,
    file_name: str,
) -> None:
    """写入解析产物（同键已存在则跳过；失败只记日志）。"""
    if _unavailable or not blocks:
        return
    digest = content_hash(data)
    try:
        from sqlalchemy import select

        from app.core.database import async_session_factory

        async with async_session_factory() as session:
            exists = await session.scalar(
                select(DocGenParseCache.id).where(
                    DocGenParseCache.content_hash == digest,
                    DocGenParseCache.parser_version == PARSER_VERSION,
                    DocGenParseCache.is_deleted.is_(False),
                )
            )
            if exists is not None:
                return
            session.add(
                DocGenParseCache(
                    content_hash=digest,
                    parser_version=PARSER_VERSION,
                    file_name=file_name[:500],
                    page_count=max(0, int(page_count)),
                    char_count=sum(len(block.text) for block in blocks),
                    blocks=[_block_payload(block) for block in blocks],
                    warnings=[str(item) for item in warnings],
                    hits=0,
                )
            )
            await session.commit()
    except Exception as exc:  # noqa: BLE001 - 缓存写入失败不影响任务
        _mark_unavailable(exc)


def reset_state_for_tests() -> None:
    """测试专用：清掉进程内熔断（表缺失降级验证后会恢复）。"""
    global _unavailable
    _unavailable = False


__all__ = ["PARSER_VERSION", "content_hash", "load_blocks", "reset_state_for_tests", "save_blocks"]
