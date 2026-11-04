"""高亮样式参数解析：页级覆盖 → 模块设置 → 出帧参数。

这里只验证「合并与降级」的纯逻辑，出帧画面由 test_ppt_video_render 覆盖。
"""

from dataclasses import replace
from types import SimpleNamespace
from typing import Any

from app.modules.agent import config, worker
from app.modules.agent.config import DEFAULTS


def _slide(**kwargs: Any) -> Any:
    """页级覆盖字段缺失（老数据）与显式 None 都应视为「跟随设置」。"""
    return SimpleNamespace(**{"highlight_style": None, "highlight_color": None, **kwargs})


def test_default_style_recolors_text_and_keeps_background() -> None:
    paint = worker._resolve_highlight_paint(DEFAULTS, _slide())

    assert paint.style == config.HIGHLIGHT_STYLE_TEXT_RECOLOR
    # 文字染色档不压暗：用户要「字变红、背景不动」
    assert paint.dim_alpha == 0
    # 也不画矩形描边：文字已在解析阶段定位，命中字直接换色即可
    assert paint.outline_px == 0
    assert paint.recolor_strength == DEFAULTS.highlight_recolor_strength
    assert paint.accent == config.parse_hex_color(DEFAULTS.highlight_color)


def test_slide_override_wins_over_module_settings() -> None:
    settings = replace(DEFAULTS, highlight_style=config.HIGHLIGHT_STYLE_TEXT_RECOLOR)
    slide = _slide(highlight_style=config.HIGHLIGHT_STYLE_DIM, highlight_color="00ff00")

    paint = worker._resolve_highlight_paint(settings, slide)

    assert paint.style == config.HIGHLIGHT_STYLE_DIM
    assert paint.color == "#00FF00"
    assert paint.accent == (0, 255, 0)
    assert paint.dim_alpha == settings.highlight_dim_alpha
    assert paint.recolor_strength == 0


def test_invalid_override_falls_back_to_module_settings() -> None:
    """坏值不能进渲染：未知样式回落默认档，非法颜色回落默认色。"""
    slide = _slide(highlight_style="make_it_purple", highlight_color="#12")

    paint = worker._resolve_highlight_paint(DEFAULTS, slide)

    assert paint.style == DEFAULTS.highlight_style
    assert paint.color == DEFAULTS.highlight_color


def test_fingerprint_changes_with_color_and_strength() -> None:
    """颜色或染色强度变了，画面就不同，帧缓存指纹必须随之变化。"""
    base = worker._resolve_highlight_paint(DEFAULTS, _slide())
    recolored = worker._resolve_highlight_paint(DEFAULTS, _slide(highlight_color="#00FF00"))
    stronger = worker._resolve_highlight_paint(replace(DEFAULTS, highlight_recolor_strength=40), _slide())

    assert base.fingerprint != recolored.fingerprint
    assert base.fingerprint != stronger.fingerprint
