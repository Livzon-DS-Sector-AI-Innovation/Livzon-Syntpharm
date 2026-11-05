"""图片压缩工具。

上传图片过大时等比压缩，优先保持清晰度：只有长边或体积超出阈值才重编码，
未超限的图片原样返回，不做任何有损处理。解码失败一律回退原图，绝不阻断上传。
"""

from __future__ import annotations

import io
import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage

logger = logging.getLogger(__name__)

# 长边上限：2560px 保留足够细节，4K 屏查看原图也不明显发虚
MAX_EDGE = 2560
# 体积阈值：低于该值且尺寸不超限则完全不处理（零重编码）
MAX_BYTES = 2 * 1024 * 1024
# JPEG 质量阶梯：起手 90 保清晰度，体积超标才逐级下调
QUALITY_STEPS = (90, 85, 80, 74)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
IMAGE_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/bmp"}
# 动图/矢量图跳过重编码（会丢失动画或矢量信息）
SKIP_EXTENSIONS = {".gif", ".svg"}


def _is_image(filename: str | None, content_type: str | None) -> bool:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext in SKIP_EXTENSIONS:
        return False
    return ext in IMAGE_EXTENSIONS or (content_type or "").lower() in IMAGE_CONTENT_TYPES


def _has_alpha(img: PILImage) -> bool:
    if img.mode in ("RGBA", "LA"):
        return True
    return img.mode == "P" and "transparency" in img.info


def _encode_jpeg(img: PILImage) -> tuple[bytes, int]:
    """按质量阶梯编码 JPEG，返回 (data, quality)。"""

    data = b""
    used = QUALITY_STEPS[-1]
    for quality in QUALITY_STEPS:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
        data = buf.getvalue()
        used = quality
        if len(data) <= MAX_BYTES:
            break
    return data, used


def _encode_png(img: PILImage) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def compress_image(
    content: bytes,
    filename: str | None = None,
    content_type: str | None = None,
) -> tuple[bytes, str, str]:
    """压缩过大图片。

    Args:
        content: 原始字节
        filename: 原始文件名（用于判断扩展名）
        content_type: 原始 MIME

    Returns:
        (data, ext, content_type)：无需压缩或压缩失败时原样返回；
        压缩后扩展名可能由 png/webp 变为 .jpg
    """
    ext = os.path.splitext(filename or "")[1].lower() or ".jpg"
    fallback_type = content_type or "application/octet-stream"

    if not content or not _is_image(filename, content_type):
        return content, ext, fallback_type

    try:
        from PIL import Image, ImageOps

        with Image.open(io.BytesIO(content)) as probe:
            width, height = probe.size
            frames = getattr(probe, "n_frames", 1)

        # 多帧图（GIF/APNG）不重编码，避免丢帧
        if frames > 1:
            return content, ext, fallback_type

        if max(width, height) <= MAX_EDGE and len(content) <= MAX_BYTES:
            return content, ext, fallback_type

        with Image.open(io.BytesIO(content)) as src:
            img = ImageOps.exif_transpose(src)
            if max(img.size) > MAX_EDGE:
                img.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
            new_size = img.size

            if _has_alpha(img):
                rgba = img.convert("RGBA")
                data = _encode_png(rgba)
                out_ext, out_type = ".png", "image/png"
                if len(data) > MAX_BYTES:
                    # PNG 体积不可控时降级为白底 JPEG（业务图片基本无透明需求）
                    flat = Image.new("RGB", rgba.size, (255, 255, 255))
                    flat.paste(rgba, mask=rgba.split()[-1])
                    data, _quality = _encode_jpeg(flat)
                    out_ext, out_type = ".jpg", "image/jpeg"
            else:
                data, _quality = _encode_jpeg(img.convert("RGB"))
                out_ext, out_type = ".jpg", "image/jpeg"

        if len(data) >= len(content):
            logger.info("图片压缩未减小体积，保留原图: %s %dx%d %dB", filename, width, height, len(content))
            return content, ext, fallback_type

        logger.info(
            "图片已压缩: %s %dx%d %.2fMB -> %dx%d %.2fMB (%s)",
            filename,
            width,
            height,
            len(content) / 1024 / 1024,
            new_size[0],
            new_size[1],
            len(data) / 1024 / 1024,
            out_type,
        )
        return data, out_ext, out_type
    except Exception:
        logger.warning("图片压缩失败，使用原始文件: %s", filename, exc_info=True)
        return content, ext, fallback_type


__all__ = ["compress_image", "MAX_EDGE", "MAX_BYTES"]
