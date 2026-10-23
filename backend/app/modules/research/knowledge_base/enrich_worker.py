"""知识库富化后台 worker：把「摸底 + 事实抽取」从任务链路移到后台持续增量。

为什么独立成 worker：任务链路的富化阶段受任务超时约束，单次只能做很小额度的增量，
大库首次全量（几千切片）放在任务里跑会把生成任务拖到小时级。这里用长运行 worker
在空闲时持续补齐——任务运行时通常已经是「索引与事实基本就绪」，只需读索引。

与 ``doc_gen/worker.py`` 的分工：那个负责生成任务（有租约、有硬超时、可取消）；
这个只做知识库富化（无租约，同环境单实例内串行推进，多实例下可能重复但幂等）。

四条稳定性约束：
1. 单轮只推进一个知识库的一小步（可配置上限），长时间占用模型配额的风险可控；
2. 「有活就立刻干下一轮、没活才休眠」——富化进度不被固定间隔拖慢；
3. 任何异常只记日志并回滚（aborted 事务会毒化 session），绝不让 worker 崩；
4. 开关默认跟随运行时配置 ``DOC_GEN_KB_BACKGROUND_ENRICH_ENABLED``，可随时关闭。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.modules.research.doc_gen.runtime_config import load_runtime_config, resolve_model
from app.shared.lifecycle import register_background_worker

logger = logging.getLogger(__name__)

WORKER_NAME = "research.kb_enrich_worker"
# 单轮镜像切片的硬上限：每轮只推进一小步，多轮累计覆盖全库
INDEX_CHUNKS_PER_ROUND = 500
# 有生成任务在跑时的让路额度：模型配额优先给生成，后台只做小步推进（不完全停）
BUSY_INDEX_LIMIT = 100
BUSY_EXTRACT_LIMIT = 40
# 后台并发上限：空闲时用来快速补齐积压（生成任务在跑时走 busy 分支、只开 1 并发让路，
# 配额优先级不变）。上限受网关承受力约束：实测 8 并发小批事实抽取稳定（8/8 成功）。
MAX_CONCURRENCY = 8
# 空闲休眠的兜底间隔（配置读取失败时用）
_FALLBACK_INTERVAL_SECONDS = 30.0

_stop = asyncio.Event()
# 轮转位置：多个知识库时轮流推进，避免总从第一个开始（大库会长期占住队列头部）
_cursor = 0
# 连续「零推进」轮数（进程内）：模型/格式持续故障时指数退避，避免每轮空转重试同一批
_stalled_rounds = 0
# 退避上限（秒）：持续失败时的休眠封顶
_BACKOFF_MAX_SECONDS = 600.0


async def _active_kbs(session: Any) -> list[Any]:
    """活跃且已关联远端数据集的知识库（数量通常个位数，一次取全）。"""
    from sqlalchemy import select

    from app.modules.research.knowledge_base.models import RdKnowledgeBase

    rows = await session.execute(
        select(RdKnowledgeBase)
        .where(
            RdKnowledgeBase.status == "active",
            RdKnowledgeBase.is_deleted.is_(False),
            RdKnowledgeBase.ragflow_dataset_id.isnot(None),
        )
        .order_by(RdKnowledgeBase.created_at.asc())
        .limit(20)
    )
    return list(rows.scalars().all())


async def _pending_fact_chunks(session: Any, kb_id: Any) -> int:
    """还有多少切片没抽过事实（增量推进的核心计数）。"""
    from sqlalchemy import func, select

    from app.modules.research.knowledge_base.models import RdKbChunk

    count = await session.scalar(
        select(func.count())
        .select_from(RdKbChunk)
        .where(
            RdKbChunk.kb_id == kb_id,
            RdKbChunk.is_deleted.is_(False),
            RdKbChunk.facts_extracted_at.is_(None),
        )
    )
    return int(count or 0)


async def _safe_rollback(session: Any) -> None:
    try:
        await session.rollback()
    except Exception:  # noqa: BLE001 - rollback 也可能失败
        logger.exception("知识库富化回滚失败")


async def _busy_with_generation(session: Any) -> bool:
    """是否有正在执行的生成任务（租约未过期，与领取闸门同一判定口径）。"""
    from datetime import UTC, datetime

    from sqlalchemy import func, select

    from app.modules.research.doc_gen.models import DocGenJob

    count = await session.scalar(
        select(func.count())
        .select_from(DocGenJob)
        .where(
            DocGenJob.is_deleted.is_(False),
            DocGenJob.lease_expires_at.is_not(None),
            DocGenJob.lease_expires_at > datetime.now(UTC),
        )
    )
    return bool(count)


async def _index_round(session: Any, kb: Any, config: Any, *, busy: bool = False) -> Any:
    """一轮摸底：镜像远端切片（限额），返回 IndexStats（失败返回空统计）。

    ``busy``（有生成任务在跑）时降到让路额度：摸底是纯远端读取，但也要给生成任务
    留出网络与写库带宽，任务空闲后再全速推进。
    """
    from app.modules.research.knowledge_base import facts as facts_mod
    from app.modules.research.knowledge_base.ragflow import RagflowClient

    client = RagflowClient()
    if not client.configured:
        return facts_mod.IndexStats()
    try:
        stats = await facts_mod.index_chunks(
            session,
            kb,
            client=client,
            max_chunks=BUSY_INDEX_LIMIT if busy else INDEX_CHUNKS_PER_ROUND,
            concurrency=1 if busy else config.kb_survey_concurrency,
        )
        await session.commit()
        return stats
    except Exception:  # noqa: BLE001 - 单轮失败只降级，下一轮继续
        logger.exception("知识库后台摸底失败", extra={"kb_id": str(kb.id), "module_name": "research"})
        await _safe_rollback(session)
        return facts_mod.IndexStats()


async def _extract_round(session: Any, kb: Any, config: Any, *, busy: bool = False) -> Any:
    """一轮事实抽取（限额），返回 FactStats（失败返回空统计）。

    ``busy``（有生成任务在跑）时降到让路额度、并发 1：模型配额优先给生成任务，
    后台只要小步推进、别把 GPU 占满。
    """
    from app.modules.research.knowledge_base import facts as facts_mod

    limit = config.kb_background_enrich_max_chunks
    if busy:  # 0=不限时也要给让路额度，否则「不限」会变成最大占用
        limit = BUSY_EXTRACT_LIMIT if limit <= 0 else min(BUSY_EXTRACT_LIMIT, limit)
    concurrency = 1 if busy else min(MAX_CONCURRENCY, config.fact_extract_concurrency)
    choice = await resolve_model(config.extract_model_name)
    try:
        stats = await facts_mod.extract_facts(
            session,
            kb,
            model_override=choice.model_override,
            config_name=choice.config_name,
            batch_size=config.fact_extract_batch_size,
            max_chunks=limit,
            concurrency=concurrency,
            timeout_seconds=config.llm_call_timeout_seconds,
            # 后台单轮可能跑十几分钟：按批落库，进度可见且中途重启不丢已完成批次
            commit_per_batch=True,
        )
        await session.commit()
        return stats
    except Exception:  # noqa: BLE001 - 单轮失败只降级，下一轮继续
        logger.exception("知识库后台事实抽取失败", extra={"kb_id": str(kb.id), "module_name": "research"})
        await _safe_rollback(session)
        return facts_mod.FactStats()


async def run_once() -> bool:
    """跑一轮富化：优先补齐有待抽切片的知识库；没有则轮转摸底发现新文档。

    返回是否真的干了事——干了就立刻进入下一轮（不空等间隔），直到没有活可干。
    """
    global _cursor, _stalled_rounds

    config = await load_runtime_config()
    if not config.kb_background_enrich_enabled:
        return False
    from app.core.database import async_session_factory

    async with async_session_factory() as session:
        kbs = await _active_kbs(session)
        if not kbs:
            return False
        # 有生成任务在跑时让路：模型配额优先给生成，后台只做小步推进（不完全停）
        busy = await _busy_with_generation(session)
        start = _cursor % len(kbs)
        order = kbs[start:] + kbs[:start]

        # 一、优先抽事实：已有切片但还没抽的（增量主体）
        for offset, kb in enumerate(order):
            if await _pending_fact_chunks(session, kb.id) <= 0:
                continue
            _cursor = (start + offset + 1) % len(kbs)
            stats = await _extract_round(session, kb, config, busy=busy)
            # _extract_round 的统计经函数内局部 import 返回，收敛成 bool 便于类型检查与判定
            progressed = bool(stats.chunks_done > 0 or stats.facts_added > 0)
            _stalled_rounds = 0 if progressed else _stalled_rounds + 1
            logger.info(
                "知识库后台富化完成一轮",
                extra={
                    "kb_id": str(kb.id),
                    "chunks_done": stats.chunks_done,
                    "facts_added": stats.facts_added,
                    "failures": stats.failures,
                    "stalled_rounds": _stalled_rounds,
                    "yielded": busy,
                    "module_name": "research",
                },
            )
            return progressed

        # 二、没有待抽切片：轮转摸底一个知识库（每轮一个，多库时轮流推进），
        # 发现新文档 / 内容变更的切片后下一轮就会进入事实抽取
        kb = order[0]
        _cursor = (start + 1) % len(kbs)
        stats = await _index_round(session, kb, config, busy=busy)
        if stats.chunks_added or stats.chunks_updated or stats.chunks_removed or stats.pending_facts:
            logger.info(
                "知识库后台摸底发现增量",
                extra={
                    "kb_id": str(kb.id),
                    "added": stats.chunks_added,
                    "updated": stats.chunks_updated,
                    "pending_facts": stats.pending_facts,
                    "module_name": "research",
                },
            )
            return True
        return False


async def _interval_seconds() -> float:
    try:
        config = await load_runtime_config()
        return max(5.0, float(config.kb_background_enrich_interval_seconds))
    except Exception:  # noqa: BLE001 - 配置读取失败退回默认间隔
        logger.exception("知识库富化间隔读取失败，退回默认值")
        return _FALLBACK_INTERVAL_SECONDS


async def _loop() -> None:
    logger.info("知识库富化 worker 已启动")
    while not _stop.is_set():
        try:
            worked = await run_once()
        except Exception:  # noqa: BLE001 - 循环内必须吞异常，否则整个后台任务崩溃
            logger.exception("知识库富化 worker 轮询异常")
            worked = False
        if worked:
            continue
        interval = await _interval_seconds()
        if _stalled_rounds >= 2:
            # 连续零推进：指数退避，模型/格式故障期间不空耗配额与日志
            interval = min(_BACKOFF_MAX_SECONDS, interval * (2 ** (_stalled_rounds - 1)))
            logger.warning(
                "知识库富化连续无进展，退避后重试",
                extra={"interval_seconds": interval, "stalled_rounds": _stalled_rounds, "module_name": "research"},
            )
        try:
            await asyncio.wait_for(_stop.wait(), timeout=interval)
        except TimeoutError:
            pass


async def start() -> None:
    """worker 入口（由应用生命周期启动）。"""
    await _loop()


def stop() -> None:
    """优雅停止：置停止位，当前轮结束后退出。"""
    _stop.set()


register_background_worker(WORKER_NAME, start, stop)

__all__ = ["WORKER_NAME", "run_once", "start", "stop"]
