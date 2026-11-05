"""提取结果缓存（DB 版）：同一「模板槽位 + 候选内容 + 提示版本」的抽取结果跨任务复用。

为什么持久化：进程内缓存（``SlotExtractor._cache``）随任务结束即失效，重跑或换任务时
同一槽位在同样资料上还要重新调模型。缓存键里带提示版本与模型档位：
提示词改动（``PROMPT_VERSION`` 递增）或换模型后旧结果自然失效，不会串用。

稳定性契约：表缺失 / DB 异常降级为「没有缓存」（本进程熔断，不再反复尝试）；
读写都走**独立 session**（提取阶段是多批并发的，不能碰任务执行 session）。
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from app.modules.research.doc_gen import status
from app.modules.research.doc_gen.extraction import EvidenceModel, SlotResult
from app.modules.research.doc_gen.models import DocGenExtractCache

logger = logging.getLogger(__name__)

# 提示版本：提取 prompt 的语义发生变更时递增（旧缓存随之作废）
PROMPT_VERSION = "1"

# 进程内熔断：表不存在或 DB 连续失败后不再反复尝试
_unavailable = False

# 只缓存「明确结果」：与内存缓存口径一致（pending/failed 不缓存，否则会把失败固化）
_CACHEABLE_STATES = frozenset({status.STATUS_OK, status.STATUS_NEEDS_VERIFY})


def _mark_unavailable(exc: BaseException) -> None:
    global _unavailable
    _unavailable = True
    logger.warning("提取缓存不可用，本进程内不再尝试", extra={"error": type(exc).__name__})


def result_to_payload(result: SlotResult) -> dict[str, Any]:
    """SlotResult → 可 JSON 落库的形态。"""
    return {
        "key": result.key,
        "text": result.text,
        "pre_compose_text": result.pre_compose_text,
        "rows": [dict(row) for row in result.rows],
        "state": result.state,
        "reason": result.reason,
        "evidence": [item.model_dump() for item in result.evidence],
        "candidates": list(result.candidates),
        "confidence": result.confidence,
        "gap_reason": result.gap_reason,
    }


def result_from_payload(payload: Any) -> SlotResult | None:
    """缓存体 → SlotResult；结构不合法返回 None（按未命中处理）。"""
    if not isinstance(payload, dict) or not payload.get("key"):
        return None
    try:
        return SlotResult(
            key=str(payload["key"]),
            text=str(payload.get("text") or ""),
            pre_compose_text=str(payload.get("pre_compose_text") or ""),
            rows=[dict(item) for item in (payload.get("rows") or []) if isinstance(item, dict)],
            state=str(payload.get("state") or status.STATUS_PENDING),
            reason=str(payload.get("reason") or ""),
            evidence=[EvidenceModel.model_validate(item) for item in (payload.get("evidence") or [])],
            candidates=[str(item) for item in (payload.get("candidates") or [])],
            confidence=payload.get("confidence"),
            gap_reason=str(payload.get("gap_reason") or ""),
        )
    except Exception:  # noqa: BLE001 - 缓存可能被人为改坏，降级为未命中
        logger.exception("提取缓存解析失败，按未命中处理")
        return None


class DbExtractCache:
    """基于 ``doc_gen_extract_cache`` 的提取结果缓存后端（注入给 ``SlotExtractor``）。

    与 ``SlotExtractor`` 的耦合刻意保持鸭子类型（``key()`` / ``get()`` / ``put()``），
    避免缓存模块与提取模块相互 import。
    """

    def __init__(self, *, template_code: str, model_note: str = "") -> None:
        self._template_code = template_code or ""
        self._model_note = model_note or ""

    def key(self, slot_key: str, content_hash: str) -> str:
        """缓存键：模板 / 槽位 / 候选内容 / 提示版本 / 模型档位 任一变化都会换键。"""
        raw = "|".join([self._template_code, slot_key, content_hash, PROMPT_VERSION, self._model_note])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def get(self, cache_key: str) -> SlotResult | None:
        if _unavailable:
            return None
        try:
            from sqlalchemy import select, update

            from app.core.database import async_session_factory

            async with async_session_factory() as session:
                row = (
                    await session.execute(
                        select(DocGenExtractCache).where(
                            DocGenExtractCache.cache_key == cache_key,
                            DocGenExtractCache.is_deleted.is_(False),
                        )
                    )
                ).scalar_one_or_none()
                if row is None:
                    return None
                result = result_from_payload(row.payload)
                try:  # 命中计数是观测信息，失败不影响命中结果
                    await session.execute(
                        update(DocGenExtractCache).where(DocGenExtractCache.id == row.id).values(hits=row.hits + 1)
                    )
                    await session.commit()
                except Exception:  # noqa: BLE001
                    await session.rollback()
                return result
        except Exception as exc:  # noqa: BLE001 - 缓存不可用只降级
            _mark_unavailable(exc)
            return None

    async def put(self, cache_key: str, result: SlotResult) -> None:
        if _unavailable or result.state not in _CACHEABLE_STATES:
            return
        try:
            from sqlalchemy import select

            from app.core.database import async_session_factory

            async with async_session_factory() as session:
                exists = await session.scalar(
                    select(DocGenExtractCache.id).where(
                        DocGenExtractCache.cache_key == cache_key,
                        DocGenExtractCache.is_deleted.is_(False),
                    )
                )
                if exists is not None:
                    return
                session.add(
                    DocGenExtractCache(
                        cache_key=cache_key,
                        slot_key=result.key[:150],
                        template_code=self._template_code[:100],
                        state=result.state[:24],
                        payload=result_to_payload(result),
                        hits=0,
                    )
                )
                await session.commit()
        except Exception as exc:  # noqa: BLE001 - 缓存写入失败不影响任务
            _mark_unavailable(exc)


def reset_state_for_tests() -> None:
    """测试专用：清掉进程内熔断。"""
    global _unavailable
    _unavailable = False


__all__ = [
    "PROMPT_VERSION",
    "DbExtractCache",
    "reset_state_for_tests",
    "result_from_payload",
    "result_to_payload",
]
