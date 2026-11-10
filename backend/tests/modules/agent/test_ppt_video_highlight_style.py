"""高亮样式参数解析：页级 → 项目级 → 模块设置 → 出帧参数。

这里只验证「合并与降级」的纯逻辑，出帧画面由 test_ppt_video_render 覆盖。
"""

from dataclasses import replace
from types import SimpleNamespace
from typing import Any

from app.modules.agent import config, worker
from app.modules.agent.config import DEFAULTS


def _slide(**kwargs: Any) -> Any:
    """页级开关默认关闭：值可能还在，未启用就不参与取值。"""
    return SimpleNamespace(
        **{
            "highlight_style": None,
            "highlight_color": None,
            "highlight_override_enabled": False,
            **kwargs,
        }
    )


def _project(**kwargs: Any) -> Any:
    """项目级开关默认关闭：关闭时值保留但不生效，回落到模块设置。"""
    return SimpleNamespace(
        **{
            "highlight_style": None,
            "highlight_color": None,
            "highlight_override_enabled": False,
            **kwargs,
        }
    )


def test_default_style_recolors_text_and_keeps_background() -> None:
    paint = worker._resolve_highlight_paint(DEFAULTS, _slide(), _project())

    assert paint.style == config.HIGHLIGHT_STYLE_TEXT_RECOLOR
    # 文字染色档不压暗：用户要「字变红、背景不动」
    assert paint.dim_alpha == 0
    # 也不画矩形描边：文字已在解析阶段定位，命中字直接换色即可
    assert paint.outline_px == 0
    assert paint.recolor_strength == DEFAULTS.highlight_recolor_strength
    assert paint.accent == config.parse_hex_color(DEFAULTS.highlight_color)


def test_slide_override_wins_over_module_settings() -> None:
    settings = replace(DEFAULTS, highlight_style=config.HIGHLIGHT_STYLE_TEXT_RECOLOR)
    slide = _slide(
        highlight_style=config.HIGHLIGHT_STYLE_DIM,
        highlight_color="00ff00",
        highlight_override_enabled=True,
    )

    paint = worker._resolve_highlight_paint(settings, slide, _project())

    assert paint.style == config.HIGHLIGHT_STYLE_DIM
    assert paint.color == "#00FF00"
    assert paint.accent == (0, 255, 0)
    assert paint.dim_alpha == settings.highlight_dim_alpha
    assert paint.recolor_strength == 0


def test_project_override_wins_over_module_settings() -> None:
    settings = replace(DEFAULTS, highlight_style=config.HIGHLIGHT_STYLE_TEXT_RECOLOR, highlight_color="#FF3B30")
    project = _project(
        highlight_style=config.HIGHLIGHT_STYLE_OUTLINE,
        highlight_color="#0055AA",
        highlight_override_enabled=True,
    )

    paint = worker._resolve_highlight_paint(settings, _slide(), project)

    assert paint.style == config.HIGHLIGHT_STYLE_OUTLINE
    assert paint.color == "#0055AA"


def test_slide_override_wins_over_project_settings() -> None:
    project = _project(
        highlight_style=config.HIGHLIGHT_STYLE_OUTLINE,
        highlight_color="#0055AA",
        highlight_override_enabled=True,
    )
    slide = _slide(
        highlight_style=config.HIGHLIGHT_STYLE_DIM,
        highlight_color="#00FF00",
        highlight_override_enabled=True,
    )

    paint = worker._resolve_highlight_paint(DEFAULTS, slide, project)

    assert paint.style == config.HIGHLIGHT_STYLE_DIM
    assert paint.color == "#00FF00"


def test_invalid_override_falls_back_to_module_settings() -> None:
    """坏值不能进渲染：未知样式回落默认档，非法颜色回落默认色。"""
    slide = _slide(
        highlight_style="make_it_purple",
        highlight_color="#12",
        highlight_override_enabled=True,
    )

    paint = worker._resolve_highlight_paint(DEFAULTS, slide, _project())

    assert paint.style == DEFAULTS.highlight_style
    assert paint.color == DEFAULTS.highlight_color


def test_invalid_project_value_falls_back_to_module_settings() -> None:
    """项目级写了坏值也不能卡住渲染，继续往模块设置回落。"""
    settings = replace(DEFAULTS, highlight_style=config.HIGHLIGHT_STYLE_DIM, highlight_color="#123456")
    project = _project(
        highlight_style="make_it_purple",
        highlight_color="#12",
        highlight_override_enabled=True,
    )

    paint = worker._resolve_highlight_paint(settings, _slide(), project)

    assert paint.style == config.HIGHLIGHT_STYLE_DIM
    assert paint.color == "#123456"


def test_fingerprint_changes_with_color_and_strength() -> None:
    """颜色或染色强度变了，画面就不同，帧缓存指纹必须随之变化。"""
    base = worker._resolve_highlight_paint(DEFAULTS, _slide(), _project())
    recolored = worker._resolve_highlight_paint(
        DEFAULTS, _slide(highlight_color="#00FF00", highlight_override_enabled=True), _project()
    )
    stronger = worker._resolve_highlight_paint(replace(DEFAULTS, highlight_recolor_strength=40), _slide(), _project())

    assert base.fingerprint != recolored.fingerprint
    assert base.fingerprint != stronger.fingerprint


def test_disabled_slide_override_is_ignored_even_when_values_kept() -> None:
    """关掉开关只是「本级不生效」：值还留着也不能参与取值，否则开关关不掉。"""
    project = _project(
        highlight_style=config.HIGHLIGHT_STYLE_OUTLINE,
        highlight_color="#0055AA",
        highlight_override_enabled=True,
    )
    slide = _slide(highlight_style=config.HIGHLIGHT_STYLE_DIM, highlight_color="#00FF00")

    paint = worker._resolve_highlight_paint(DEFAULTS, slide, project)

    assert paint.style == config.HIGHLIGHT_STYLE_OUTLINE
    assert paint.color == "#0055AA"


def test_disabled_project_override_is_ignored_even_when_values_kept() -> None:
    settings = replace(DEFAULTS, highlight_style=config.HIGHLIGHT_STYLE_TEXT_RECOLOR, highlight_color="#123456")
    project = _project(highlight_style=config.HIGHLIGHT_STYLE_OUTLINE, highlight_color="#0055AA")

    paint = worker._resolve_highlight_paint(settings, _slide(), project)

    assert paint.style == settings.highlight_style
    assert paint.color == "#123456"


def test_both_levels_disabled_use_module_settings() -> None:
    settings = replace(DEFAULTS, highlight_style=config.HIGHLIGHT_STYLE_DIM, highlight_color="#654321")
    slide = _slide(highlight_style=config.HIGHLIGHT_STYLE_OUTLINE, highlight_color="#00FF00")
    project = _project(highlight_style=config.HIGHLIGHT_STYLE_TEXT_RECOLOR, highlight_color="#0055AA")

    paint = worker._resolve_highlight_paint(settings, slide, project)

    assert paint.style == config.HIGHLIGHT_STYLE_DIM
    assert paint.color == "#654321"


def test_enabled_slide_falls_back_per_field_to_project() -> None:
    """勾选后只填样式、没填颜色时，颜色仍按字段回落到项目，而不是整级跳过。"""
    project = _project(highlight_color="#0055AA", highlight_override_enabled=True)
    slide = _slide(highlight_style=config.HIGHLIGHT_STYLE_DIM, highlight_override_enabled=True)

    paint = worker._resolve_highlight_paint(DEFAULTS, slide, project)

    assert paint.style == config.HIGHLIGHT_STYLE_DIM
    assert paint.color == "#0055AA"
