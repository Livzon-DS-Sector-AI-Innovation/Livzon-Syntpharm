"""MinIO / S3-compatible object storage service — 模块级 bucket 隔离。

每个模块拥有独立 bucket：{MINIO_BUCKET_PREFIX}-{module}，例如：
    dazah-equipment、dazah-production、dazah-quality。

所有文件访问通过后端代理，浏览器不需要直连 MinIO——只需一个端点。

Usage:
    from app.core.storage import upload_object, get_object, delete_object, is_enabled

    if is_enabled():
        upload_object("equipment", "inspection/abc.jpg", data, len(data), "image/jpeg")
        data, ct = get_object("equipment", "inspection/abc.jpg")
        delete_object("equipment", "inspection/abc.jpg")
"""

from __future__ import annotations

import logging
from io import BytesIO
from typing import TYPE_CHECKING

from fastapi import UploadFile

if TYPE_CHECKING:
    from minio import Minio

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client: Minio | None = None
_enabled: bool | None = None
_known_buckets: set[str] = set()


def _init() -> None:
    global _client, _enabled
    if _enabled is not None:
        return
    settings = get_settings()
    _enabled = settings.MINIO_ENABLED
    if _enabled:
        from minio import Minio

        _client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )


def _get_client() -> Minio | None:
    _init()
    return _client if _enabled else None


def _module_bucket(module: str) -> str:
    return f"{get_settings().MINIO_BUCKET_PREFIX}-{module}"


def _ensure_bucket(module: str) -> None:
    client = _get_client()
    if client is None:
        return
    bucket = _module_bucket(module)
    if bucket in _known_buckets:
        return
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info("Created MinIO bucket: %s", bucket)
        _known_buckets.add(bucket)
    except Exception:
        logger.exception("Failed to ensure MinIO bucket: %s", bucket)


def upload_object(
    module: str,
    object_key: str,
    data: bytes,
    length: int,
    content_type: str = "application/octet-stream",
) -> str:
    """上传对象，返回 object_key。"""
    client = _get_client()
    if client is None:
        raise RuntimeError("MinIO is not enabled")
    _ensure_bucket(module)
    client.put_object(
        bucket_name=_module_bucket(module),
        object_name=object_key,
        data=BytesIO(data),
        length=length,
        content_type=content_type,
    )
    return object_key


def get_object(module: str, object_key: str) -> tuple[bytes, str] | None:
    """读取对象，返回 (data, content_type)；不存在返回 None。"""
    client = _get_client()
    if client is None:
        return None
    from minio.error import S3Error

    try:
        resp = client.get_object(
            bucket_name=_module_bucket(module),
            object_name=object_key,
        )
        data = resp.read()
        ct = resp.getheader("Content-Type") or "application/octet-stream"
        resp.close()
        resp.release_conn()
        return data, ct
    except S3Error:
        return None


def delete_object(module: str, object_key: str) -> None:
    """删除对象。"""
    client = _get_client()
    if client is None:
        raise RuntimeError("MinIO is not enabled")
    client.remove_object(
        bucket_name=_module_bucket(module),
        object_name=object_key,
    )


def is_enabled() -> bool:
    _init()
    return _enabled or False


async def save_upload_file(file: UploadFile, sub_dir: str = "reagent-labels") -> str:
    """保存单个上传文件到本地存储

    Args:
        file: 上传的文件
        sub_dir: 子目录名称

    Returns:
        文件访问 URL 路径
    """
    import os
    import uuid as _uuid

    content = await file.read()
    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    filename = f"{_uuid.uuid4()}{ext}"
    dir_path = os.path.join("uploads", sub_dir)
    os.makedirs(dir_path, exist_ok=True)
    file_path = os.path.join(dir_path, filename)
    with open(file_path, "wb") as f:
        f.write(content)
    return f"/uploads/{sub_dir}/{filename}"


async def save_upload_files(files: list[UploadFile], sub_dir: str = "reagent-labels") -> list[str]:
    """保存多个上传的文件

    Args:
        files: 上传的文件列表
        sub_dir: 子目录名称

    Returns:
        文件访问 URL 路径列表
    """
    urls = []
    for file in files:
        try:
            url = await save_upload_file(file, sub_dir)
            urls.append(url)
        except Exception as e:
            # 继续处理其他文件，记录错误
            print(f"保存文件 {file.filename} 失败: {e}")
            continue

    return urls


def delete_upload_file(file_url: str) -> bool:
    """删除上传的文件

    Args:
        file_url: 文件访问 URL 路径

    Returns:
        是否删除成功
    """
    try:
        # 将 URL 路径转换为实际文件路径
        if file_url.startswith("/uploads/"):
            file_path = file_url[9:]  # 去掉 "/uploads/"
        else:
            file_path = file_url

        # 删除文件
        import os

        full_path = os.path.join("uploads", file_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False
    except Exception as e:
        print(f"删除文件失败: {e}")
        return False
