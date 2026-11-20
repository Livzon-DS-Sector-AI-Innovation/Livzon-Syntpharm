"""DOCX 翻译 —— 任务编排。

流程：上传字节 → 临时目录落盘 → 提取 → LLM 翻译 → 按模式回写 →
结果存 MinIO → 清理临时文件。所有 python-docx 操作放在线程里执行，
LLM 调用在事件循环内异步进行。
"""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
import tempfile
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.database import async_session_factory
from app.core.exceptions import BadRequestException, NotFoundException
from app.shared.config_reader import get_module_setting_int

from .config import MODE_BILINGUAL, MODE_BOTH, MODE_REPLACE, UNIT_WHITELIST, TranslateConfig
from .engine_models import TranslationResult
from .extractor import DocxExtractor
from .glossary import Glossary
from .jobs import get_registry
from .models import DocxTranslationFile, DocxTranslationTask
from .repository import (
    DocxTranslationFileRepository,
    DocxTranslationTaskRepository,
    DocxTranslationTermRepository,
)
from .translator import Translator
from .validator import Validator
from .writer import DocxWriter

logger = logging.getLogger(__name__)

MODULE = "docx_translator"
STORAGE_MODULE = "registration"
DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

SETTING_MAX_FILE_MB = "DOCX_TRANSLATOR_MAX_FILE_MB"
SETTING_MAX_FILES = "DOCX_TRANSLATOR_MAX_FILES"
SETTING_BATCH_SIZE = "DOCX_TRANSLATOR_DEFAULT_BATCH_SIZE"
SETTING_MIN_SUCCESS_RATE = "DOCX_TRANSLATOR_MIN_SUCCESS_RATE"
SETTING_RETENTION_DAYS = "DOCX_TRANSLATOR_RETENTION_DAYS"
SETTING_FILE_TIMEOUT_MINUTES = "DOCX_TRANSLATOR_FILE_TIMEOUT_MINUTES"

DEFAULT_MAX_FILE_MB = 50
DEFAULT_MAX_FILES = 10
DEFAULT_BATCH_SIZE = 30
DEFAULT_MIN_SUCCESS_RATE = 90
DEFAULT_RETENTION_DAYS = 30
DEFAULT_FILE_TIMEOUT_MINUTES = 30

# 纯数字/符号/单位不需要送模型；只要含字母或汉字就必须翻译
_TRANSLATABLE_PATTERN = re.compile(r"[A-Za-z\u4e00-\u9fff]")
_UNITS_BY_LENGTH = sorted(UNIT_WHITELIST, key=len, reverse=True)

SUPPORTED_SUFFIXES = (".docx", ".doc", ".wps")


@dataclass
class UploadedDoc:
    filename: str
    data: bytes


def sanitize_filename(name: str) -> str:
    """只保留文件名本身，去掉路径分隔符与控制字符。"""
    base = Path(name.replace("\\", "/")).name
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", base).strip()
    return cleaned or f"document_{uuid.uuid4().hex[:6]}.docx"


async def load_limits() -> tuple[int, int, float]:
    """读取运行时限制：单文件大小 MB、单次文件数、成功率告警阈值。"""
    max_file_mb = await get_module_setting_int(MODULE, SETTING_MAX_FILE_MB, DEFAULT_MAX_FILE_MB)
    max_files = await get_module_setting_int(MODULE, SETTING_MAX_FILES, DEFAULT_MAX_FILES)
    min_rate = await get_module_setting_int(MODULE, SETTING_MIN_SUCCESS_RATE, DEFAULT_MIN_SUCCESS_RATE)
    return max_file_mb, max_files, float(min_rate)


