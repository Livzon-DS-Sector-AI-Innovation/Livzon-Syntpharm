"""交付物模板服务层：Word 母本的上传留档、版本历史、下载与回滚。

模板在这里只是一份带版本历史的 Word 原件：上传不解析结构、不推断填充项、不生成示例稿。
填充项识别下线后，「槽位读写 / 预览 / 重解析」相关实现一并移除；母本里写哪里，由生成时
的智能体读母本自己决定（见 ``report_gen/outline.py``）。
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

# 版本类型：母本留档。历史数据里还有 ``sample``（填充示例稿）类型的行，
# 展示与回滚判定要认得它——不能因为新代码不再生成就当成未知类型报错。
VERSION_KIND_TEMPLATE = "template"
VERSION_KIND_SAMPLE = "sample"


def sniff_word_ext(filename: str, data: bytes) -> str:
    """校验文件内容与扩展名一致，返回规范化扩展名。

    只看扩展名会让改后缀的垃圾文件进库，直到渲染阶段才以 anchor_unresolved 暴露，
    排查成本极高，因此在入口处用文件头判断真实格式。
    """
    ext = Path(filename).suffix.lower()
    if ext not in WORD_EXTENSIONS:
        raise BadRequestException(
            f"这个文件不是 Word 文档（{ext or '未知格式'}）。请上传 {'、'.join(sorted(WORD_EXTENSIONS))} 格式的文件"
        )
    if not data:
        raise BadRequestException(f"这个文件是空的：{filename}，请换一个文件再上传")
    if len(data) > MAX_TEMPLATE_BYTES:
        raise BadRequestException(
            f"这个文件太大了：{filename}（上限 {MAX_TEMPLATE_BYTES // 1024 // 1024}MB），请压缩后再上传"
        )
    head = data[:8]
    if ext in {".docx", ".dotx"} and not head.startswith(_ZIP_MAGIC):
        raise BadRequestException(
            f"这个文件打不开：{filename} 只是改了后缀名，内容不是 Word 文档。请在 Word 里另存为 .docx 再上传"
        )
    if ext == ".doc" and not head.startswith(_OLE_MAGIC):
        raise BadRequestException(
            f"这个文件打不开：{filename} 只是改了后缀名，内容不是 Word 97-2003 文档。"
            "请在 Word 里另存为 .doc 或 .docx 再上传"
        )
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
    kind: str = VERSION_KIND_TEMPLATE,
    make_current: bool = True,
) -> Any:
    """把一份文件留档为模板的新版本。

    版本号在模板行锁内取 ``max(version_no) + 1``：并发上传同一模板不会算出同一个号，
    ``UniqueConstraint(template_id, version_no)`` 是最后一道保险。软删的版本仍占号，
    因此版本号单调递增、永不复用。

    ``make_current=False`` 用于填充示例稿（``kind='sample'``）：只占号留档，
    不把正在使用的母本版本挤下去，也不参与部分唯一索引。此时调用方必须自行保证
    不修改模板主表的文件指向。
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

    if make_current:
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
        kind=kind,
        is_current=make_current,
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
        raise BadRequestException("还没有选择文件，请先选择要上传的 Word 文档")

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


async def _load_template_or_404(session: AsyncSession, template_id: uuid.UUID, *, for_update: bool = False) -> Any:
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
        raise NotFoundException("模板")
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
        raise BadRequestException("这个模板还没有上传 Word 文件，请先上传")
    data = store.load_bytes(template.file_object_key)
    if data is None:
        raise BadRequestException("打不开这个 Word 文件，可能已被清理，请重新上传")
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
        raise NotFoundException("历史版本")
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
        raise BadRequestException("打不开这个历史版本的文件，可能已被清理")
    ext = version.file_ext or ".docx"
    if getattr(version, "kind", VERSION_KIND_TEMPLATE) == VERSION_KIND_SAMPLE:
        return data, f"{template.name}-填充示例-v{version.version_no}{ext}", _template_mime(ext)
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
            "kind": row.kind,
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
    新版本复用目标版本的文件键，所以回滚不产生额外文件副本。模板级填写要求快照一并
    回填，避免出现「旧母本 + 新要求」的错配。
    """
    template, version = await _get_template_version(session, template_id, version_id)
    if version.kind == VERSION_KIND_SAMPLE:
        raise BadRequestException(
            "这是填充示例稿，不是模板文件，不能恢复成当前版本。它只用于对照填写位置，用完可以删掉"
        )
    if version.is_current:
        raise BadRequestException(f"v{version.version_no} 就是正在使用的版本，不用再恢复")
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
        raise BadRequestException("正在使用的版本不能删除。要换掉它，请上传一个新版本；或先恢复别的版本，再删这一个")
    total = (
        await session.execute(
            select(func.count())
            .select_from(RdDeliverableTemplateVersion)
            .where(
                RdDeliverableTemplateVersion.template_id == template.id,
                # 只数母本版本：历史示例稿再多也不该让「唯一母本不能删」的判定失效
                RdDeliverableTemplateVersion.kind == VERSION_KIND_TEMPLATE,
                RdDeliverableTemplateVersion.is_deleted.is_(False),
            )
        )
    ).scalar_one()
    # 历史示例稿不是母本，删它不会让模板失去可用文件，不受「唯一版本」限制
    if version.kind == VERSION_KIND_TEMPLATE and total <= 1:
        raise BadRequestException("这是这个模板唯一的一份文件，删掉就没有可用的模板了，不能删除")
    version.is_deleted = True
    version.updated_by = user_id
    await session.flush()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
