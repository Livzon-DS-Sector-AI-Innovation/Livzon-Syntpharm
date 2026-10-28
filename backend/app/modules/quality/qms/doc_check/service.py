"""Doc Check 模块业务逻辑层

负责文档上传暂存、文本抽取、LLM 调用与问题落库。
表格字段以 quality.sop_ai_check_main / quality.sop_ai_check_problem 为准。
"""

import asyncio
import logging
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Any

import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, DuplicateException, NotFoundException
from app.core.llm import LLMError, llm_client
from app.core.storage import get_object, upload_object
from app.core.storage import is_enabled as storage_enabled
from app.modules.quality.qms.doc_check.repository import DocCheckRepository
from app.modules.quality.qms.doc_check.schemas import (
    DocCheckConfigCreate,
    DocCheckConfigUpdate,
    DocCheckCreate,
    DocCheckUpdate,
    ProblemUpdate,
)
from app.modules.quality.sop_ai.models import (
    CheckStatus,
    HandleStatus,
    ProblemType,
    RiskLevel,
    SopAiCheckMain,
    SopAiCheckProblem,
)

logger = logging.getLogger(__name__)

# 单次提交给 LLM 的正文上限与问题条数上限，避免超长文档撑爆上下文
MAX_DOC_CHARS = 30000
MAX_PROBLEMS = 50
# 未启用 MinIO 时的进程内兜底缓存上限（仅用于本地开发）
UPLOAD_CACHE_MAX_ENTRIES = 16
UPLOAD_CACHE_MAX_BYTES = 64 * 1024 * 1024

STORAGE_MODULE = "quality"
OBJECT_PREFIX = "doc-check"

_PROBLEM_TYPE_ALIASES: dict[str, ProblemType] = {
    "duplicate": ProblemType.DUPLICATE,
    "重复": ProblemType.DUPLICATE,
    "重复文件": ProblemType.DUPLICATE,
    "conflict": ProblemType.CONFLICT,
    "冲突": ProblemType.CONFLICT,
    "参数冲突": ProblemType.CONFLICT,
    "compliance": ProblemType.COMPLIANCE,
    "合规": ProblemType.COMPLIANCE,
    "合规问题": ProblemType.COMPLIANCE,
    "format": ProblemType.FORMAT,
    "格式": ProblemType.FORMAT,
    "格式问题": ProblemType.FORMAT,
    "content": ProblemType.CONTENT,
    "内容": ProblemType.CONTENT,
    "内容问题": ProblemType.CONTENT,
    "logic": ProblemType.CONTENT,
    "missing": ProblemType.CONTENT,
}

_RISK_LEVEL_ALIASES: dict[str, RiskLevel] = {
    "high": RiskLevel.HIGH,
    "critical": RiskLevel.HIGH,
    "error": RiskLevel.HIGH,
    "高": RiskLevel.HIGH,
    "严重": RiskLevel.HIGH,
    "medium": RiskLevel.MEDIUM,
    "warning": RiskLevel.MEDIUM,
    "中": RiskLevel.MEDIUM,
    "警告": RiskLevel.MEDIUM,
    "low": RiskLevel.LOW,
    "info": RiskLevel.LOW,
    "低": RiskLevel.LOW,
    "提示": RiskLevel.LOW,
}


@dataclass(frozen=True)
class UploadedDoc:
    """一次上传的元信息"""

    file_id: str
    file_name: str
    file_size: int
    content_type: str

    @property
    def object_key(self) -> str:
        return f"{OBJECT_PREFIX}/{self.file_id}"


_upload_cache: OrderedDict[str, tuple[UploadedDoc, bytes | None]] = OrderedDict()
_upload_cache_bytes = 0