def validate_uploads(files: list[UploadedDoc], max_file_mb: int, max_files: int) -> None:
    if not files:
        raise BadRequestException("请先上传至少一个 Word 文档")
    if len(files) > max_files:
        raise BadRequestException(f"单次最多处理 {max_files} 个文件")
    limit_bytes = max_file_mb * 1024 * 1024
    for item in files:
        suffix = Path(item.filename).suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            raise BadRequestException(f"不支持的文件类型：{item.filename}（仅支持 .docx / .doc / .wps）")
        if len(item.data) > limit_bytes:
            raise BadRequestException(f"文件超过 {max_file_mb}MB：{item.filename}")
        if not item.data:
            raise BadRequestException(f"文件内容为空：{item.filename}")


async def load_glossary(session: AsyncSession) -> Glossary:
    """启用中的术语，统一按 {中文: 英文} 组织（引擎按方向自行取用）。"""
    repo = DocxTranslationTermRepository(session)
    rows = await repo.list_enabled()
    glossary = Glossary()
    glossary.load_from_terms({row.term_zh: row.term_en for row in rows})
    return glossary


def _build_config(source_lang: str, target_lang: str, mode: str, batch_size: int) -> TranslateConfig:
    config = TranslateConfig(
        source_lang=source_lang,
        target_lang=target_lang,
        mode=mode,
        batch_size=batch_size,
    )
    errors = config.validate()
    if errors:
        raise BadRequestException("；".join(errors))
    return config


def _modes_for(config: TranslateConfig) -> list[str]:
    if config.mode == MODE_BOTH:
        return [MODE_BILINGUAL, MODE_REPLACE]
    return [config.mode]


def _output_name(stem: str, mode: str, target_lang: str) -> str:
    suffix = "_bi" if mode == MODE_BILINGUAL else f"_{target_lang}"
    return f"{stem}{suffix}.docx"


def _extract(docx_path: str) -> tuple[Any, list[Any], DocxExtractor]:
    extractor = DocxExtractor()
    doc, units = extractor.extract(docx_path)
    return doc, units, extractor


def _write_output(
    source_path: str,
    out_path: str,
    mode: str,
    target_lang: str,
    results: list[TranslationResult],
) -> dict[str, Any]:
    """在新加载的 Document 上回写，返回保存后校验统计。"""
    doc, units, _extractor = _extract(source_path)
    writer = DocxWriter(mode=mode, target_lang=target_lang)
    writer.write(doc, out_path, units, results)
    return Validator().validate_post_save(out_path, units, results, mode=mode)


def is_translatable(text: str) -> bool:
    """是否包含可译字符：纯数字、单位、编号、符号一律跳过。

    先按单位白名单剔除单位（长单位优先，避免 mg 被 g 拆掉），
    剩下只要还有字母或汉字就必须翻译（如 "3 batches"）。
    """
    cleaned = text or ""
    for unit in _UNITS_BY_LENGTH:
        cleaned = cleaned.replace(unit, "")
    return bool(_TRANSLATABLE_PATTERN.search(cleaned))


