"""区域级高亮的真库烟测（只读为主，末尾复原）。

在容器内跑：docker cp 到 /app/scripts/test/ 后
    docker exec erp-backend /app/.venv/bin/python -m scripts.test.smoke_highlight_regions
"""

import asyncio
import json
import uuid

from app.core.database import async_session_factory
from app.modules.agent import highlight, service

PROJECT_ID = uuid.UUID("164584ca-a8d4-4cb2-852f-7aa8d9efb771")
SLIDE_UID = "960fe969-8c10-4475-9207-44e14ebb7097"


def show(title: str, payload: object) -> None:
    print(f"\n== {title} ==")
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


async def main() -> None:
    async with async_session_factory() as session:
        response = await service.slide_regions(session, PROJECT_ID, SLIDE_UID)
        show(
            "regions 接口数据",
            {
                "page": [response.page_width, response.page_height],
                "items": len(response.items),
                "first_items": [item.model_dump() for item in response.items[:3]],
                "sentences": response.sentences[:3],
                "sentence_count": len(response.sentences),
            },
        )

        if not response.items:
            print("\n该页解析不出元素，跳过后续校验")
            return

        first = response.items[0]
        stored = {
            "regions": [
                {"id": first.element_id, "mode": "area", "color": "ff3b30", "fill_alpha": 120},
            ],
            "sentences": [{"text": response.sentences[0], "targets": [first.element_id], "mute": []}],
        }

        slide = await service.get_slide_by_uid(session, PROJECT_ID, SLIDE_UID)
        original = slide.highlight_regions

        # 走与接口相同的校验链路，确认落库值被规范化（颜色大写、alpha 夹紧）
        config = highlight.parse_region_config(stored, slide.layout)
        slide.highlight_regions = highlight.dump_region_config(config)
        await session.commit()
        reloaded = service.slide_item(slide, PROJECT_ID)
        show("写入后回显", reloaded.highlight_regions.model_dump() if reloaded.highlight_regions else None)

        # 渲染侧：area 应带自己的颜色，off 应一个框都不给
        area_boxes = highlight.boxes_for_segment(
            highlight.ScriptSegment(text=response.sentences[0], targets=(first.element_id,)),
            slide.layout,
            config=config,
        )
        off_config = highlight.parse_region_config({"regions": [{"id": first.element_id, "mode": "off"}]}, slide.layout)
        off_boxes = highlight.boxes_for_segment(
            highlight.ScriptSegment(text=response.sentences[0], targets=(first.element_id,)),
            slide.layout,
            config=off_config,
        )
        show(
            "渲染取框",
            {
                "area": [
                    {"top": box.top, "left": box.left, "mode": box.mode, "color": box.color, "alpha": box.fill_alpha}
                    for box in area_boxes
                ],
                "off_count": len(off_boxes),
            },
        )

        # 复原
        slide.highlight_regions = original
        await session.commit()
        print("\n已复原原始 highlight_regions")


if __name__ == "__main__":
    asyncio.run(main())
