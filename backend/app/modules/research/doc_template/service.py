"""交付物模板服务层：Word 母本的上传留档、版本历史、下载与回滚。

上传路径刻意不解析母本结构、不推断填充项：模板在这里只是一份带版本历史的 Word 原件。
只有「槽位结构」相关接口会临时扁平化母本（认位置，不调模型），供人工核对与重解析。
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.modules.research.doc_template import store

logger = logging.getLogger(__name__)

# ===== 交付物模板：Word 母本管理 =====

WORD_EXTENSIONS = {".docx", ".dotx", ".doc"}
_ZIP_MAGIC = b"PK\x03\x04"
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
MAX_TEMPLATE_BYTES = 50 * 1024 * 1024


def sniff_word_ext(filename: str, data: bytes) -> str:
    """校验文件内容与扩展名一致，返回规范化扩展名。

    只看扩展名会让改后缀的垃圾文件进库，直到渲染阶段才以 anchor_unresolved 暴露，
    排查成本极高，因此在入口处用文件头判断真实格式。
    """
    ext = Path(filename).suffix.lower()
    if ext not in WORD_EXTENSIONS:
        raise BadRequestException(f"不支持的模板格式：{ext or '未知'}（仅支持 {'、'.join(sorted(WORD_EXTENSIONS))}）")
    if not data:
        raise BadRequestException(f"模板文件为空：{filename}")
    if len(data) > MAX_TEMPLATE_BYTES:
        raise BadRequestException(f"模板文件超过 {MAX_TEMPLATE_BYTES // 1024 // 1024}MB 上限：{filename}")
    head = data[:8]
    if ext in {".docx", ".dotx"} and not head.startswith(_ZIP_MAGIC):
        raise BadRequestException(f"文件内容与扩展名不符（{filename} 不是真正的 Word XML 文档）")
    if ext == ".doc" and not head.startswith(_OLE_MAGIC):
        raise BadRequestException(f"文件内容与扩展名不符（{filename} 不是真正的 Word 97-2003 文档）")
    return ext


async def attach_template_file(
    session: AsyncSession,
    template: Any,
    filename: str,
    data: bytes,
    user_id: uuid.UUID | None,
    change_note: str | None = None,
) -> str:
    """校验并挂载一个 Word 母本到模板记录，返回存储键。

    只做格式校验与留档，不解析母本结构、不推断填充项：模板在这里只是一份可下载的
    Word 原件。每次挂载都会在版本表留档一条新记录（首次即 v1），并把模板主表指向它
    ——主表始终等于「当前生效版本」，所以下载与回滚完全不需要感知版本表。

    刻意不碰 ``is_active``：上传 ≠ 启用。
    """
    ext = sniff_word_ext(filename, data)
    key = store.save_bytes(
        f"template{ext}",
        data,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if ext != ".doc"
        else "application/msword",
    )
    template.file_object_key = key
    template.file_name = filename[:500]
    template.file_ext = ext
    template.updated_by = user_id
    # 先同步主表再留档：版本快照记录的应是「本次挂载后」的槽位定义
    await _record_template_version(
        session,
        template,
        filename=filename,
        ext=ext,
        size=len(data),
        key=key,
        change_note=change_note,
        user_id=user_id,
    )
    await session.flush()
    return key


async def _record_template_version(
    session: AsyncSession,
    template: Any,
    *,
    filename: str,
    ext: str,
    size: int | None,
    key: str,
    change_note: str | None,
    user_id: uuid.UUID | None,
) -> Any:
    """把刚挂载的母本留档为模板的新版本，并置为当前生效版本。

    版本号在模板行锁内取 ``max(version_no) + 1``：并发上传同一模板不会算出同一个号，
    ``UniqueConstraint(template_id, version_no)`` 是最后一道保险。软删的版本仍占号，
    因此版本号单调递增、永不复用。
    """
    from sqlalchemy import func, select, update

    from app.modules.research.models import RdDeliverableTemplate, RdDeliverableTemplateVersion

    # 锁模板行，避免并发上传把同一个版本号写两次
    await session.execute(
        select(RdDeliverableTemplate.id).where(RdDeliverableTemplate.id == template.id).with_for_update()
    )
    current_max = (
        await session.execute(
            select(func.max(RdDeliverableTemplateVersion.version_no)).where(
                RdDeliverableTemplateVersion.template_id == template.id
            )
        )
    ).scalar_one_or_none()
    version_no = int(current_max or 0) + 1

    # 旧的当前版本退位；连软删记录一并清掉，保证部分唯一索引不被占用
    await session.execute(
        update(RdDeliverableTemplateVersion)
        .where(
            RdDeliverableTemplateVersion.template_id == template.id,
            RdDeliverableTemplateVersion.is_current.is_(True),
        )
        .values(is_current=False)
        .execution_options(synchronize_session=False)
    )

    version = RdDeliverableTemplateVersion(
        template_id=template.id,
        version_no=version_no,
        file_object_key=key,
        file_name=filename[:500],
        file_ext=ext,
        file_size=size,
        template_code=template.template_code,
        template_structure=template.template_structure,
        change_note=(change_note or "").strip() or None,
        is_current=True,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(version)
    await session.flush()
    return version


async def batch_upload_templates(
    session: AsyncSession,
    uploads: list[UploadFile],
    stage: str = "",
    deliverable_type: str = "",
    user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """批量上传 Word 母本：每个文件建一条模板记录，不解析结构、不推断填充项。

    同名文件不再跳过，而是作为该模板的新版本挂载——原行为要求先删掉旧模板再传，
    会把历史版本一并丢掉，正是版本管理要解决的问题。
    """
    from sqlalchemy import select

    from app.modules.research.models import RdDeliverableTemplate

    if not uploads:
        raise BadRequestException("请选择至少一个模板文件")

    created: list[dict[str, str | int]] = []
    versioned: list[dict[str, str | int]] = []
    skipped: list[str] = []
    for upload in uploads:
        filename = (upload.filename or "").strip()
        if not filename:
            continue
        data = await upload.read()
        try:
            ext = sniff_word_ext(filename, data)
        except BadRequestException as exc:
            skipped.append(f"{filename}：{exc.detail if hasattr(exc, 'detail') else exc}")
            continue
        name = Path(filename).stem[:200]
        existing = (
            (
                await session.execute(
                    select(RdDeliverableTemplate).where(
                        RdDeliverableTemplate.name == name,
                        RdDeliverableTemplate.is_deleted.is_(False),
                    )
                )
            )
            .scalars()
            .first()
        )
        if existing is not None:
            # 同名即该模板的新版本：母本换代，旧版本留在版本表里可回滚
            await attach_template_file(session, existing, filename, data, user_id, change_note="批量上传新版本")
            current = await _current_template_version(session, existing.id)
            versioned.append(
                {
                    "id": str(existing.id),
                    "name": name,
                    "version_no": str(current.version_no if current is not None else ""),
                    "file_name": filename,
                }
            )
            continue
        # 新模板：只登记名称与业务归属，母本原样留档，不解析结构
        template = RdDeliverableTemplate(
            name=name,
            deliverable_type=(deliverable_type or "")[:50],
            stage=(stage or "")[:50],
            description=f"由 {filename} 上传",
            is_active=False,
            created_by=user_id,
        )
        session.add(template)
        await session.flush()
        await attach_template_file(session, template, filename, data, user_id)
        created.append({"id": str(template.id), "name": name, "file_ext": ext})
    return {"created": created, "versioned": versioned, "skipped": skipped}


def _template_mime(ext: str) -> str:
    """按扩展名给出下载 MIME。"""
    if ext == ".doc":
        return "application/msword"
    if ext == ".dotx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.template"
    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


async def _load_template_or_404(
    session: AsyncSession, template_id: uuid.UUID, *, for_update: bool = False
) -> Any:
    """取模板记录，不存在（或已软删）即 404。

    ``for_update=True`` 时对行加锁：槽位结构是「读-改-写」，不加锁时两个并发保存
    都能通过令牌比对，后写的会静默覆盖前一个。
    """
    from sqlalchemy import select

    from app.modules.research.models import RdDeliverableTemplate

    stmt = select(RdDeliverableTemplate).where(RdDeliverableTemplate.id == template_id)
    if for_update:
        stmt = stmt.with_for_update()
    template = (await session.execute(stmt)).scalar_one_or_none()
    if template is None or template.is_deleted:
        raise NotFoundException("模板不存在")
    return template


async def _current_template_version(session: AsyncSession, template_id: uuid.UUID) -> Any:
    """该模板当前生效的版本记录（尚未留档任何版本时返回 None）。"""
    from sqlalchemy import select

    from app.modules.research.models import RdDeliverableTemplateVersion

    return (
        (
            await session.execute(
                select(RdDeliverableTemplateVersion).where(
                    RdDeliverableTemplateVersion.template_id == template_id,
                    RdDeliverableTemplateVersion.is_current.is_(True),
                    RdDeliverableTemplateVersion.is_deleted.is_(False),
                )
            )
        )
        .scalars()
        .first()
    )


async def template_download_payload(session: AsyncSession, template_id: uuid.UUID) -> tuple[bytes, str, str]:
    """取模板「当前生效版本」的母本字节流，返回 (data, 下载文件名, MIME)。"""
    template = await _load_template_or_404(session, template_id)
    if not template.file_object_key:
        raise NotFoundException("该模板尚未上传 Word 模板原件")
    data = store.load_bytes(template.file_object_key)
    if data is None:
        raise NotFoundException("模板文件读取失败（存储不可用或文件已被清理）")
    ext = template.file_ext or ".docx"
    return data, f"{template.name}{ext}", _template_mime(ext)


async def _get_template_version(
    session: AsyncSession, template_id: uuid.UUID, version_id: uuid.UUID
) -> tuple[Any, Any]:
    """取模板 + 指定版本；不存在、已软删或不属于该模板均按 404 处理。"""
    from app.modules.research.models import RdDeliverableTemplateVersion

    template = await _load_template_or_404(session, template_id)
    version = await session.get(RdDeliverableTemplateVersion, version_id)
    if version is None or version.is_deleted or version.template_id != template.id:
        raise NotFoundException("模板版本不存在")
    return template, version


async def template_version_download_payload(
    session: AsyncSession, template_id: uuid.UUID, version_id: uuid.UUID
) -> tuple[bytes, str, str]:
    """取某个历史版本的母本字节流，返回 (data, 下载文件名, MIME)。

    文件名带版本号，避免多次下载同名文件互相覆盖。
    """
    template, version = await _get_template_version(session, template_id, version_id)
    data = store.load_bytes(version.file_object_key)
    if data is None:
        raise NotFoundException("该版本文件读取失败（存储不可用或文件已被清理）")
    ext = version.file_ext or ".docx"
    return data, f"{template.name}-v{version.version_no}{ext}", _template_mime(ext)


async def list_template_versions(session: AsyncSession, template_id: uuid.UUID) -> list[dict[str, Any]]:
    """模板的版本历史（新版本在前），带上传人姓名便于审计。"""
    from sqlalchemy import select

    from app.modules.research.models import RdDeliverableTemplateVersion
    from app.platform.identity.models import User

    template = await _load_template_or_404(session, template_id)
    rows = (
        (
            await session.execute(
                select(RdDeliverableTemplateVersion)
                .where(
                    RdDeliverableTemplateVersion.template_id == template.id,
                    RdDeliverableTemplateVersion.is_deleted.is_(False),
                )
                .order_by(RdDeliverableTemplateVersion.version_no.desc())
            )
        )
        .scalars()
        .all()
    )

    # 上传人姓名一次性批量取，避免逐行查询
    uploader_ids = {row.created_by for row in rows if row.created_by is not None}
    names: dict[uuid.UUID, str] = {}
    if uploader_ids:
        names = {
            user_id: name
            for user_id, name in (
                await session.execute(select(User.id, User.name).where(User.id.in_(uploader_ids)))
            ).all()
        }

    return [
        {
            "id": row.id,
            "version_no": row.version_no,
            "file_name": row.file_name,
            "file_ext": row.file_ext,
            "file_size": row.file_size,
            "template_code": row.template_code,
            "change_note": row.change_note,
            "is_current": row.is_current,
            "created_by": row.created_by,
            "created_by_name": names.get(row.created_by) if row.created_by is not None else None,
            "created_at": row.created_at,
        }
        for row in rows
    ]


async def restore_template_version(
    session: AsyncSession,
    template_id: uuid.UUID,
    version_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """回滚：以目标版本的内容新建 v(N+1) 并设为当前生效版本。

    历史版本本身不被改写（版本号单调递增，类似 git revert），也不复制存储对象——
    新版本复用目标版本的文件键，所以回滚不产生额外文件副本。槽位定义快照一并回填，
    避免出现「旧母本 + 新槽位」的错配。
    """
    template, version = await _get_template_version(session, template_id, version_id)
    if version.is_current:
        raise BadRequestException(f"v{version.version_no} 已是当前生效版本，无需回滚")
    # 先让主表等于目标版本，_record_template_version 才能快照到正确的槽位定义
    template.file_object_key = version.file_object_key
    template.file_name = version.file_name
    template.file_ext = version.file_ext
    template.template_code = version.template_code
    template.template_structure = version.template_structure
    template.updated_by = user_id
    new_version = await _record_template_version(
        session,
        template,
        filename=version.file_name or template.name,
        ext=version.file_ext or ".docx",
        size=version.file_size,
        key=version.file_object_key,
        change_note=f"回滚自 v{version.version_no}",
        user_id=user_id,
    )
    logger.info(
        "template version restored",
        extra={
            "template_id": str(template.id),
            "from_version": version.version_no,
            "new_version": new_version.version_no,
        },
    )
    return {
        "id": str(new_version.id),
        "template_id": str(template.id),
        "version_no": new_version.version_no,
        "from_version_no": version.version_no,
        "file_name": new_version.file_name,
        "file_ext": new_version.file_ext,
    }


async def delete_template_version(
    session: AsyncSession,
    template_id: uuid.UUID,
    version_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
) -> None:
    """软删一个历史版本。

    当前生效版本与模板的唯一版本都不能删（否则就没有可用母本了）。只软删记录、
    不删存储对象：留档的意义在于可追溯，物理删文件不可逆，风险高于收益。
    """
    from sqlalchemy import func, select

    from app.modules.research.models import RdDeliverableTemplateVersion

    template, version = await _get_template_version(session, template_id, version_id)
    if version.is_current:
        raise BadRequestException("当前生效版本不能删除；如需替换请上传新版本，或先回滚到其他版本")
    total = (
        await session.execute(
            select(func.count())
            .select_from(RdDeliverableTemplateVersion)
            .where(
                RdDeliverableTemplateVersion.template_id == template.id,
                RdDeliverableTemplateVersion.is_deleted.is_(False),
            )
        )
    ).scalar_one()
    if total <= 1:
        raise BadRequestException("这是该模板的唯一版本，不能删除")
    version.is_deleted = True
    version.updated_by = user_id
    await session.flush()


# ===== 槽位结构：AI 识别结果的人工查看与编辑 =====

# 人工新增的槽位默认锁定这几个字段：名称、标识、位置是人的判断，重解析不许覆盖
_NEW_SLOT_EDITED_FIELDS = ("anchor", "label", "slot_key")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _structure_token(structure: dict[str, Any]) -> str | None:
    """并发编辑令牌：优先用人工保存时间，没有人工痕迹时退回 AI 识别时间。"""
    return structure.get("edited_at") or structure.get("analyzed_at")


def _load_candidates(template: Any) -> list[dict[str, Any]]:
    """把当前母本扁平化成候选位置：只读文件、不调模型、不写库。"""
    from app.modules.research.report_gen.structure import (
        build_candidates,
        cell_refs,
        open_document,
        paragraph_refs,
    )

    if not template.file_object_key:
        return []
    data = store.load_bytes(template.file_object_key)
    if not data:
        raise BadRequestException("母本文件已丢失，请重新上传模板")
    document = open_document(data)
    return build_candidates(paragraph_refs(document), cell_refs(document))


def _slot_payload(slot: dict[str, Any], candidate_ids: dict[tuple[Any, ...], str]) -> dict[str, Any]:
    from app.modules.research.report_gen.structure import anchor_key

    return {
        "slot_key": slot["slot_key"],
        "label": slot["label"],
        "value_type": slot["value_type"],
        "owner_hint": slot["owner_hint"],
        "hint": slot["hint"],
        "location": slot["location"],
        "candidate_id": candidate_ids.get(anchor_key(slot["anchor"])),
        "anchor": slot["anchor"],
        "is_enabled": slot["is_enabled"],
        "origin": slot["origin"],
        "edited_fields": slot["edited_fields"],
    }


async def template_slots_payload(session: AsyncSession, template_id: uuid.UUID) -> dict[str, Any]:
    """槽位结构 + 候选位置清单。母本换过版时 ``is_stale=True``，前端据此拦截保存。"""
    from app.modules.research.report_gen.structure import (
        STRUCTURE_VERSION,
        anchor_key,
        normalize_structure,
        structure_is_stale,
    )

    template = await _load_template_or_404(session, template_id)
    if not template.file_object_key:
        raise BadRequestException("该模板还没有上传 Word 母本，无法查看槽位结构")

    structure = normalize_structure(template.template_structure)
    candidates = _load_candidates(template)
    candidate_ids = {anchor_key(item["anchor"]): item["candidate_id"] for item in candidates}
    used = {anchor_key(slot["anchor"]) for slot in structure["slots"]}

    slots = [_slot_payload(slot, candidate_ids) for slot in structure["slots"]]
    return {
        "template_id": str(template.id),
        "template_name": template.name,
        "file_name": template.file_name,
        "version": structure.get("version") or STRUCTURE_VERSION,
        "source_key": structure.get("source_key"),
        "analyzed_at": structure.get("analyzed_at"),
        "edited_at": structure.get("edited_at"),
        "token": _structure_token(structure),
        "is_stale": structure_is_stale(structure, template.file_object_key),
        "slots": slots,
        "candidates": [
            {
                "candidate_id": item["candidate_id"],
                "kind": item["kind"],
                "label": item["label"],
                "text": item["text"],
                "style": item["style"] or "",
                "context": item["context"],
                "used": anchor_key(item["anchor"]) in used,
            }
            for item in candidates
        ],
        "candidate_total": len(candidates),
        "total_count": len(slots),
        "enabled_count": sum(1 for slot in slots if slot["is_enabled"]),
    }


def _resolve_slots(raw_slots: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把前端提交的槽位对齐到真实候选位：锚点只能来自当前母本。"""
    from app.modules.research.report_gen.structure import anchor_key, normalize_slot, validate_slots

    by_id = {item["candidate_id"]: item for item in candidates}
    by_anchor = {anchor_key(item["anchor"]): item for item in candidates}

    resolved: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_slots):
        key = str(raw.get("slot_key") or "").strip() or f"第 {index + 1} 个槽位"
        candidate = None
        candidate_id = str(raw.get("candidate_id") or "").strip()
        if candidate_id:
            candidate = by_id.get(candidate_id)
        elif isinstance(raw.get("anchor"), dict):
            candidate = by_anchor.get(anchor_key(raw["anchor"]))
        if candidate is None:
            raise BadRequestException(f"{key} 绑定的位置不在当前母本中，请重新识别或换个位置")
        resolved.append(
            normalize_slot({**raw, "anchor": candidate["anchor"], "location": candidate["label"]})
        )

    validate_slots(resolved, {anchor_key(item["anchor"]) for item in candidates})
    return resolved


