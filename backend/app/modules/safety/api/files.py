# mypy: ignore-errors
"""File proxy endpoints — MinIO / local dual-mode file serving.

All file access through this proxy; browsers never connect to MinIO directly.
Supports backward compatibility with legacy local paths (uploads/safety/...).
"""

import logging
import os
import urllib.parse
from io import BytesIO
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import RequiredUser
from app.core.exceptions import AppException
from app.core.storage import get_object
from app.core.storage import is_enabled as minio_enabled

logger = logging.getLogger(__name__)

files_router = APIRouter()

# ── MIME type mapping (extension -> content-type) ──
_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".svg": "image/svg+xml",
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
    ".json": "application/json",
    ".zip": "application/zip",
}


def _guess_content_type(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    return _MIME_TYPES.get(ext, "application/octet-stream")


def _allowed_upload_roots() -> list[str]:
    """Absolute directories that the file proxy is allowed to read from."""
    settings = get_settings()
    roots: list[str] = []
    for raw in (settings.UPLOAD_DIR, settings.LEGACY_UPLOAD_DIR):
        if not raw:
            continue
        root = os.path.realpath(os.path.abspath(raw))
        # 根目录 / 盘符根不能当白名单，否则等于放开整个文件系统
        if os.path.dirname(root) == root:
            continue
        if root not in roots:
            roots.append(root)
    return roots


def _within_upload_roots(candidate: str) -> str | None:
    """Return the real path when it stays inside an upload root, else None.

    ``realpath`` 先解析符号链接与 ``..``，再与白名单根做 commonpath 比较，
    因此 ``/etc/passwd``、``../../.env``、软链逃逸都会被判为越界。
    """
    try:
        real = os.path.realpath(candidate)
    except (OSError, ValueError):
        return None
    for root in _allowed_upload_roots():
        try:
            if os.path.commonpath([real, root]) == root:
                return real
        except ValueError:  # 跨盘符（Windows）无法比较
            continue
    return None


def _resolve_local_path(file_path: str) -> str | None:
    """Resolve a stored file path to a local path inside an upload root.

    Handles three storage conventions:
      1. Clean relative paths (new): ``safety/hazard/file.jpg``
         → ``{uploads}/safety/hazard/file.jpg``
      2. Legacy prefix paths (old): ``uploads/safety/hazard/file.jpg``
         → ``{uploads}/safety/hazard/file.jpg`` (via stripping the prefix)
      3. Paths already anchored at cwd or absolute legacy paths
         → kept only when they resolve inside an upload root

    所有候选路径都必须落在 ``UPLOAD_DIR`` / ``LEGACY_UPLOAD_DIR`` 之内，
    否则返回 ``None``（对外表现为 404），避免通过 ``{file_path:path}``
    读取任意文件（如 ``.env``、``/etc/passwd``）。
    """
    if not file_path or "\x00" in file_path:
        return None

    uploads_base = os.path.abspath(get_settings().UPLOAD_DIR)

    # 1. Try joining with uploads base (handles clean paths + legacy prefix paths)
    #    If path starts with "uploads/", strip it to avoid double prefix:
    #      uploads/safety/hazard/f.jpg  →  safety/hazard/f.jpg  →  OK
    #      safety/hazard/f.jpg          →  safety/hazard/f.jpg  →  OK
    if file_path.startswith("uploads/"):
        relative = file_path[len("uploads/") :]
    elif file_path.startswith("uploads\\"):
        relative = file_path[len("uploads\\") :]
    else:
        relative = file_path
    candidate = os.path.normpath(os.path.join(uploads_base, relative))
    if os.path.isfile(candidate):
        resolved = _within_upload_roots(candidate)
        if resolved:
            return resolved

    # 2. Try the path directly (handles absolute legacy paths)
    if os.path.isabs(file_path) and os.path.isfile(file_path):
        resolved = _within_upload_roots(file_path)
        if resolved:
            return resolved

    # 3. Try relative to cwd directly (for paths already anchored at cwd)
    candidate = os.path.normpath(os.path.join(os.path.abspath("."), file_path))
    if os.path.isfile(candidate):
        return _within_upload_roots(candidate)

    return None


@files_router.get(
    "/files/{file_path:path}",
    summary="代理文件访问（MinIO / 本地双模式）",
    description="通过 object_key 或本地路径返回文件内容。支持向后兼容旧路径。",
)
async def handler(
    current_user: RequiredUser,
    file_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """Serve a file from MinIO or local disk. Supports legacy paths."""

    # URL-decode in case the client encoded special characters (e.g. %2F from
    # encodeURIComponent). In most cases this is a no-op on already-decoded paths.
    file_path = urllib.parse.unquote(file_path)

    content_type = _guess_content_type(file_path)

    if minio_enabled():
        # ── MinIO mode: try object_key first ──
        result = get_object("safety", file_path)
        if result is not None:
            data, ct = result
            return StreamingResponse(
                BytesIO(data),
                media_type=ct or content_type,
            )
        # ── Fallback: try local paths (MinIO can be unreachable) ──
        local_path = _resolve_local_path(file_path)
        if local_path:
            return FileResponse(local_path, media_type=content_type)
        raise AppException(status_code=404, message="File not found")

    # ── Local mode ──
    local_path = _resolve_local_path(file_path)
    if local_path:
        return FileResponse(local_path, media_type=content_type)

    raise AppException(status_code=404, message="File not found")