async def translate_one(
    item: UploadedDoc,
    config: TranslateConfig,
    glossary: Glossary,
    *,
    job_id: str,
    file_index: int,
    min_success_rate: float,
    on_batch_done: Callable[[int, int], None] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """翻译单个文件，返回 (文件结果, 输出文件描述列表)。"""
    filename = sanitize_filename(item.filename)
    stem = Path(filename).stem
    work_dir = tempfile.mkdtemp(prefix="docx_translator_")
    extractor: DocxExtractor | None = None
    try:
        src = Path(work_dir) / filename
        src.write_bytes(item.data)

        doc, units, extractor = await asyncio.to_thread(_extract, str(src))
        if not units:
            raise RuntimeError("文档中没有可翻译的文本段落")

        translatable = [unit for unit in units if is_translatable(unit.text)]
        skipped_units = len(units) - len(translatable)
        if skipped_units:
            logger.info(
                "跳过无需翻译的段落: skipped=%d total=%d",
                skipped_units,
                len(units),
                extra={"job_id": job_id, "biz_module": "registration"},
            )
        if not translatable:
            # 整篇都是数字/符号：没有可译内容，直接按失败处理，避免产出空文件
            raise RuntimeError("文档中没有可翻译的文本段落")

        translator = Translator(config=config, glossary=glossary)
        results = await translator.translate_all(translatable, on_batch_done=on_batch_done)
        stats = Validator().validate(translatable, results)

        outputs: list[dict[str, Any]] = []
        warnings: list[str] = []
        if float(stats.get("success_rate", 0.0)) < min_success_rate:
            warnings.append(
                f"段落成功率 {float(stats.get('success_rate', 0.0)):.1f}% 低于 {min_success_rate:.0f}%，请人工复核"
            )

        converted = extractor.get_converted_temp_path() if extractor is not None else None
        source_docx = converted or str(src)
        for mode in _modes_for(config):
            out_name = _output_name(stem, mode, config.target_lang)
            out_path = Path(work_dir) / out_name
            post = await asyncio.to_thread(_write_output, source_docx, str(out_path), mode, config.target_lang, results)
            if not post.get("match", True):
                warnings.append(
                    "保存后校验：" + ("译文段落数与预期不一致" if mode == MODE_BILINGUAL else "存在原文残留")
                )

            key = f"docx_translations/{datetime.now(UTC):%Y%m%d}/{job_id}/{file_index}_{out_name}"
            data = out_path.read_bytes()
            if not storage.is_enabled():
                raise RuntimeError("文件存储未启用，无法保存翻译结果")
            await asyncio.to_thread(storage.upload_object, STORAGE_MODULE, key, data, len(data), DOCX_CONTENT_TYPE)
            outputs.append(
                {
                    "kind": "bilingual" if mode == MODE_BILINGUAL else "translated",
                    "filename": out_name,
                    "file_index": file_index,
                    "object_key": key,
                    "file_size": len(data),
                }
            )
            file_index += 1

        result = {
            "filename": filename,
            "success": bool(outputs),
            "outputs": outputs,
            "translated_units": int(stats.get("success", 0)),
            "total_units": int(stats.get("total_units", 0)),
            "success_rate": round(float(stats.get("success_rate", 0.0)), 1),
            "warnings": warnings,
            "error": None,
            "skipped_units": skipped_units,
        }
        return result, outputs
    finally:
        if extractor is not None:
            try:
                extractor.cleanup_converted()
            except Exception:  # noqa: BLE001 - 清理失败不影响主流程
                logger.warning("cleanup converted temp failed", extra={"biz_module": "registration"})
        shutil.rmtree(work_dir, ignore_errors=True)


async def run_job(
    job_id: str,
    files: list[UploadedDoc],
    config: TranslateConfig,
    glossary: Glossary,
    min_success_rate: float,
    user_id: UUID | None = None,
) -> dict[str, Any]:
    """后台任务主体：归档原件 → 建任务行 → 逐文件翻译 → 收尾回写。

    单文件失败不影响其他文件，失败也会落库（含原因）；
    任务收尾放在 finally，异常时也写 failed，避免任务永远停在 running。
    """
    registry = get_registry()
    started = time.monotonic()
    file_timeout = await resolve_file_timeout_seconds()
    source_keys = await upload_sources(job_id, files)
    task_id = await create_task(
        job_id=job_id,
        files=files,
        config=config,
        source_keys=source_keys,
        user_id=user_id,
    )

    results: list[dict[str, Any]] = []
    next_index = 0
    success_count = 0
    fail_count = 0
    status = "done"
    task_error: str | None = None
    try:
        for done, item in enumerate(files, start=1):
            current_name = sanitize_filename(item.filename)
            registry.update(job_id, current_file=current_name, batch_done=0, batch_total=0)

            def _on_batch(batch_index: int, batch_total: int) -> None:
                registry.update(job_id, batch_done=batch_index, batch_total=batch_total)
                logger.info(
                    "docx translation batch done: %d/%d",
                    batch_index,
                    batch_total,
                    extra={"job_id": job_id, "source_file": current_name, "biz_module": "registration"},
                )

            try:
                call = translate_one(
                    item,
                    config,
                    glossary,
                    job_id=job_id,
                    file_index=next_index,
                    min_success_rate=min_success_rate,
                    on_batch_done=_on_batch,
                )
                if file_timeout > 0:
                    file_result, outputs = await asyncio.wait_for(call, timeout=file_timeout)
                else:
                    file_result, outputs = await call
                next_index += len(outputs)
            except TimeoutError:
                logger.warning(
                    "docx translation file timeout",
                    extra={"job_id": job_id, "source_file": current_name, "biz_module": "registration"},
                )
                file_result = {
                    "filename": current_name,
                    "success": False,
                    "outputs": [],
                    "translated_units": 0,
                    "total_units": 0,
                    "success_rate": 0.0,
                    "warnings": [],
                    "error": f"处理超时（>{int(file_timeout // 60)} 分钟），已终止",
                    "skipped_units": 0,
                }
            except Exception as e:  # noqa: BLE001 - 单文件失败写入结果，不中断任务
                logger.exception("docx translation failed for file", extra={"job_id": job_id})
                file_result = {
                    "filename": sanitize_filename(item.filename),
                    "success": False,
                    "outputs": [],
                    "translated_units": 0,
                    "total_units": 0,
                    "success_rate": 0.0,
                    "warnings": [],
                    "error": str(e) or "翻译失败",
                    "skipped_units": 0,
                }
            results.append(file_result)
            if file_result.get("success"):
                success_count += 1
            else:
                fail_count += 1
            await persist_file_records(
                job_id=job_id,
                task_id=task_id,
                item=item,
                config=config,
                file_result=file_result,
                user_id=user_id,
            )
            # 文件落库后立刻回写任务计数，历史列表能看到「翻译中 2/3」
            await update_task_progress(task_id, success_count=success_count, fail_count=fail_count)
            registry.update(job_id, files_done=done)
    except Exception as e:
        status = "failed"
        task_error = str(e) or "翻译任务异常"
        raise
    finally:
        registry.update(job_id, current_file=None, batch_done=0, batch_total=0)
        await finish_task(
            task_id,
            status=status,
            success_count=success_count,
            fail_count=fail_count,
            elapsed_seconds=int(time.monotonic() - started),
            error=task_error,
        )

    return {"files": results}


def build_job_config(source_lang: str, target_lang: str, mode: str, batch_size: int | None) -> TranslateConfig:
    return _build_config(source_lang, target_lang, mode, batch_size or DEFAULT_BATCH_SIZE)


async def resolve_batch_size(batch_size: int | None) -> int:
    if batch_size:
        return batch_size
    return await get_module_setting_int(MODULE, SETTING_BATCH_SIZE, DEFAULT_BATCH_SIZE)


def find_output(result: dict[str, Any] | None, file_index: int) -> dict[str, Any] | None:
    """按 file_index 在任务结果里定位输出文件（禁止外部传 object key）。"""
    if not result:
        return None
    for item in result.get("files") or []:
        for output in item.get("outputs") or []:
            if isinstance(output, dict) and int(output.get("file_index", -1)) == file_index:
                return dict(output)
    return None


__all__ = [
    "DOCX_CONTENT_TYPE",
    "DEFAULT_RETENTION_DAYS",
    "STORAGE_MODULE",
    "UploadedDoc",
    "build_job_config",
    "create_task",
    "delete_file_record",
    "delete_task_records",
    "update_task_progress",
    "finish_task",
    "get_task",
    "sources_for_retranslate",
    "upload_sources",
    "find_output",
    "get_file_record",
    "load_glossary",
    "load_limits",
    "persist_file_records",
    "read_file_object",
    "reconcile_interrupted_tasks",
    "resolve_batch_size",
    "resolve_file_timeout_seconds",
    "resolve_retention_days",
    "is_translatable",
    "run_job",
    "sanitize_filename",
    "validate_uploads",
]


async def sources_for_retranslate(task: DocxTranslationTask) -> list[UploadedDoc]:
    """从对象存储取回任务原件，供「再次翻译」重新提交。"""
    if not task.source_keys:
        raise BadRequestException("该任务未保存原件，无法再次翻译，请重新上传文件")

    files: list[UploadedDoc] = []
    for index, entry in enumerate(task.source_keys):
        key = str(entry.get("object_key") or "")
        filename = str(entry.get("filename") or f"document_{index + 1}.docx")
        stored = await asyncio.to_thread(storage.get_object, STORAGE_MODULE, key)
        if stored is None:
            raise BadRequestException(f"原件已被清理，无法再次翻译：{filename}")
        files.append(UploadedDoc(filename=filename, data=stored[0]))
    if not files:
        raise BadRequestException("该任务未保存原件，无法再次翻译，请重新上传文件")
    return files


async def delete_task_records(session: AsyncSession, task: DocxTranslationTask) -> None:
    """软删任务与其文件行，并尽力删除产出对象与原件。"""
    task_repo = DocxTranslationTaskRepository(session)
    file_repo = DocxTranslationFileRepository(session)

    keys: list[str] = []
    for row in await file_repo.list_by_job(task.job_ref):
        if row.object_key:
            keys.append(row.object_key)
    for entry in task.source_keys or []:
        key = str(entry.get("object_key") or "")
        if key:
            keys.append(key)

    await file_repo.soft_delete_by_job(task.job_ref)
    await task_repo.soft_delete(task)

    if not storage.is_enabled():
        return
    for key in keys:
        try:
            await asyncio.to_thread(storage.delete_object, STORAGE_MODULE, key)
        except Exception:
            logger.warning(
                "清理翻译任务对象失败",
                extra={"object_key": key, "biz_module": "registration"},
                exc_info=True,
            )


async def reconcile_interrupted_tasks(session: AsyncSession, tasks: list[DocxTranslationTask]) -> int:
    """把进程内已不存在的 running 任务标记为失败。

    任务进度只存在进程内（registry），服务重启/热重载会丢；
    数据库里的 running 行如果找不到对应 job，就是中断任务，
    不清理会一直显示「翻译中」。
    """
    registry = get_registry()
    changed = 0
    now = datetime.now(UTC)
    stale_after_seconds = 40 * 60
    for task in tasks:
        if task.status == "running":
            updated_at = task.updated_at or task.created_at
            if updated_at is not None and updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=UTC)
            stalled = bool(updated_at) and (now - updated_at).total_seconds() > stale_after_seconds

            if not stalled and registry.exists(task.job_ref):
                # 进程内还有该任务且近期有更新 → 仍在跑，交给逐文件回写
                continue

            task.status = "failed"
            if stalled:
                task.error = "任务超过 40 分钟无进展，已自动终止"
                registry.mark_failed(task.job_ref, task.error)
            else:
                task.error = "服务重启导致任务中断，请重新提交或再次翻译"
            changed += 1

        # 不论中断还是收尾异常，计数都以文件行为准，未完成的文件计入失败
        success, fail = await _derive_task_counts(session, task)
        if task.success_count != success or task.fail_count != fail:
            task.success_count = success
            task.fail_count = fail
            changed += 1

    if not changed:
        return 0
    await session.commit()
    logger.warning(
        "修正任务状态/计数: count=%d",
        changed,
        extra={"biz_module": "registration"},
    )
    return changed


