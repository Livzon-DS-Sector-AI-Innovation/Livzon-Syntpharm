"""轻量页级编辑：改一个文本框的文字、换一张图片。

刻意只支持这两种操作，并且**不保证版式**：

- 文字按 run 级替换：保留首个 run 的字体/字号/颜色，其余 run 清空。
  整段替换会丢局部格式，重新排版又需要真正的排版引擎，两者都不划算。
- 图片替换走 `r:embed` 重新指向新增的 image part，保留原 left/top/width/height，
  绝不「删掉再加一个」，否则版面必然漂移。

编辑产出的是新字节流，交给 `source_replace` 走同一套对齐与重渲染链路，
因此改动只会影响真正变化的那一页。
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Any

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.parts.image import Image

logger = logging.getLogger(__name__)


class EditError(ValueError):
    """编辑失败，message 直接回给前端。"""


@dataclass(frozen=True)
class EditableShape:
    index: int
    name: str
    kind: str
    text: str
    has_picture: bool
    editable_text: bool


def _slide(prs: Any, page_index: int) -> Any:
    if page_index < 1 or page_index > len(prs.slides):
        raise EditError(f"页码超出范围：{page_index}")
    return prs.slides[page_index - 1]


def _is_picture(shape: Any) -> bool:
    """判断是否图片形状。

    python-pptx 的 `Picture` 没有 `has_picture` 属性（取不到会静默为 False），
    只能按 `shape_type` 判定。
    """
    return getattr(shape, "shape_type", None) == MSO_SHAPE_TYPE.PICTURE


def _find_shape(slide: Any, identifier: str | int) -> Any:
    if isinstance(identifier, int):
        if 0 <= identifier < len(slide.shapes):
            return slide.shapes[identifier]
        raise EditError(f"形状下标超出范围：{identifier}")
    for shape in slide.shapes:
        if shape.name == identifier:
            return shape
    raise EditError(f"未找到形状：{identifier}")


def list_editable_shapes(pptx_bytes: bytes, page_index: int) -> list[EditableShape]:
    """列出某页可编辑的形状，供前端下拉选择。"""
    prs = Presentation(io.BytesIO(pptx_bytes))
    slide = _slide(prs, page_index)
    result: list[EditableShape] = []
    for index, shape in enumerate(slide.shapes):
        editable_text = bool(getattr(shape, "has_text_frame", False) and shape.has_text_frame)
        text = shape.text_frame.text if editable_text else ""
        result.append(
            EditableShape(
                index=index,
                name=shape.name,
                kind=str(getattr(shape, "shape_type", "")),
                text=text[:200],
                has_picture=_is_picture(shape),
                editable_text=editable_text,
            )
        )
    return result


def _replace_text(shape: Any, new_text: str) -> None:
    """run 级替换：首个 run 承载全文并保留其格式，其余 run 清空。"""
    if not getattr(shape, "has_text_frame", False) or not shape.has_text_frame:
        raise EditError(f"形状「{shape.name}」不是文本框")
    paragraphs = shape.text_frame.paragraphs
    if not paragraphs:
        shape.text_frame.text = new_text
        return

    first_paragraph = paragraphs[0]
    runs = list(first_paragraph.runs)
    if runs:
        runs[0].text = new_text
        for run in runs[1:]:
            run.text = ""
    else:
        first_paragraph.text = new_text

    # 其余段落清空，避免旧内容残留在文本框下方
    for paragraph in paragraphs[1:]:
        for run in paragraph.runs:
            run.text = ""


def _is_native_image(image_bytes: bytes) -> bool:
    """python-pptx 能否直接写入该格式（BMP/GIF/JPEG/PNG/TIFF/WMF）。

    `ext` 是懒加载属性：格式不认识时抛 ValueError，内容根本不是图片时抛 OSError。
    """
    try:
        return bool(Image.from_blob(image_bytes, None).ext)
    except (OSError, ValueError):
        return False


def _image_stream(image_bytes: bytes) -> io.BytesIO:
    """把上传图片整理成 python-pptx 可写入的字节流。

    python-pptx 只认 BMP/GIF/JPEG/PNG/TIFF/WMF，webp 之类会直接抛 ValueError，
    这里先用 Pillow 转成 PNG，避免把「不支持的格式」暴露成 500。
    """
    if _is_native_image(image_bytes):
        return io.BytesIO(image_bytes)

    try:
        from PIL import Image as PILImage

        with PILImage.open(io.BytesIO(image_bytes)) as source:
            buffer = io.BytesIO()
            source.convert("RGBA").save(buffer, format="PNG")
    except (OSError, ValueError) as exc:
        raise EditError("图片无法解析，请换一张 png / jpg 图片") from exc
    buffer.seek(0)
    return buffer


def _replace_image(shape: Any, image_bytes: bytes) -> None:
    """替换图片关系而不是重建形状，位置尺寸完全不变。"""
    if not _is_picture(shape):
        raise EditError(f"形状「{shape.name}」不是图片")

    _image_part, r_id = shape.part.get_or_add_image_part(_image_stream(image_bytes))
    blip = shape._element.blipFill.blip  # noqa: SLF001 — python-pptx 未暴露公开 API
    blip.rEmbed = r_id


def apply_edit(pptx_bytes: bytes, edit: dict[str, Any]) -> bytes:
    """应用一次编辑，返回新的 pptx 字节流。

    edit 结构：
        {"page_index": 3, "shape": "标题 1", "type": "text", "text": "新文案"}
        {"page_index": 3, "shape": "图片 4", "type": "image", "image_bytes": b"..."}
    """
    edit_type = str(edit.get("type") or "").strip()
    if edit_type not in ("text", "image"):
        raise EditError("不支持的编辑类型")

    page_index = int(edit.get("page_index") or 0)
    shape_ref = edit.get("shape")
    if shape_ref is None or shape_ref == "":
        raise EditError("请选择要修改的形状")

    prs = Presentation(io.BytesIO(pptx_bytes))
    slide = _slide(prs, page_index)
    shape = _find_shape(slide, shape_ref)

    if edit_type == "text":
        text = str(edit.get("text") or "")
        _replace_text(shape, text)
    else:
        image_bytes = edit.get("image_bytes") or b""
        if not image_bytes:
            raise EditError("图片内容为空")
        _replace_image(shape, image_bytes)

    output = io.BytesIO()
    prs.save(output)
    logger.info("页级编辑完成: page=%s shape=%s type=%s", page_index, shape.name, edit_type)
    return output.getvalue()