def _remember_upload(doc: UploadedDoc, payload: bytes | None) -> None:
    """记录上传结果；MinIO 可用时只留元信息，不可用时缓存正文。"""
    global _upload_cache_bytes
    _upload_cache[doc.file_id] = (doc, payload)
    _upload_cache.move_to_end(doc.file_id)
    if payload is not None:
        _upload_cache_bytes += len(payload)
    while _upload_cache and (
        len(_upload_cache) > UPLOAD_CACHE_MAX_ENTRIES or _upload_cache_bytes > UPLOAD_CACHE_MAX_BYTES
    ):
        _, dropped = _upload_cache.popitem(last=False)
        if dropped[1] is not None:
            _upload_cache_bytes -= len(dropped[1])


async def store_upload(file_name: str, content_type: str, data: bytes) -> UploadedDoc:
    """保存上传文件：优先 MinIO，不可用时退化为进程内缓存。"""
    doc = UploadedDoc(
        file_id=str(uuid.uuid4()),
        file_name=file_name,
        file_size=len(data),
        content_type=content_type,
    )
    if storage_enabled():
        await asyncio.to_thread(upload_object, STORAGE_MODULE, doc.object_key, data, len(data), content_type)
        _remember_upload(doc, None)
    else:
        logger.warning("MinIO 未启用，上传文件仅保存在当前进程内存中: file_id=%s", doc.file_id)
        _remember_upload(doc, data)
    return doc


async def load_upload_bytes(file_id: str) -> bytes | None:
    """读取上传文件正文；进程内没有则回源 MinIO。"""
    entry = _upload_cache.get(file_id)
    if entry is not None and entry[1] is not None:
        _upload_cache.move_to_end(file_id)
        return entry[1]
    if not storage_enabled():
        return None
    stored = await asyncio.to_thread(get_object, STORAGE_MODULE, f"{OBJECT_PREFIX}/{file_id}")
    return stored[0] if stored else None


def _extract_text(data: bytes) -> str:
    """按文件头识别格式并抽取纯文本（docx / pdf / txt）。"""
    if data.startswith(b"%PDF"):
        import pdfplumber

        with pdfplumber.open(BytesIO(data)) as pdf:
            return "\n".join((page.extract_text() or "") for page in pdf.pages)
    if data.startswith(b"PK\x03\x04"):
        import docx

        document = docx.Document(BytesIO(data))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    return data.decode("utf-8", errors="replace")


def _clip(value: Any, limit: int) -> str | None:
    """截断到列长度上限。"""
    if value is None:
        return None
    text = str(value).strip()
    return text[:limit] or None


def _to_problem_type(value: Any) -> ProblemType:
    if isinstance(value, ProblemType):
        return value
    return _PROBLEM_TYPE_ALIASES.get(str(value or "").strip().lower(), ProblemType.CONTENT)


def _to_risk_level(value: Any) -> RiskLevel:
    if isinstance(value, RiskLevel):
        return value
    return _RISK_LEVEL_ALIASES.get(str(value or "").strip().lower(), RiskLevel.MEDIUM)


def _enum_value(value: Any) -> str:
    """枚举成员取小写值，兼容直接存字符串的历史数据。"""
    if isinstance(value, str):
        return value.lower()
    return str(getattr(value, "value", value)).lower()


