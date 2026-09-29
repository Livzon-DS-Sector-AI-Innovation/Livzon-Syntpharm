"""文档生成后台 worker。

生成一个任务需要几分钟，而 SchedulerEngine 的主循环是串行的（放在引擎里会卡住
其它模块的定时任务），因此按 AGENTS.md 用 register_background_worker 注册为
长运行进程：自带轮询循环、一次只处理一个任务、租约超时后可被重新领取。

四条「卡住也必须能停下来」的保障：

1. 任务跑在**可单独取消的子任务**里，取消它不会牵连 worker 主循环；
2. 整任务硬超时 ``DOC_GEN_JOB_TIMEOUT_SECONDS``：任何一环卡死（模型不返回、对象存储
   挂住、解析库陷入 C 层）都会在超时后被切断并落终态；
3. 启动时先做一次恢复：把上一次进程被杀/热重载时留在「解析中/提取中」的任务判为失败，
   不再让前端对着一个永远不会动的进度条空等；
4. 关停时 ``abort_all()``：让解析线程与模型调用尽快放手，避免留下半截状态。
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from app.modules.research.doc_gen import cancellation, pipeline
from app.modules.research.doc_gen import repository as repo
from app.modules.research.doc_gen.runtime_config import RuntimeConfig, load_runtime_config
from app.shared.lifecycle import register_background_worker

logger = logging.getLogger(__name__)

WORKER_NAME = "research.doc_gen_worker"
_stop = asyncio.Event()


async def run_once() -> str | None:
    """领取并执行一个任务；没有可做的任务时返回 None。"""
    config = await load_runtime_config()
    if not config.enabled:
        return None
    from app.core.database import async_session_factory

    async with async_session_factory() as session:
        job = await repo.claim_next_job(session, config.lease_seconds, config.max_concurrency)
        await session.commit()
        if job is None:
            return None
        claimed, template = job.id, job.template_code  # 出 session 后不可再访问 ORM 属性
    logger.info("开始文档生成任务", extra={"job_id": str(claimed), "template": template})
    return await _execute_guarded(claimed, config)


async def _execute_guarded(job_id: uuid.UUID, config: RuntimeConfig) -> str:
    """在可取消的子任务里执行任务，并施加整体硬超时。

    这里的 ``create_task`` 属于 AGENTS.md 允许的「后台工作进程内部基础设施任务」：
    业务步骤仍由 pipeline 串行执行，只是给执行体套一层能被强制停下来的外壳。
    """
    handle = cancellation.register(job_id)
    task = asyncio.create_task(pipeline.execute_job(job_id, handle))
    cancellation.attach_task(handle, task)
    try:
        return await asyncio.wait_for(task, timeout=config.job_timeout_seconds)
    except TimeoutError:
        logger.error("文档生成任务整体超时", extra={"job_id": str(job_id), "timeout": config.job_timeout_seconds})
        await _finalize(job_id, "failed", "timeout", f"任务超过 {config.job_timeout_seconds} 秒未完成，已强制终止")
        return "failed"
    except asyncio.CancelledError:
        if not handle.event.is_set():
            # 取消来自主循环关停，不是任务终止请求：原样抛回，不吞掉关停信号
            raise
        logger.warning("文档生成任务被强制终止", extra={"job_id": str(job_id), "reason": handle.reason})
        await _finalize(job_id, "cancelled", "cancelled", f"任务已被强制终止（{handle.reason}）")
        return "cancelled"
    finally:
        cancellation.unregister(job_id)


async def _finalize(job_id: uuid.UUID, target: str, code: str, message: str) -> None:
    """用独立 session 落终态——被打断的执行 session 已经不可信。"""
    from app.core.database import async_session_factory

    try:
        async with async_session_factory() as session:
            await repo.finalize_job(session, job_id, target, code, message)
    except Exception:  # noqa: BLE001 - 收尾失败只记日志，不能让 worker 崩
        logger.exception("文档生成任务终止后收尾失败", extra={"job_id": str(job_id)})


async def _recover_on_startup() -> None:
    """启动恢复：把上一进程遗留的执行中任务判为失败。"""
    from app.core.database import async_session_factory

    try:
        async with async_session_factory() as session:
            count = await repo.recover_stale_jobs(session)
        if count:
            logger.warning("文档生成 worker 启动恢复完成", extra={"recovered": count})
    except Exception:  # noqa: BLE001 - 恢复失败不能阻塞 worker 启动
        logger.exception("文档生成 worker 启动恢复失败")


async def _loop() -> None:
    """轮询循环（单实例内串行，模型部署吞吐未知，先不做并发）。"""
    await _recover_on_startup()
    logger.info("文档生成 worker 已启动")
    while not _stop.is_set():
        try:
            handled = await run_once()
        except Exception:  # noqa: BLE001 - 循环内必须吞异常，否则整个后台任务崩溃
            handled = None
            logger.exception("文档生成 worker 轮询异常")
        if handled is None:
            try:
                await asyncio.wait_for(_stop.wait(), timeout=5)
            except TimeoutError:
                pass
            continue


async def stop() -> None:
    """优雅停止：先终止在执行的任务，再退出轮询。"""
    cancellation.abort_all("shutdown")
    _stop.set()


async def start() -> None:
    """worker 入口（由应用生命周期启动）。"""
    await _loop()


register_background_worker(WORKER_NAME, start, stop)