async def get_task(session: AsyncSession, task_id: UUID) -> DocxTranslationTask:
    """按任务 ID 取任务，不存在/已删抛 404。"""
    task = await DocxTranslationTaskRepository(session).get(task_id)
    if task is None:
        raise NotFoundException("翻译任务不存在或已删除")
    return task


async def upload_sources(job_id: str, files: list[UploadedDoc]) -> list[dict[str, object]]:
    """把上传原件写入对象存储，供「再次翻译」与事后核对。"""
    if not storage.is_enabled():
        logger.warning("MinIO disabled; source files not archived", extra={"job_id": job_id})
        return []

    keys: list[dict[str, object]] = []
    for index, item in enumerate(files):
        filename = sanitize_filename(item.filename)
        key = f"docx_translations/{datetime.now(UTC):%Y%m%d}/{job_id}/source/{index}_{filename}"
        try:
            await asyncio.to_thread(
                storage.upload_object,
                STORAGE_MODULE,
                key,
                item.data,
                len(item.data),
                DOCX_CONTENT_TYPE,
            )
            keys.append({"filename": filename, "object_key": key, "size": len(item.data)})
        except Exception:
            logger.exception(
                "归档翻译原件失败",
                extra={"job_id": job_id, "source_filename": filename, "biz_module": "registration"},
            )
    return keys


