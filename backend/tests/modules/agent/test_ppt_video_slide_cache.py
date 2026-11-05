"""保存页配置必须让该页片段缓存失效（「保存即生效」）。

守的是踩过的坑：页内高亮配置改完保存成功，成片却没变——
片段 key 里的视觉指纹一旦漏项（或渲染器换了实现），旧片段会被原样复用。
所以保存画面相关配置必须显式作废这页的片段；只改讲稿则不用动画面缓存。

依赖真实数据库（要验证行真的被删掉），跑之前先 `alembic upgrade head`。
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agent import highlight, service
from app.modules.agent.models import PptVideoProject, PptVideoSegment, PptVideoSlide

_IMAGE_SHA = "a" * 64


def _layout() -> dict[str, Any]:
    return {
        "width": 12192000,
        "height": 6858000,
        "shapes": [
            {
                "name": "title",
                "kind": "text",
                "text": "季度汇报",
                "left": 600000,
                "top": 400000,
                "width": 4000000,
                "height": 600000,
            },
            {
                "name": "body",
                "kind": "text",
                "text": "原料药注册申报节点",
                "left": 600000,
                "top": 1200000,
                "width": 8000000,
                "height": 3000000,
            },
        ],
    }


async def _make_page(session: AsyncSession) -> tuple[PptVideoProject, PptVideoSlide]:
    project = PptVideoProject(
        id=uuid.uuid4(),
        name=f"保存即生效-{uuid.uuid4().hex[:6]}",
        source_object_key=f"agent/ppt-video/source/{uuid.uuid4().hex}.pptx",
        source_filename="deck.pptx",
        source_sha256=uuid.uuid4().hex * 2,
        slide_count=1,
        default_language="zh",
        default_voice_id="zf_001",
        speed=1.0,
    )
    session.add(project)
    await session.flush()
    slide = PptVideoSlide(
        id=uuid.uuid4(),
        project_id=project.id,
        slide_no=1,
        script_text="原料药注册申报节点。",
        image_sha256=_IMAGE_SHA,
        layout=_layout(),
    )
    session.add(slide)
    await session.flush()
    return project, slide


def _add_segment(session: AsyncSession, segment_key: str) -> None:
    session.add(
        PptVideoSegment(
            id=uuid.uuid4(),
            segment_key=segment_key,
            image_sha256=_IMAGE_SHA,
            audio_sha256="b" * 64,
            encoder_key="v2-test",
            duration_ms=1000,
            object_key=f"ppt-video/segments/{segment_key}.mp4",
            file_size=1024,
        )
    )


async def _segments(session: AsyncSession) -> list[PptVideoSegment]:
    result = await session.scalars(select(PptVideoSegment).where(PptVideoSegment.image_sha256 == _IMAGE_SHA))
    return list(result.all())


async def _save(
    session: AsyncSession,
    project: PptVideoProject,
    slide: PptVideoSlide,
    **overrides: Any,
) -> None:
    payload: dict[str, Any] = {
        "script_text": None,
        "language": None,
        "voice_id": None,
        "speed": None,
        "clear_language": False,
        "clear_voice": False,
        "clear_speed": False,
        "updated_by": None,
    }
    payload.update(overrides)
    await service.update_slide(session, project.id, str(slide.slide_uid), **payload)


async def test_saving_highlight_color_drops_page_segments(db_session: AsyncSession) -> None:
    project, slide = await _make_page(db_session)
    _add_segment(db_session, "seg-before-1")
    _add_segment(db_session, "seg-before-2")
    await db_session.flush()
    assert len(await _segments(db_session)) == 2

    await _save(db_session, project, slide, highlight_color="#FF3B30")

    assert await _segments(db_session) == []


async def test_saving_highlight_regions_drops_page_segments(db_session: AsyncSession) -> None:
    project, slide = await _make_page(db_session)
    _add_segment(db_session, "seg-before")
    await db_session.flush()
    element_id = next(iter(highlight.element_index(_layout())))

    await _save(
        db_session,
        project,
        slide,
        highlight_regions={"regions": [{"id": element_id, "mode": "text"}], "sentences": []},
    )

    assert await _segments(db_session) == []


async def test_script_only_save_keeps_page_segments(db_session: AsyncSession) -> None:
    """只改讲稿时画面没变（音频指纹变化自会让 key 失效），不必作废该页片段。"""
    project, slide = await _make_page(db_session)
    _add_segment(db_session, "seg-keep")
    await db_session.flush()

    await _save(db_session, project, slide, script_text="改过的讲稿。")

    assert [row.segment_key for row in await _segments(db_session)] == ["seg-keep"]


async def test_resaving_same_config_keeps_page_segments(db_session: AsyncSession) -> None:
    """配置没变就复用缓存：重复保存不该白重渲一页。"""
    project, slide = await _make_page(db_session)
    await _save(db_session, project, slide, highlight_color="#FF3B30")
    _add_segment(db_session, "seg-after-save")
    await db_session.flush()

    await _save(db_session, project, slide, highlight_color="#FF3B30")

    assert [row.segment_key for row in await _segments(db_session)] == ["seg-after-save"]
