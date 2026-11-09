"""高亮三级开关（模块总闸 / 项目 / 本页）的判定单测。

守两件事：
1. 模块总闸关掉后，任何层级勾选都不该出高亮；
2. 项目未勾选 = 该页成片无高亮（除非本页单独勾选），计划为空时不产生高亮时间轴。
"""

from pathlib import Path

from app.modules.agent import highlight, service, worker
from app.modules.agent.config import DEFAULTS


def _layout() -> dict[str, object]:
    return {
        "width": 12192000,
        "height": 6858000,
        "shapes": [
            {
                "id": "s0",
                "text": "含量测定",
                "left": 0,
                "top": 0,
                "width": 900000,
                "height": 400000,
            }
        ],
    }


def _page_audio(duration_ms: int = 4000) -> service.PageAudio:
    return service.PageAudio(
        path=Path("ignored.wav"),
        duration_ms=duration_ms,
        sha256="sha",
        audio_key="key",
        segments=[],
        segment_durations_ms=[],
        pause_ms=0,
    )


def test_highlight_active_truth_table() -> None:
    # 总闸关 → 一律不亮
    assert highlight.highlight_active(False, False, False) is False
    assert highlight.highlight_active(False, True, False) is False
    assert highlight.highlight_active(False, False, True) is False
    assert highlight.highlight_active(False, True, True) is False
    # 总闸开：项目或本页任一层勾选即亮
    assert highlight.highlight_active(True, False, False) is False
    assert highlight.highlight_active(True, True, False) is True
    assert highlight.highlight_active(True, False, True) is True
    assert highlight.highlight_active(True, True, True) is True


def test_build_highlight_plan_empty_when_inactive() -> None:
    plan = worker._build_highlight_plan(
        "本页介绍含量测定方法。",
        _layout(),
        _page_audio(),
        DEFAULTS,
        False,
    )

    # 不亮也要保留总时长，时间轴仍按整页音频走
    assert plan.steps == []
    assert plan.total_ms == 4000
    assert plan.has_boxes is False


def test_build_highlight_plan_builds_when_active() -> None:
    plan = worker._build_highlight_plan(
        "本页介绍含量测定方法。",
        _layout(),
        _page_audio(),
        DEFAULTS,
        True,
    )

    assert plan.steps != []
    assert plan.has_boxes is True
    assert plan.total_ms == 4000