async def create_task(
    *,
    job_id: str,
    files: list[UploadedDoc],
    config: TranslateConfig,
    source_keys: list[dict[str, object]],
    user_id: UUID | None,
) -> UUID | None:
    """建任务行（running）；失败不打断翻译，返回 None。"""
    try:
        async with async_session_factory() as session:
            task = DocxTranslationTask(
                id=uuid.uuid4(),
                job_ref=job_id,
                status="running",
                source_count=len(files),
                success_count=0,
                fail_count=0,
                first_source_filename=sanitize_filename(files[0].filename) if files else "",
                source_lang=config.source_lang,
                target_lang=config.target_lang,
                mode=config.mode,
                batch_size=config.batch_size,
                elapsed_seconds=0,
                source_keys=source_keys,
                created_by=user_id,
                updated_by=user_id,
            )
            saved = await DocxTranslationTaskRepository(session).create(task)
            return saved.id
    except Exception:
        logger.exception("建翻译任务行失败", extra={"job_id": job_id, "biz_module": "registration"})
        return None


async def update_task_progress(task_id: UUID | None, *, success_count: int, fail_count: int) -> None:
    """运行中逐文件回写计数；失败只记日志，不打断翻译主流程。"""
    if task_id is None:
        return
    try:
        async with async_session_factory() as session:
            await DocxTranslationTaskRepository(session).update_progress(
                task_id, success_count=success_count, fail_count=fail_count
            )
    except Exception:
        logger.exception(
            "回写翻译进度失败",
            extra={"task_id": str(task_id), "biz_module": "registration"},
        )


