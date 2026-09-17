"""产物与资料的存储：MinIO 优先，未启用时落本地 UPLOAD_DIR。"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from app.core import storage
from app.core.config import get_settings

logger = logging.getLogger(__name__)

MODULE = "research"
PREFIX = "doc-gen"


def save_bytes(name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """保存字节流，返回可用于 load_bytes 的键。"""
    key = f"{PREFIX}/{uuid.uuid4().hex}/{name}"
    if storage.is_enabled():
        try:
            return storage.upload_object(MODULE, key, data, len(data), content_type)
        except Exception:  # noqa: BLE001 - 存储不可用时退回本地，保证开发环境可用
            logger.exception("MinIO 上传失败，退回本地存储")
    target = Path(get_settings().UPLOAD_DIR) / key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return f"local:{key}"


def load_master(asset_name: str) -> bytes | None:
    """读取模板母本：优先 MinIO（可运营替换），否则用仓库内置 assets。

    `asset_name` 为空（自动识别出来的规格没有内置母本）时直接返回 None，
    否则 `TEMPLATE_DIR / ""` 会命中目录并在 read_bytes 时抛 IsADirectoryError。
    """
    if not asset_name:
        return None
    key = f"{PREFIX}/masters/{asset_name}"
    if storage.is_enabled():
        result = storage.get_object(MODULE, key)
        if result:
            return result[0]
    from app.modules.research.doc_gen.template_spec import TEMPLATE_DIR

    path = TEMPLATE_DIR / asset_name
    return path.read_bytes() if path.is_file() else None


def load_bytes(key: str) -> bytes | None:
    """按键读取字节流。"""
    if key.startswith("local:"):
        path = Path(get_settings().UPLOAD_DIR) / key[len("local:") :]
        return path.read_bytes() if path.exists() else None
    if not storage.is_enabled():
        return None
    result = storage.get_object(MODULE, key)
    return result[0] if result else None


__all__ = ["MODULE", "load_bytes", "load_master", "load_master_by_code", "load_master_by_id", "save_bytes"]


async def load_master_by_id(template_id: str | None) -> bytes | None:
    """按交付物模板主键取母本。

    必须按 id 而不是 template_code 取：同一个槽位定义下可以有多份母本，
    按 code 取会让「选 A 模板、渲染用 B 母本」这种错乱成为可能。
    """
    if not template_id:
        return None
    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.modules.research.models import RdDeliverableTemplate

    async with async_session_factory() as session:
        row = (
            await session.execute(
                select(RdDeliverableTemplate).where(
                    RdDeliverableTemplate.id == template_id,
                    RdDeliverableTemplate.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if row is None or not row.file_object_key:
            return None
        return load_bytes(row.file_object_key)


async def load_master_by_code(template_code: str) -> bytes | None:
    """按槽位定义取最近一份母本（仅用于没有显式模板 id 的历史任务）。"""
    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.modules.research.models import RdDeliverableTemplate

    async with async_session_factory() as session:
        row = (
            await session.execute(
                select(RdDeliverableTemplate)
                .where(
                    RdDeliverableTemplate.template_code == template_code,
                    RdDeliverableTemplate.is_active.is_(True),
                    ~RdDeliverableTemplate.is_deleted,
                    RdDeliverableTemplate.file_object_key.isnot(None),
                )
                .order_by(RdDeliverableTemplate.created_at.desc())
                .limit(1)
            )
        ).scalars().first()
        if row is None or not row.file_object_key:
            return None
        return load_bytes(row.file_object_key)
