"""页级轻量编辑单测：形状列举、改文字、换图片、下载目标解析。

这里只跑 python-pptx 与纯函数，不碰 MinIO / LibreOffice / 模型：
编辑产出的是字节流，落库与重渲由 `source_replace` 的用例覆盖。
"""

import io
import uuid

import pytest
from PIL import Image as PILImage
from pptx import Presentation
from pptx.util import Emu, Pt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.modules.agent import editor, service
from app.modules.agent.models import PptVideoProject


def _png_bytes(color: tuple[int, int, int] = (255, 0, 0)) -> bytes:
    buffer = io.BytesIO()
    PILImage.new("RGB", (16, 16), color).save(buffer, format="PNG")
    return buffer.getvalue()


def _webp_bytes(color: tuple[int, int, int] = (0, 0, 255)) -> bytes:
    buffer = io.BytesIO()
    PILImage.new("RGB", (16, 16), color).save(buffer, format="WEBP")
    return buffer.getvalue()


def _deck_with_text_and_picture() -> bytes:
    """两页：第一页有文本框与图片，第二页只有标题。"""
    presentation = Presentation()
    layout = presentation.slide_layouts[6]  # 空白布局，形状完全由用例控制
    slide = presentation.slides.add_slide(layout)
    box = slide.shapes.add_textbox(Emu(914400), Emu(914400), Emu(4572000), Emu(914400))
    paragraph = box.text_frame.paragraphs[0]
    first = paragraph.add_run()
    first.text = "标题原文"
    first.font.size = Pt(24)
    first.font.bold = True
    second = paragraph.add_run()
    second.text = "副标题"
    second.font.size = Pt(12)

    picture = slide.shapes.add_picture(io.BytesIO(_png_bytes()), Emu(914400), Emu(2743200), width=Emu(1828800))

    second_slide = presentation.slides.add_slide(layout)
    second_slide.shapes.add_textbox(Emu(914400), Emu(914400), Emu(4572000), Emu(914400)).text_frame.text = "第二页"

    output = io.BytesIO()
    presentation.save(output)
    result = output.getvalue()
    assert picture.width == Emu(1828800)  # 形状确实加上了，避免用例在空页上跑
    return result


# ── 形状列举 ──────────────────────────────────────────────────────────────


def test_list_editable_shapes_marks_text_and_picture() -> None:
    shapes = editor.list_editable_shapes(_deck_with_text_and_picture(), 1)

    text_items = [item for item in shapes if item.editable_text]
    picture_items = [item for item in shapes if item.has_picture]
    assert len(text_items) == 1
    assert len(picture_items) == 1
    assert text_items[0].text.replace("\n", "") == "标题原文副标题"
    assert picture_items[0].text == ""


def test_list_editable_shapes_truncates_long_text() -> None:
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    slide.shapes.add_textbox(Emu(0), Emu(0), Emu(4572000), Emu(914400)).text_frame.text = "长" * 500
    output = io.BytesIO()
    presentation.save(output)

    shapes = editor.list_editable_shapes(output.getvalue(), 1)

    assert shapes[0].editable_text is True
    assert shapes[0].text == "长" * 200


def test_list_editable_shapes_rejects_out_of_range_page() -> None:
    with pytest.raises(editor.EditError, match="页码超出范围"):
        editor.list_editable_shapes(_deck_with_text_and_picture(), 9)


# ── 改文字 ────────────────────────────────────────────────────────────────


def test_apply_text_edit_keeps_first_run_format() -> None:
    original = _deck_with_text_and_picture()

    edited = editor.apply_edit(original, {"page_index": 1, "shape": 0, "type": "text", "text": "新标题"})

    presentation = Presentation(io.BytesIO(edited))
    paragraph = presentation.slides[0].shapes[0].text_frame.paragraphs[0]
    assert paragraph.runs[0].text == "新标题"
    assert paragraph.runs[0].font.size == Pt(24)
    assert paragraph.runs[0].font.bold is True
    # 其余 run 清空，避免旧文字残留在后面
    assert [run.text for run in paragraph.runs[1:]] == [""]


def test_apply_text_edit_clears_extra_paragraphs() -> None:
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    frame = slide.shapes.add_textbox(Emu(0), Emu(0), Emu(4572000), Emu(1828800)).text_frame
    frame.text = "第一段"
    frame.add_paragraph().text = "第二段"
    buffer = io.BytesIO()
    presentation.save(buffer)

    edited = editor.apply_edit(buffer.getvalue(), {"page_index": 1, "shape": 0, "type": "text", "text": "只剩一段"})

    paragraphs = Presentation(io.BytesIO(edited)).slides[0].shapes[0].text_frame.paragraphs
    assert paragraphs[0].text == "只剩一段"
    assert [paragraph.text for paragraph in paragraphs[1:]] == [""]


def test_apply_text_edit_rejects_picture_shape() -> None:
    deck = _deck_with_text_and_picture()

    with pytest.raises(editor.EditError, match="不是文本框"):
        editor.apply_edit(deck, {"page_index": 1, "shape": 1, "type": "text", "text": "改图"})


# ── 换图片 ────────────────────────────────────────────────────────────────


