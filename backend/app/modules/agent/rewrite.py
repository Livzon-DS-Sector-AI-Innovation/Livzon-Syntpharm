"""讲稿改写编排：四种语义共用一个入口。

对外只有 `run()` / `submit()`：

- `fill_blank`      只补空页（上传后的默认行为）
- `rewrite_all`     覆盖全部可生成页
- `rewrite_selected`覆盖指定页
- `rewrite_one`     单页改写（同步调用，供编辑区按钮用）

隐藏的实现：

1. 三层规则拼装（单次指令 > 项目规范 > 全局规范），复用 `script_ai` 的 prompt 构造；
2. 覆盖前把目标页讲稿写进 `revision.before`，再更新讲稿 —— 顺序不能反，否则回滚没有依据；
3. 分批计时重试，单批失败只记错误，最终状态可能是 partial；
4. 讲稿变更后清空音频指纹，强制该页重新 TTS。

模型走 `ai_config.resolve()` 的四级回落，调用方不需要知道「现在用的是谁的 Key」。
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, cast

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.jobs import submit_job_safe
from app.core.llm import LLMError, llm_client
from app.modules.agent.ai_config import ResolvedModel, compose_guide_block, resolve, resolve_guide
from app.modules.agent.config import MODULE_CODE, PptVideoSettings, load_settings
from app.modules.agent.models import (
    REVISION_STATUS_FAILED,
    REVISION_STATUS_RUNNING,
    REVISION_STATUS_SUCCEEDED,
    REWRITE_MODE_FILL_BLANK,
    REWRITE_MODE_REWRITE_ALL,
    REWRITE_MODE_REWRITE_ONE,
    REWRITE_MODE_REWRITE_SELECTED,
    REWRITE_MODE_SOURCE_REPLACE,
    SCRIPT_AI_STATUS_DONE,
    SCRIPT_AI_STATUS_FAILED,
    SCRIPT_AI_STATUS_PARTIAL,
    SCRIPT_AI_STATUS_RUNNING,
    SCRIPT_SOURCE_AI,
    PptVideoProject,
    PptVideoScriptRevision,
    PptVideoSlide,
)
from app.modules.agent.script_ai import (
    MAX_ERROR_CHARS,
    _join_errors,
    _set_status,
    batch_progress,
    build_messages,
    extract_batch_scripts,
    is_blank_script,
    is_generatable,
)

logger = logging.getLogger(__name__)

JOB_NAME = f"{MODULE_CODE}.ppt-video.script-rewrite"

#: 改写任务的统一说明，避免模型把「改写」理解成「重新编一段」
_TASK_HINT = "请重写下列页码的讲稿：保留页面信息与数字，按规范调整文风与篇幅，不要新增页面之外的结论。"


@dataclass
class RewriteRequest:
    """一次改写请求。scope 为空表示按 mode 的默认范围。"""

    mode: str
    slide_uids: list[str] = field(default_factory=list)
    instruction: str | None = None
    requested_by_name: str | None = None


@dataclass
class RewriteResult:
    revision_id: uuid.UUID | None = None
    status: str = SCRIPT_AI_STATUS_DONE
    total: int = 0
    done: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "revision_id": str(self.revision_id) if self.revision_id else None,
            "status": self.status,
            "total": self.total,
            "done": self.done,
            "skipped": self.skipped,
            "failed": self.failed,
            "errors": self.errors[:3],
        }


def _select_targets(slides: list[PptVideoSlide], request: RewriteRequest) -> tuple[list[PptVideoSlide], int]:
    """按 mode 挑目标页，返回 (目标页, 跳过数)。"""
    wanted = {uid for uid in request.slide_uids if uid}
    targets: list[PptVideoSlide] = []
    skipped = 0

    for slide in slides:
        if request.mode == REWRITE_MODE_REWRITE_ALL:
            selected = True
        elif request.mode in (
            REWRITE_MODE_REWRITE_SELECTED,
            REWRITE_MODE_REWRITE_ONE,
            REWRITE_MODE_SOURCE_REPLACE,
        ):
            selected = str(slide.slide_uid) in wanted
        else:  # fill_blank
            selected = is_blank_script(slide.script_text)

        if not selected:
            continue
        if not is_generatable(slide.page_text, slide.page_notes):
            # 纯图片页没有可讲的内容，保留原讲稿，不计入失败
            skipped += 1
            continue
        targets.append(slide)

    return targets, skipped


async def _create_revision(
    session: AsyncSession,
    project: PptVideoProject,
    request: RewriteRequest,
    model: ResolvedModel,
    targets: list[PptVideoSlide],
    source_version: int | None = None,
) -> PptVideoScriptRevision:
    revision = PptVideoScriptRevision(
        project_id=project.id,
        mode=request.mode,
        instruction=(request.instruction or None),
        model_name=model.model_name,
        provider=model.source,
        scope=[str(slide.slide_uid) for slide in targets],
        before={str(slide.slide_uid): slide.script_text or "" for slide in targets},
        status=REVISION_STATUS_RUNNING,
        progress=0,
        source_version=source_version,
        applied=True,
        requested_by_name=request.requested_by_name,
    )
    session.add(revision)
    await session.flush()
    return revision


async def _update_revision(
    session: AsyncSession,
    revision_id: uuid.UUID,
    *,
    status: str,
    progress: int,
    after: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    values: dict[str, Any] = {
        "status": status,
        "progress": progress,
        "error_message": error[:MAX_ERROR_CHARS] if error else None,
        "updated_at": func.now(),
    }
    if after is not None:
        values["after"] = after
    await session.execute(
        update(PptVideoScriptRevision).where(PptVideoScriptRevision.id == revision_id).values(**values)
    )
    await session.commit()


async def _write_script(
    session: AsyncSession,
    project_id: uuid.UUID,
    slide_uid: str,
    script: str,
    *,
    only_if_blank: bool,
) -> bool:
    """写入讲稿；讲稿变了就清空音频指纹，强制重新 TTS。"""
    conditions = [
        PptVideoSlide.project_id == project_id,
        PptVideoSlide.slide_uid == uuid.UUID(str(slide_uid)),
        PptVideoSlide.is_deleted.is_(False),
    ]
    if only_if_blank:
        conditions.append(func.coalesce(func.btrim(PptVideoSlide.script_text, " \t\r\n\u3000"), "") == "")

    stmt = (
        update(PptVideoSlide)
        .where(*conditions)
        .values(
            script_text=script,
            script_source=SCRIPT_SOURCE_AI,
            script_stale=False,
            audio_object_key=None,
            audio_sha256=None,
            duration_ms=0,
            updated_at=func.now(),
        )
        .returning(PptVideoSlide.slide_uid)
    )
    return await session.scalar(stmt) is not None


async def run(
    session: AsyncSession,
    project: PptVideoProject,
    request: RewriteRequest,
    settings: PptVideoSettings,
    user_id: uuid.UUID | None = None,
    revision_id: uuid.UUID | None = None,
) -> RewriteResult:
    """执行一次改写。调用方负责提交事务；本函数按批 commit 以便前端看到进度。"""
    slides = list(
        (
            await session.scalars(
                select(PptVideoSlide)
                .where(PptVideoSlide.project_id == project.id, PptVideoSlide.is_deleted.is_(False))
                .order_by(PptVideoSlide.slide_no)
            )
        ).all()
    )
    targets, skipped = _select_targets(slides, request)
    result = RewriteResult(total=len(targets), skipped=skipped)

    model = await resolve(session, project, user_id)
    guide = await resolve_guide(session, project)
    guide_block = compose_guide_block(guide, request.instruction, settings.script_guide_max_chars)

    revision = await session.get(PptVideoScriptRevision, revision_id) if revision_id else None
    if revision is None:
        revision = await _create_revision(session, project, request, model, targets)
    else:
        # 换源场景由 source_replace 预先建好修订记录（before 里还包含被删除页），这里只补模型信息
        revision.model_name = model.model_name
        revision.provider = model.source
        await session.flush()
    result.revision_id = revision.id
    await session.commit()

    if not targets:
        await _update_revision(session, revision.id, status=REVISION_STATUS_SUCCEEDED, progress=100, after={})
        await _set_status(session, project.id, SCRIPT_AI_STATUS_DONE, 100, None)
        return result

    await _set_status(session, project.id, SCRIPT_AI_STATUS_RUNNING, 0, None)

    language = project.default_language if project.default_language in ("zh", "en") else "zh"
    batch_size = max(1, settings.script_ai_batch_size)
    only_if_blank = request.mode == REWRITE_MODE_FILL_BLANK
    task_hint = "" if only_if_blank else _TASK_HINT
    after: dict[str, str] = {}

    for start in range(0, len(targets), batch_size):
        batch = targets[start : start + batch_size]
        items = [(slide.slide_no, slide.page_text, slide.page_notes) for slide in batch]
        allowed = {slide.slide_no for slide in batch}
        messages = build_messages(
            language,
            project.name,
            items,
            max_page_text_chars=settings.script_ai_max_page_text_chars,
            guide_block=guide_block,
            current_scripts={slide.slide_no: slide.script_text or "" for slide in batch},
            task_hint=task_hint,
        )
        batch_nos = sorted(allowed)
        logger.info("讲稿改写批次开始: project=%s slides=%s mode=%s", project.id, batch_nos, request.mode)
        try:
            payload = await asyncio.wait_for(
                llm_client.chat_json(
                    messages,
                    expected_keys=["slides"],
                    config_id=model.config_id,
                    owner_user_id=str(user_id) if user_id else None,
                ),
                timeout=settings.script_ai_timeout_seconds,
            )
        except (LLMError, TimeoutError) as exc:
            reason = str(exc) or f"超过 {settings.script_ai_timeout_seconds} 秒未返回"
            result.failed += len(batch)
            result.errors.append(f"第 {'、'.join(str(no) for no in batch_nos)} 页改写失败：{reason}")
            logger.warning("讲稿改写批次失败: project=%s err=%s", project.id, reason[:MAX_ERROR_CHARS])
            continue
        except Exception as exc:  # noqa: BLE001 — 单批未知异常不能打断整批任务
            logger.exception("讲稿改写批次异常: project=%s", project.id)
            result.failed += len(batch)
            result.errors.append(f"第 {'、'.join(str(no) for no in batch_nos)} 页改写失败：{exc}")
            continue

        scripts = extract_batch_scripts(payload, allowed)
        by_no = {slide.slide_no: slide for slide in batch}
        written = 0
        for slide_no, script in scripts.items():
            slide = by_no[slide_no]
            if await _write_script(session, project.id, str(slide.slide_uid), script, only_if_blank=only_if_blank):
                after[str(slide.slide_uid)] = script
                written += 1
        await session.commit()

        result.done += written
        result.failed += len(batch) - written
        await _update_revision(
            session,
            revision.id,
            status=REVISION_STATUS_RUNNING,
            progress=batch_progress(result.done + result.failed, result.total),
            after=after,
        )
        await _set_status(
            session,
            project.id,
            SCRIPT_AI_STATUS_RUNNING,
            batch_progress(result.done + result.failed, result.total),
            None,
        )

    if result.failed == 0:
        result.status = SCRIPT_AI_STATUS_DONE
    elif result.done > 0:
        result.status = SCRIPT_AI_STATUS_PARTIAL
    else:
        result.status = SCRIPT_AI_STATUS_FAILED

    revision_status = (
        REVISION_STATUS_SUCCEEDED if result.status != SCRIPT_AI_STATUS_FAILED else REVISION_STATUS_FAILED
    )
    await _update_revision(
        session,
        revision.id,
        status=revision_status,
        progress=100,
        after=after,
        error=_join_errors(result.errors),
    )
    await _set_status(session, project.id, result.status, 100, _join_errors(result.errors))
    logger.info(
        "讲稿改写完成: project=%s mode=%s 写入=%s 失败=%s",
        project.id,
        request.mode,
        result.done,
        result.failed,
    )
    return result


async def run_job(project_id: uuid.UUID, request_payload: dict[str, Any], user_id: str | None) -> dict[str, Any]:
    """后台任务 runner：独立会话，异常不外抛到事件循环。"""
    settings = await load_settings()
    request = RewriteRequest(
        mode=str(request_payload.get("mode") or REWRITE_MODE_FILL_BLANK),
        slide_uids=[str(uid) for uid in request_payload.get("slide_uids") or [] if uid],
        instruction=request_payload.get("instruction"),
        requested_by_name=request_payload.get("requested_by_name"),
    )
    async with async_session_factory() as session:
        project = await session.scalar(
            select(PptVideoProject).where(
                PptVideoProject.id == project_id,
                PptVideoProject.is_deleted.is_(False),
            )
        )
        if project is None:
            logger.warning("讲稿改写跳过：项目不存在 project=%s", project_id)
            return {"status": "skipped", "reason": "project_not_found"}

        revision_id = request_payload.get("revision_id")
        try:
            result = await run(
                session,
                project,
                request,
                settings,
                uuid.UUID(user_id) if user_id else None,
                uuid.UUID(str(revision_id)) if revision_id else None,
            )
        except Exception as exc:  # noqa: BLE001 — 后台任务必须自己收尾
            logger.exception("讲稿改写失败: project=%s", project_id)
            await session.rollback()
            async with async_session_factory() as failure_session:
                await _set_status(
                    failure_session,
                    project_id,
                    SCRIPT_AI_STATUS_FAILED,
                    0,
                    f"讲稿改写失败：{str(exc)[:MAX_ERROR_CHARS]}",
                )
                if revision_id:
                    await _update_revision(
                        failure_session,
                        uuid.UUID(str(revision_id)),
                        status=REVISION_STATUS_FAILED,
                        progress=0,
                        error=str(exc),
                    )
            return {"status": SCRIPT_AI_STATUS_FAILED, "error": str(exc)[:MAX_ERROR_CHARS]}
    return result.to_dict()


async def submit(
    project_id: uuid.UUID,
    request_payload: dict[str, Any],
    user_id: uuid.UUID | None,
) -> uuid.UUID | None:
    """提交后台改写任务。"""
    return await submit_job_safe(
        JOB_NAME,
        lambda _job_id: run_job(project_id, request_payload, str(user_id) if user_id else None),
    )


async def list_revisions(session: AsyncSession, project_id: uuid.UUID, limit: int = 30) -> list[PptVideoScriptRevision]:
    result = await session.scalars(
        select(PptVideoScriptRevision)
        .where(
            PptVideoScriptRevision.project_id == project_id,
            PptVideoScriptRevision.is_deleted.is_(False),
        )
        .order_by(PptVideoScriptRevision.created_at.desc())
        .limit(limit)
    )
    return list(result.all())


async def rollback_revision(
    session: AsyncSession,
    project_id: uuid.UUID,
    revision_id: uuid.UUID,
) -> int:
    """把某次修订的 before 写回，返回恢复的页数。"""
    revision = await session.scalar(
        select(PptVideoScriptRevision).where(
            PptVideoScriptRevision.id == revision_id,
            PptVideoScriptRevision.project_id == project_id,
            PptVideoScriptRevision.is_deleted.is_(False),
        )
    )
    if revision is None:
        raise ValueError("修订记录不存在")
    if not revision.applied:
        raise ValueError("该修订已回滚过")

    restored = 0
    for slide_uid, script in (revision.before or {}).items():
        updated = await session.execute(
            update(PptVideoSlide)
            .where(
                PptVideoSlide.project_id == project_id,
                PptVideoSlide.slide_uid == uuid.UUID(str(slide_uid)),
                PptVideoSlide.is_deleted.is_(False),
            )
            .values(
                script_text=script or "",
                audio_object_key=None,
                audio_sha256=None,
                duration_ms=0,
                updated_at=func.now(),
            )
        )
        restored += cast(CursorResult[Any], updated).rowcount or 0

    revision.applied = False
    revision.status = REVISION_STATUS_FAILED if revision.status == REVISION_STATUS_RUNNING else revision.status
    await session.commit()
    return restored
