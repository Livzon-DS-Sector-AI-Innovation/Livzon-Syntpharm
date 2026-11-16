"""给存量的 AI 讲稿补句末标点（幂等、可预览、可回滚）。

背景
----
改造前 `script_ai.segments_to_script()` 用空串直拼各段，落库的 `script_text` 与
`script_segments` 都没有句末标点。TTS 靠标点断句，缺标点会让整页被当成一句连读，
听感明显偏快；补标点后 `script_key` 变化，旧音频会在下次渲染时自动重新合成。

为什么不放进 alembic
------------------
纯数据回填、不含结构变更；进迁移链会在正式环境部署时自动改写生产讲稿。
按仓库惯例放 scripts/migration/，由人确认后手动执行。

只处理 `script_source='ai'` 且有 `script_segments` 的行：
- 人工改过的讲稿（manual/upload）不动，避免擅自改用户措辞；
- 没有 `script_segments` 的旧行无法确定断句位置，跳过并计数，留给用户在前端处理。

用法
----
    uv run python scripts/migration/backfill_agent_script_punctuation.py                  # 只预览
    uv run python scripts/migration/backfill_agent_script_punctuation.py --project-id <id>
    uv run python scripts/migration/backfill_agent_script_punctuation.py --apply          # 实际写入
"""

import argparse
import asyncio
import os
import re
import sys
import uuid
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import select

from app.core.database import async_session_factory
from app.modules.agent.alignment import SENTENCE_END_CHARS, ensure_sentence_end
from app.modules.agent.models import PptVideoProject, PptVideoSlide

_SAMPLE_LIMIT = 10
_BATCH_SIZE = 200


def _flatten(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def plan_fix(slide: PptVideoSlide, language: str) -> tuple[str, list[dict[str, Any]]] | None:
    """算出这一页补标点后的 (script_text, script_segments)；无需改动返回 None。"""
    script = (slide.script_text or "").strip()
    stored = slide.script_segments
    if not script or not isinstance(stored, list) or not stored:
        return None

    texts: list[str] = []
    targets: list[list[str]] = []
    for item in stored:
        if not isinstance(item, dict):
            return None
        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            return None
        raw_targets = item.get("targets") or []
        texts.append(text.strip())
        targets.append([str(target) for target in raw_targets] if isinstance(raw_targets, list) else [])

    # 落库段必须与讲稿逐字一致，否则说明用户改过讲稿，不能按段重排
    if _flatten("".join(texts)) != _flatten(script):
        return None

    fixed = [ensure_sentence_end(text, language) for text in texts]
    if fixed == texts and script[-1] in SENTENCE_END_CHARS:
        return None

    joiner = " " if language == "en" else ""
    new_script = joiner.join(fixed)
    new_segments: list[dict[str, Any]] = [
        {"text": text, "targets": item_targets} for text, item_targets in zip(fixed, targets, strict=True)
    ]
    if new_script == script and new_segments == stored:
        return None
    return new_script, new_segments


async def main(apply: bool, project_id: uuid.UUID | None) -> int:
    async with async_session_factory() as session:
        stmt = select(PptVideoSlide).where(
            PptVideoSlide.is_deleted.is_(False),
            PptVideoSlide.script_source == "ai",
            PptVideoSlide.script_text != "",
        )
        if project_id is not None:
            stmt = stmt.where(PptVideoSlide.project_id == project_id)
        slides = list((await session.scalars(stmt.order_by(PptVideoSlide.project_id, PptVideoSlide.slide_no))).all())

        languages: dict[uuid.UUID, str] = {}
        if slides:
            project_ids = {slide.project_id for slide in slides}
            rows = await session.execute(
                select(PptVideoProject.id, PptVideoProject.default_language).where(PptVideoProject.id.in_(project_ids))
            )
            languages = {row.id: (row.default_language or "zh") for row in rows}

        samples: list[tuple[str, str, str]] = []
        pending: list[tuple[PptVideoSlide, str, list[dict[str, object]]]] = []
        skipped_no_segments = 0
        for slide in slides:
            if not slide.script_segments:
                skipped_no_segments += 1
                continue
            language = languages.get(slide.project_id, "zh")
            planned = plan_fix(slide, language)
            if planned is None:
                continue
            new_script, new_segments = planned
            pending.append((slide, new_script, new_segments))
            if len(samples) < _SAMPLE_LIMIT:
                samples.append((slide.script_text or "", new_script, str(slide.id)))

        print(f"扫描 AI 讲稿: {len(slides)} 页")
        print(f"需要补标点: {len(pending)} 页；无分段结构跳过: {skipped_no_segments} 页")
        for before, after, slide_id in samples:
            print(f"  slide={slide_id}")
            print(f"    before: {before[:60]}")
            print(f"    after : {after[:60]}")

        if not apply:
            print("\n预览模式，未写入。确认无误后加 --apply 执行。")
            return 0
        if not pending:
            print("没有需要写入的记录。")
            return 0

        for start in range(0, len(pending), _BATCH_SIZE):
            for slide, new_script, new_segments in pending[start : start + _BATCH_SIZE]:
                slide.script_text = new_script
                slide.script_segments = new_segments
            await session.commit()
            print(f"已写入 {min(start + _BATCH_SIZE, len(pending))}/{len(pending)} 页")

        print("完成。旧音频会在下次渲染时因 script_key 变化自动重新合成。")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="给存量 AI 讲稿补句末标点")
    parser.add_argument("--apply", action="store_true", help="实际写入（默认只预览）")
    parser.add_argument("--project-id", type=str, default=None, help="只处理指定项目")
    args = parser.parse_args()
    project = uuid.UUID(args.project_id) if args.project_id else None
    raise SystemExit(asyncio.run(main(args.apply, project)))