async def _derive_task_counts(session: AsyncSession, task: DocxTranslationTask) -> tuple[int, int]:
    """任务计数以文件行为唯一事实来源：成功=成功文件数，失败=总数-成功。"""
    success = await DocxTranslationFileRepository(session).count_success_by_job(task.job_ref)
    fail = max(task.source_count - success, 0)
    return success, fail


async def finish_task(
    task_id: UUID | None,
    *,
    status: str,
    success_count: int,
    fail_count: int,
    elapsed_seconds: int,
    error: str | None = None,
) -> None:
    """回写任务收尾状态；无论成功失败都必须调用，避免任务永久 running。"""
    if task_id is None:
        return
    try:
        async with async_session_factory() as session:
            repo = DocxTranslationTaskRepository(session)
            task = await repo.get(task_id)
            if task is None:
                return
            task.status = status
            # 内存变量可能因中断而不准，收尾时按已落库的文件行回算
            derived_success, derived_fail = await _derive_task_counts(session, task)
            task.success_count = derived_success
            task.fail_count = derived_fail
            task.elapsed_seconds = elapsed_seconds
            task.error = error
            await repo.save(task)
    except Exception:
        logger.exception("回写翻译任务状态失败", extra={"task_id": str(task_id), "biz_module": "registration"})