def test_apply_image_edit_keeps_geometry() -> None:
    deck = _deck_with_text_and_picture()
    before = Presentation(io.BytesIO(deck)).slides[0].shapes[1]
    geometry = (before.left, before.top, before.width, before.height)

    edited = editor.apply_edit(
        deck,
        {"page_index": 1, "shape": 1, "type": "image", "image_bytes": _png_bytes((0, 255, 0))},
    )

    after = Presentation(io.BytesIO(edited)).slides[0].shapes[1]
    assert (after.left, after.top, after.width, after.height) == geometry
    assert after.image.blob != before.image.blob
    assert after.image.content_type == "image/png"


def test_apply_image_edit_converts_webp_to_png() -> None:
    deck = _deck_with_text_and_picture()

    edited = editor.apply_edit(
        deck,
        {"page_index": 1, "shape": 1, "type": "image", "image_bytes": _webp_bytes()},
    )

    image = Presentation(io.BytesIO(edited)).slides[0].shapes[1].image
    # python-pptx 只认 BMP/GIF/JPEG/PNG/TIFF/WMF，webp 必须转码后再写入
    assert image.content_type == "image/png"


def test_apply_image_edit_rejects_text_shape() -> None:
    with pytest.raises(editor.EditError, match="不是图片"):
        editor.apply_edit(
            _deck_with_text_and_picture(),
            {"page_index": 1, "shape": 0, "type": "image", "image_bytes": _png_bytes()},
        )


def test_apply_image_edit_rejects_empty_payload() -> None:
    with pytest.raises(editor.EditError, match="图片内容为空"):
        editor.apply_edit(
            _deck_with_text_and_picture(),
            {"page_index": 1, "shape": 1, "type": "image", "image_bytes": b""},
        )


def test_apply_image_edit_rejects_unparsable_bytes() -> None:
    with pytest.raises(editor.EditError, match="图片无法解析"):
        editor.apply_edit(
            _deck_with_text_and_picture(),
            {"page_index": 1, "shape": 1, "type": "image", "image_bytes": b"not an image"},
        )


# ── 入参校验 ──────────────────────────────────────────────────────────────


def test_apply_edit_rejects_unknown_type() -> None:
    with pytest.raises(editor.EditError, match="不支持的编辑类型"):
        editor.apply_edit(_deck_with_text_and_picture(), {"page_index": 1, "shape": 0, "type": "delete"})


def test_apply_edit_rejects_missing_shape_reference() -> None:
    with pytest.raises(editor.EditError, match="请选择要修改的形状"):
        editor.apply_edit(_deck_with_text_and_picture(), {"page_index": 1, "type": "text", "text": "x"})


def test_apply_edit_rejects_unknown_shape_name() -> None:
    with pytest.raises(editor.EditError, match="未找到形状"):
        editor.apply_edit(
            _deck_with_text_and_picture(),
            {"page_index": 1, "shape": "不存在的形状", "type": "text", "text": "x"},
        )


def test_apply_edit_rejects_shape_index_out_of_range() -> None:
    with pytest.raises(editor.EditError, match="形状下标超出范围"):
        editor.apply_edit(_deck_with_text_and_picture(), {"page_index": 1, "shape": 99, "type": "text", "text": "x"})


# ── 源 PPT 下载目标 ───────────────────────────────────────────────────────


async def _make_project(session: AsyncSession, *, source_version: int = 1, name: str | None = None) -> PptVideoProject:
    project = PptVideoProject(
        id=uuid.uuid4(),
        name=name or f"下载测试-{uuid.uuid4().hex[:6]}",
        source_object_key=f"ppt-video/{uuid.uuid4()}/source-v{source_version}.pptx",
        source_filename="原始文件名 含空格.pptx",
        source_sha256=uuid.uuid4().hex * 2,
        slide_count=1,
        default_language="zh",
        default_voice_id="zf_001",
        speed=1.0,
        source_version=source_version,
    )
    session.add(project)
    await session.flush()
    return project


async def test_source_download_target_uses_project_name_and_version(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = await _make_project(db_session, source_version=3)
    monkeypatch.setattr(storage, "stat_object", lambda _module, _key: 2048)

    object_key, file_name = await service.source_download_target(db_session, project.id)

    assert object_key == project.source_object_key
    # 文件名只用项目名与版本号，不带上用户上传的原始文件名
    assert file_name == f"{project.name}-v3.pptx"


async def test_source_download_target_strips_path_separators_from_name(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = await _make_project(db_session, name='研发/季报 "终稿"\n')
    monkeypatch.setattr(storage, "stat_object", lambda _module, _key: 2048)

    _object_key, file_name = await service.source_download_target(db_session, project.id)

    # 斜杠会变成目录、换行会截断响应头，都必须替换掉
    assert "/" not in file_name
    assert "\n" not in file_name
    assert file_name == "研发_季报 _终稿_-v1.pptx"


async def test_source_download_target_reports_missing_object(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = await _make_project(db_session)
    monkeypatch.setattr(storage, "stat_object", lambda _module, _key: None)

    with pytest.raises(service.NotFoundError, match="源 PPT 已丢失"):
        await service.source_download_target(db_session, project.id)
