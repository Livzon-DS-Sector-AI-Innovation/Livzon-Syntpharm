"""交付物模板文件的存储：MinIO 优先，未启用时落本地 UPLOAD_DIR。"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from app.core import storage
from app.core.config import get_settings

logger = logging.getLogger(__name__)

MODULE = "research"
# 沿用 doc-gen 前缀：存量模板的 file_object_key 都是按此前缀写入的，
# 改名会让所有历史版本的文件指向失效。
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


def load_bytes(key: str) -> bytes | None:
    """按键读取字节流。"""
    if key.startswith("local:"):
        path = Path(get_settings().UPLOAD_DIR) / key[len("local:") :]
        return path.read_bytes() if path.exists() else None
    if not storage.is_enabled():
        return None
    result = storage.get_object(MODULE, key)
    return result[0] if result else None


__all__ = ["MODULE", "load_bytes", "save_bytes"]