def _to_file_rows(
    *,
    job_id: str,
    task_id: UUID | None,
    item: UploadedDoc,
    config: TranslateConfig,
    file_result: dict[str, Any],
    user_id: UUID | None,
) -> list[DocxTranslationFile]:
    """把单个文件的处理结果映射为记录行：成功写产出，失败写原因。"""
    base = {
        "id": uuid.uuid4(),
        "task_id": task_id,
        "job_ref": job_id,
        "source_filename": str(file_result.get("filename") or sanitize_filename(item.filename)),
        "source_lang": config.source_lang,
        "target_lang": config.target_lang,
        "mode": config.mode,
        "success_rate": float(file_result.get("success_rate") or 0.0),
        "translated_units": int(file_result.get("translated_units") or 0),
        "total_units": int(file_result.get("total_units") or 0),
        "warnings": list(file_result.get("warnings") or []),
        "success": bool(file_result.get("success")),
        "error": file_result.get("error"),
        "created_by": user_id,
        "updated_by": user_id,
    }
    if not file_result.get("success"):
        return [
            DocxTranslationFile(
                **base,
                output_filename="",
                output_kind="",
                object_key=None,
                file_size=0,
            )
        ]

    rows: list[DocxTranslationFile] = []
    for output in file_result.get("outputs") or []:
        rows.append(
            DocxTranslationFile(
                **base,
                output_filename=str(output.get("filename") or ""),
                output_kind=str(output.get("kind") or ""),
                object_key=str(output.get("object_key") or ""),
                file_size=int(output.get("file_size") or 0),
            )
        )
    return rows


async def persist_file_records(
    *,
    job_id: str,
    item: UploadedDoc,
    config: TranslateConfig,
    file_result: dict[str, Any],
    user_id: UUID | None,
    task_id: UUID | None = None,
) -> None:
    """逐文件落库历史记录（成功与失败都写）；失败只记日志，绝不打断翻译任务。"""
    rows = _to_file_rows(
        job_id=job_id,
        task_id=task_id,
        item=item,
        config=config,
        file_result=file_result,
        user_id=user_id,
    )
    if not rows:
        return
    try:
        async with async_session_factory() as session:
            repo = DocxTranslationFileRepository(session)
            await repo.delete_by_source(job_id, rows[0].source_filename)
            await repo.create_many(rows)
    except Exception:
        logger.exception(
            "docx translation history persist failed",
            extra={"job_id": job_id, "biz_module": "registration"},
        )


async def get_file_record(session: AsyncSession, file_id: UUID) -> DocxTranslationFile:
    """按记录 ID 取历史文件，不存在/已删抛 404。"""
    record = await DocxTranslationFileRepository(session).get(file_id)
    if record is None:
        raise NotFoundException("翻译文件记录不存在或已删除")
    return record


def read_file_object(record: DocxTranslationFile) -> bytes | None:
    """从对象存储读取译文内容；对象已被清理时返回 None。"""
    if not record.object_key:
        return None
    stored = storage.get_object(STORAGE_MODULE, record.object_key)
    return stored[0] if stored else None


async def delete_file_record(session: AsyncSession, record: DocxTranslationFile) -> None:
    """软删记录 + 尽力删除对象（与授权书 delete_letter 口径一致）。"""
    repo = DocxTranslationFileRepository(session)
    await repo.soft_delete(record)
    if not record.object_key:
        return
    try:
        if storage.is_enabled():
            await asyncio.to_thread(storage.delete_object, STORAGE_MODULE, record.object_key)
    except Exception:
        logger.warning(
            "清理翻译结果文件失败",
            extra={"object_key": record.object_key, "biz_module": "registration"},
            exc_info=True,
        )


async def resolve_file_timeout_seconds() -> float:
    """单文件超时秒数；<=0 表示不限制。"""
    minutes = await get_module_setting_int(MODULE, SETTING_FILE_TIMEOUT_MINUTES, DEFAULT_FILE_TIMEOUT_MINUTES)
    return float(minutes) * 60 if minutes and minutes > 0 else 0.0


async def resolve_retention_days() -> int:
    """保留天数：<=0 表示不自动清理。"""
    return await get_module_setting_int(MODULE, SETTING_RETENTION_DAYS, DEFAULT_RETENTION_DAYS)
