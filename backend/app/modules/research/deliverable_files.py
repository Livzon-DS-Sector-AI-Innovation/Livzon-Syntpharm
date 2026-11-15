"""阶段交付文档附件的落盘与定位。

上传、下载原先散在 ``api.py`` 里；AI 生成完成后也要把 docx 写进同一个目录，
抽出来给 ``api.py`` 与 ``deliverable_generation.py`` 共用，避免服务层反向 import api。

文件名规则与历史一致：``{deliverable_id}_{原始文件名}``。所有写入前都对文件名
做 ``os.path.basename``，防止调用方带 ``../`` 把文件写到目录外。
"""

from __future__ import annotations

import logging
import os
from uuid import UUID

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 交付物附件目录：由配置派生，不再硬编码 /tmp（容器重启即丢）。
_DELIVERABLE_SUBDIR: tuple[str, ...] = ("research", "deliverables")


def deliverable_upload_dir() -> str:
    """交付物附件的落盘目录（UPLOAD_DIR/research/deliverables）。"""
    return os.path.join(get_settings().UPLOAD_DIR, *_DELIVERABLE_SUBDIR)


def legacy_deliverable_dir() -> str | None:
    """历史版本附件目录（LEGACY_UPLOAD_DIR/research/deliverables），未配置则不兜底。"""
    legacy_root = get_settings().LEGACY_UPLOAD_DIR
    return os.path.join(legacy_root, *_DELIVERABLE_SUBDIR) if legacy_root else None


def safe_file_name(file_name: str) -> str:
    """只保留文件名本身，挡掉目录穿越与空名。"""
    name = os.path.basename(file_name or "").strip()
    return name or "attachment"


def stored_file_name(deliverable_id: UUID, file_name: str) -> str:
    """落盘用的文件名：``{deliverable_id}_{原始文件名}``。"""
    return f"{deliverable_id}_{safe_file_name(file_name)}"


def deliverable_download_url(deliverable_id: UUID) -> str:
    """交付物附件的下载地址（后端代理，浏览器不直连存储）。"""
    return f"/api/v1/research/rd-stage-deliverables/{deliverable_id}/download"


def save_deliverable_bytes(deliverable_id: UUID, file_name: str, data: bytes) -> int:
    """把字节写进交付物附件目录，返回字节数。

    同名文件直接覆盖：同一条交付文档重新生成时应当替换掉旧附件，
    历史版本由「新建一条交付文档记录」承载，不靠磁盘上堆同名文件。
    """
    target_dir = deliverable_upload_dir()
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, stored_file_name(deliverable_id, file_name))
    with open(file_path, "wb") as handle:
        handle.write(data)
    return len(data)


def resolve_deliverable_path(deliverable_id: UUID, file_name: str) -> str | None:
    """按交付文档找已落盘的附件；找不到时回落到历史目录。"""
    stored = stored_file_name(deliverable_id, file_name)
    file_path = os.path.join(deliverable_upload_dir(), stored)
    if os.path.exists(file_path):
        return file_path
    legacy_dir = legacy_deliverable_dir()
    if legacy_dir:
        legacy_path = os.path.join(legacy_dir, stored)
        if os.path.exists(legacy_path):
            return legacy_path
    return None