def _stamp_manual_edits(
    slots: list[dict[str, Any]], old_slots: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """把「这次到底改了什么」写进槽位，供下一次合并重解析判断保留范围。"""
    from app.modules.research.report_gen.structure import anchor_key, edited_fields_between

    old_by_anchor = {anchor_key(slot["anchor"]): slot for slot in old_slots}
    for slot in slots:
        old = old_by_anchor.get(anchor_key(slot["anchor"]))
        if old is None:
            slot["origin"] = "manual"
            slot["edited_fields"] = list(_NEW_SLOT_EDITED_FIELDS)
            continue
        changed = edited_fields_between(old, slot)
        # 老结构可能还没补 edited_fields / origin，按「未人工动过」处理
        merged_fields = sorted(set(old.get("edited_fields") or []) | set(changed))
        slot["edited_fields"] = merged_fields
        slot["origin"] = "manual" if merged_fields or old.get("origin") == "manual" else "ai"
    return slots


def _save_result(structure: dict[str, Any], slots: list[dict[str, Any]], token: str) -> dict[str, Any]:
    return {
        "slots": slots,
        "token": token,
        "analyzed_at": structure.get("analyzed_at"),
        "edited_at": structure.get("edited_at"),
        "total_count": len(slots),
        "enabled_count": sum(1 for slot in slots if slot["is_enabled"]),
    }


async def save_template_slots(
    session: AsyncSession,
    template_id: uuid.UUID,
    raw_slots: list[dict[str, Any]],
    token: str | None,
    user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """全量覆盖槽位结构；锚点必须属于当前母本，母本换版后禁止直接保存。"""
    from app.modules.research.report_gen.structure import (
        STRUCTURE_VERSION,
        normalize_structure,
        structure_is_stale,
    )

    template = await _load_template_or_404(session, template_id, for_update=True)
    if not template.file_object_key:
        raise BadRequestException("该模板还没有上传 Word 母本，无法保存槽位结构")

    current = normalize_structure(template.template_structure)
    if structure_is_stale(current, template.file_object_key):
        raise BadRequestException("母本已换版，请先「重新识别」槽位结构再保存，避免把旧位置写到新母本上")

    candidates = _load_candidates(template)
    if not candidates:
        raise BadRequestException("母本中没有可填写的位置，无法保存槽位结构")

    stored_token = _structure_token(current)
    if stored_token and token != stored_token:
        raise BadRequestException("槽位结构已被其他人修改，请关闭抽屉重新打开后再改")

    slots = _stamp_manual_edits(_resolve_slots(raw_slots, candidates), current["slots"])
    now = _now_iso()
    structure = {
        "version": STRUCTURE_VERSION,
        "source_key": template.file_object_key,
        "analyzed_at": current.get("analyzed_at"),
        "edited_at": now,
        "edited_by": str(user_id) if user_id else None,
        "slots": slots,
    }
    template.template_structure = structure
    template.updated_by = user_id
    await session.flush()
    logger.info(
        "template slots saved",
        extra={
            "template_id": str(template.id),
            "slot_count": len(slots),
            "enabled_count": sum(1 for slot in slots if slot["is_enabled"]),
        },
    )
    return _save_result(structure, slots, now)


async def reparse_template_slots(
    session: AsyncSession,
    template_id: uuid.UUID,
    token: str | None,
    user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """强制重解析并按锚点合并：人工改过的字段保留，AI 新识别的位置补进来。

    返回里同时带 ``ai_slots``（本次识别原始结果）与 ``slots``（合并后结果），
    差异展示只走响应，不落库。
    """
    from app.modules.research.report_gen.config import load_config
    from app.modules.research.report_gen.structure import (
        STRUCTURE_VERSION,
        ensure_structure,
        merge_slots,
        normalize_structure,
    )

    template = await _load_template_or_404(session, template_id, for_update=True)
    if not template.file_object_key:
        raise BadRequestException("该模板还没有上传 Word 母本，无法识别槽位结构")

    current = normalize_structure(template.template_structure)
    stored_token = _structure_token(current)
    if stored_token and token != stored_token:
        raise BadRequestException("槽位结构已被其他人修改，请关闭抽屉重新打开后再改")

    config = await load_config()
    fresh = await ensure_structure(session, template, config, force=True)
    ai_slots: list[dict[str, Any]] = list(fresh.get("slots") or [])
    merged, stats = merge_slots(current["slots"], ai_slots)

    now = _now_iso()
    structure = {
        "version": STRUCTURE_VERSION,
        "source_key": template.file_object_key,
        "analyzed_at": now,
        "edited_at": now,
        "edited_by": str(user_id) if user_id else None,
        "slots": merged,
    }
    # ensure_structure 刚写的是纯 AI 结果，这里用合并结果覆盖（同一 session，不额外提交）
    template.template_structure = structure
    template.updated_by = user_id
    await session.flush()
    logger.info(
        "template slots reparsed",
        extra={
            "template_id": str(template.id),
            "ai_slots": len(ai_slots),
            "merged_slots": len(merged),
            **stats,
        },
    )
    return {
        **_save_result(structure, merged, now),
        "ai_slots": ai_slots,
        "stats": stats,
    }
