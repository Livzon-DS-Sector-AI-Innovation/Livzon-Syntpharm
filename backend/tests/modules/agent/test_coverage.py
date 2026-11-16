"""讲稿覆盖度自检单测（纯函数，不依赖数据库与 LLM）。"""

from typing import Any

from app.modules.agent.coverage import compute_coverage


def _layout(*shapes: dict[str, Any]) -> dict[str, Any]:
    return {"width": 12192000, "height": 6858000, "shapes": list(shapes)}


def _shape(
    text: str, *, left: int = 800000, top: int = 400000, width: int = 3000000, height: int = 600000
) -> dict[str, Any]:
    return {
        "name": "tb",
        "kind": "TEXT_BOX (17)",
        "text": text,
        "left": left,
        "top": top,
        "width": width,
        "height": height,
    }


def test_full_coverage_when_every_point_is_mentioned() -> None:
    layout = _layout(_shape("收率提升"), _shape("产线满负荷", top=1200000))

    result = compute_coverage("本页讲收率提升，产线满负荷。", layout)

    assert result.checked is True
    assert result.score == 1.0
    assert result.missing == []


def test_missing_points_listed_in_reading_order() -> None:
    layout = _layout(
        _shape("右栏要点", left=6000000, top=1200000),
        _shape("左栏要点", left=800000, top=1200000),
        _shape("页面标题", top=300000, width=6000000),
    )

    result = compute_coverage("页面标题。", layout)

    assert result.checked is True
    assert 0 < result.score < 1
    assert result.missing == ["左栏要点", "右栏要点"]


def test_blank_script_is_not_checked() -> None:
    result = compute_coverage("   ", _layout(_shape("收率提升")))

    assert result.checked is False
    assert result.score == 0.0


def test_page_without_text_is_not_checked() -> None:
    layout = {"width": 12192000, "height": 6858000, "shapes": []}

    result = compute_coverage("本页只有一张图片。", layout)

    assert result.checked is False


def test_partial_score_between_zero_and_one() -> None:
    layout = _layout(_shape("收率提升"), _shape("产线满负荷", top=1200000))
    result = compute_coverage("本页讲收率提升。", layout)

    assert 0 < result.score < 1