class DocCheckService:
    """Doc Check 模块服务层"""

    DEFAULT_SYSTEM_PROMPT = """你是一位 GMP 文档审核专家，负责审核制药企业的 SOP、质量标准等文件。
请从格式规范、内容完整性、法规合规性、逻辑合理性、参数一致性等维度审核，并只以 JSON 返回结果：
{
  "summary": "总体结论（200 字以内）",
  "problems": [
    {
      "problem_type": "duplicate|conflict|compliance|format|content",
      "risk_level": "high|medium|low",
      "location": "问题所在章节或页码",
      "description": "问题描述",
      "suggestion": "整改建议",
      "source_file": "来源文件名"
    }
  ]
}
没有发现问题时 problems 返回空数组。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DocCheckRepository(session)

    # ============ 配置 ============

    async def get_configs(self) -> list[Any]:
        return await self.repo.get_configs()

    async def get_config(self, config_id: str) -> Any:
        config = await self.repo.get_config_by_id(config_id)
        if config is None:
            raise NotFoundException("配置", config_id)
        return config

    async def create_config(self, data: DocCheckConfigCreate, operator: str | None) -> Any:
        if await self.repo.get_config_by_key(data.config_key) is not None:
            raise DuplicateException("配置键", data.config_key)
        try:
            return await self.repo.create_config(
                {
                    "config_key": data.config_key,
                    "config_value": data.config_value,
                    "description": data.description,
                    "operator": operator,
                }
            )
        except IntegrityError as exc:
            await self.session.rollback()
            raise DuplicateException("配置键", data.config_key) from exc

    async def update_config(self, config_id: str, data: DocCheckConfigUpdate, operator: str | None) -> Any:
        config = await self.get_config(config_id)
        changes: dict[str, Any] = {"operator": operator}
        if data.config_value is not None:
            changes["config_value"] = data.config_value
        if data.description is not None:
            changes["description"] = data.description
        if len(changes) == 1:
            return config
        updated = await self.repo.update_config(config_id, changes)
        return updated or config

    # ============ 校验任务 ============

    async def create_check(self, data: DocCheckCreate, operator: str | None) -> SopAiCheckMain:
        return await self.repo.create_check(
            {
                "file_code": self._generate_file_code(data.doc_type),
                "file_type": data.doc_type,
                "file_name": data.doc_title,
                "check_type": data.check_type,
                "status": CheckStatus.PENDING.value,
                "operator": operator,
            }
        )

    async def get_checks(
        self,
        skip: int = 0,
        limit: int = 20,
        status: str | None = None,
        file_type: str | None = None,
        operator: str | None = None,
    ) -> tuple[list[SopAiCheckMain], int]:
        return await self.repo.get_checks(
            skip=skip,
            limit=limit,
            status=status,
            file_type=file_type,
            operator=operator,
        )

    async def get_check(self, check_id: str) -> SopAiCheckMain:
        check = await self.repo.get_check_by_id(check_id)
        if check is None:
            raise NotFoundException("校验任务", check_id)
        return check

    async def update_check(self, check_id: str, data: DocCheckUpdate) -> SopAiCheckMain:
        check = await self.get_check(check_id)
        if _enum_value(check.status) != CheckStatus.PENDING.value:
            raise BadRequestException("只有待处理状态的任务才能修改")
        changes: dict[str, Any] = {}
        if data.doc_type is not None:
            changes["file_type"] = data.doc_type
        if data.doc_title is not None:
            changes["file_name"] = data.doc_title
        if data.check_type is not None:
            changes["check_type"] = data.check_type
        if not changes:
            return check
        updated = await self.repo.update_check(check_id, changes)
        return updated or check

    async def mark_running(self, check_id: str) -> SopAiCheckMain:
        check = await self.get_check(check_id)
        status = _enum_value(check.status)
        if status == CheckStatus.RUNNING.value:
            raise BadRequestException("任务正在执行中，请稍后查看进度")
        if status == CheckStatus.COMPLETED.value:
            raise BadRequestException("已完成的任务不能重复执行")
        updated = await self.repo.update_check(
            check_id,
            {"status": CheckStatus.RUNNING.value, "result_summary": None},
        )
        return updated or check

    async def cancel_check(self, check_id: str) -> SopAiCheckMain:
        check = await self.get_check(check_id)
        if _enum_value(check.status) not in (CheckStatus.PENDING.value, CheckStatus.RUNNING.value):
            raise BadRequestException("只有待处理或执行中的任务才能取消")
        updated = await self.repo.update_check(check_id, {"status": CheckStatus.CANCELLED.value})
        return updated or check

    async def delete_check(self, check_id: str) -> None:
        check = await self.get_check(check_id)
        if _enum_value(check.status) == CheckStatus.RUNNING.value:
            raise BadRequestException("执行中的任务不能删除，请先取消")
        if not await self.repo.delete_check(check_id):
            raise NotFoundException("校验任务", check_id)

    async def execute_check(
        self,
        check_id: str,
        *,
        file_id: str | None,
        doc_content: str | None,
        operator: str | None,
    ) -> str:
        """执行校验：抽取正文 → 调用 LLM → 落库问题明细。返回最终状态。"""
        check = await self.get_check(check_id)
        try:
            text = (doc_content or "").strip() or await self._load_document_text(file_id)
            summary, problems = await self._analyze(check, text)
            await self.repo.soft_delete_problems_by_check(check_id)
            if problems:
                await self.repo.create_problems_bulk(check_id, problems)
            await self.repo.update_check(
                check_id,
                {
                    "status": CheckStatus.COMPLETED.value,
                    "result_summary": summary,
                    "total_problems": len(problems),
                    "risk_high": sum(1 for item in problems if item["risk_level"] is RiskLevel.HIGH),
                    "risk_medium": sum(1 for item in problems if item["risk_level"] is RiskLevel.MEDIUM),
                    "risk_low": sum(1 for item in problems if item["risk_level"] is RiskLevel.LOW),
                    "operator": operator or check.operator,
                },
            )
            logger.info(
                "文档校验完成: check_id=%s problem_count=%s",
                check_id,
                len(problems),
                extra={"module": "quality", "check_id": check_id},
            )
            return CheckStatus.COMPLETED.value
        except BadRequestException as exc:
            logger.warning("文档校验前置条件不满足: check_id=%s detail=%s", check_id, exc.detail)
            await self.repo.update_check(
                check_id,
                {"status": CheckStatus.FAILED.value, "result_summary": str(exc.detail or "校验执行失败")},
            )
            raise
        except (LLMError, httpx.HTTPError):
            logger.exception("文档校验 AI 调用失败: check_id=%s", check_id)
            await self.repo.update_check(
                check_id,
                {"status": CheckStatus.FAILED.value, "result_summary": "AI 分析暂时不可用，请人工审核"},
            )
            return CheckStatus.FAILED.value
        except Exception:
            logger.exception("文档校验执行失败: check_id=%s", check_id)
            await self.repo.update_check(
                check_id,
                {"status": CheckStatus.FAILED.value, "result_summary": "校验执行失败，请重试或人工审核"},
            )
            raise

    # ============ 问题明细 ============

    async def get_problems(self, check_id: str) -> list[SopAiCheckProblem]:
        return await self.repo.get_problems_by_check(check_id)

    async def update_problem(self, problem_id: str, data: ProblemUpdate, operator: str | None) -> SopAiCheckProblem:
        problem = await self.repo.get_problem_by_id(problem_id)
        if problem is None:
            raise NotFoundException("问题", problem_id)
        handle_status = HandleStatus(data.handle_status)
        ignore_reason = data.ignore_reason or problem.ignore_reason
        if handle_status is HandleStatus.IGNORED and not ignore_reason:
            raise BadRequestException("忽略问题必须填写忽略原因")
        updated = await self.repo.update_problem(
            problem_id,
            {
                "handle_status": handle_status,
                "ignore_reason": ignore_reason if handle_status is HandleStatus.IGNORED else None,
                "operator": operator,
            },
        )
        return updated or problem

    async def batch_update_problems(
        self,
        problem_ids: list[str],
        handle_status: str,
        ignore_reason: str | None,
        operator: str | None,
    ) -> tuple[int, list[str]]:
        updated = 0
        skipped: list[str] = []
        payload = ProblemUpdate(handle_status=handle_status, ignore_reason=ignore_reason)
        for problem_id in dict.fromkeys(problem_ids):
            try:
                await self.update_problem(problem_id, payload, operator)
            except (NotFoundException, BadRequestException) as exc:
                logger.info("批量处理跳过问题: problem_id=%s detail=%s", problem_id, exc.detail)
                skipped.append(problem_id)
            else:
                updated += 1
        return updated, skipped

    async def confirm_check(self, check_id: str, operator: str | None) -> tuple[str, int]:
        """确认通过：把仍未处理的问题标记为已确认，返回（任务状态, 确认条数）。"""
        check = await self.get_check(check_id)
        if _enum_value(check.status) != CheckStatus.COMPLETED.value:
            raise BadRequestException("只有已完成的校验才能确认通过")
        problems = await self.repo.get_problems_by_check(check_id)
        pending = [item for item in problems if _enum_value(item.handle_status) == HandleStatus.PENDING.value]
        for item in pending:
            await self.repo.update_problem(
                item.id,
                {"handle_status": HandleStatus.CONFIRMED, "ignore_reason": None, "operator": operator},
            )
        return _enum_value(check.status), len(pending)

    # ============ 内部方法 ============

    def _generate_file_code(self, doc_type: str) -> str:
        prefix = "".join(ch for ch in doc_type.strip().upper() if ch.isalnum()) or "DOC"
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"DC-{prefix}-{timestamp}-{uuid.uuid4().hex[:4].upper()}"

    async def _load_document_text(self, file_id: str | None) -> str:
        if not file_id:
            raise BadRequestException("缺少待校验文件，请先上传文件或提交文档正文")
        data = await load_upload_bytes(file_id)
        if data is None:
            raise BadRequestException("上传文件已失效，请重新上传")
        try:
            text = await asyncio.to_thread(_extract_text, data)
        except Exception as exc:
            logger.exception("文档解析失败: file_id=%s", file_id)
            raise BadRequestException("文档解析失败，请确认格式为 docx/pdf/txt") from exc
        cleaned = text.strip()
        if not cleaned:
            raise BadRequestException("未能从文档中提取到文本内容")
        return cleaned[:MAX_DOC_CHARS]

    async def _analyze(self, check: SopAiCheckMain, text: str) -> tuple[str, list[dict[str, Any]]]:
        payload = await llm_client.chat_json(
            messages=[
                {"role": "system", "content": await self._get_system_prompt()},
                {"role": "user", "content": self._build_prompt(check.file_name or "", check.file_type or "", text)},
            ],
            expected_keys=["summary", "problems"],
            temperature=0.3,
        )
        summary = _clip(payload.get("summary"), 4000) or "AI 未返回总体结论，请人工复核"
        raw_items = payload.get("problems")
        items = raw_items if isinstance(raw_items, list) else []
        problems: list[dict[str, Any]] = []
        for item in items[:MAX_PROBLEMS]:
            if not isinstance(item, dict):
                continue
            normalized = self._normalize_problem(item, check)
            if normalized["description"] or normalized["suggestion"]:
                problems.append(normalized)
        return summary, problems

    def _normalize_problem(self, item: dict[str, Any], check: SopAiCheckMain) -> dict[str, Any]:
        return {
            "problem_type": _to_problem_type(item.get("problem_type") or item.get("category")),
            "risk_level": _to_risk_level(item.get("risk_level") or item.get("severity")),
            "location": _clip(item.get("location"), 500),
            "description": _clip(item.get("description") or item.get("title"), 4000),
            "source_file": _clip(item.get("source_file") or check.file_name, 500),
            "suggestion": _clip(item.get("suggestion"), 4000),
            "handle_status": HandleStatus.PENDING,
            "operator": check.operator,
        }

    async def _get_system_prompt(self) -> str:
        config = await self.repo.get_config_by_key("system_prompt")
        if config is not None and config.config_value and config.config_value.strip():
            return config.config_value.strip()
        return self.DEFAULT_SYSTEM_PROMPT

    def _build_prompt(self, file_name: str, file_type: str, text: str) -> str:
        return f"""请审核以下{file_type or "SOP"}文档：
文档名称：{file_name or "未命名"}
文档正文：
{text}

请按系统提示要求返回 JSON 审核结果。"""
