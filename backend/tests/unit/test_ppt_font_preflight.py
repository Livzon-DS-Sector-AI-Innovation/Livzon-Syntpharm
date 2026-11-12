# mypy: ignore-errors
"""PPT 页图出图前的字体自检（`agent.render.verify_font_environment`）。

背景：镜像里忘了装 Liberation/Carlito 时，Arial/Times New Roman 会被 fontconfig 判给更宽的
DejaVu，页图表现为「文字提前折行、上下两段压在一起」。错图看起来像内容写错，极难排查，
所以出图前必须显式校验，不合格就失败。
"""

from __future__ import annotations

import pytest

from app.modules.agent import render


def _fake_match(table: dict[str, str]):
    """构造一个假的 fc-match：未列出的族名一律落到 DejaVu Sans。"""

    def _lookup(name: str) -> str:
        return table.get(name, "DejaVu Sans")

    return _lookup


_OK_ENV = {
    "Arial": "Liberation Sans",
    "Times New Roman": "Liberation Serif",
    "Calibri": "Carlito",
    "微软雅黑": "Noto Sans CJK SC",
    "Microsoft YaHei": "Noto Sans CJK SC",
    "宋体": "Noto Serif CJK SC",
    "SimSun": "Noto Serif CJK SC",
    "思源黑体 CN": "Noto Sans CJK SC",
}


def test_font_environment_ok_returns_no_problem() -> None:
    assert render.font_environment_problems(_fake_match(_OK_ENV)) == []


def test_missing_latin_metric_compatible_font_is_reported() -> None:
    """Arial 落到 DejaVu（v1 镜像的真实状态）必须被报出来。"""
    env = {**_OK_ENV, "Arial": "DejaVu Sans"}
    problems = render.font_environment_problems(_fake_match(env))

    assert len(problems) == 1
    assert "Arial" in problems[0]
    assert "DejaVu Sans" in problems[0]
    assert "Liberation Sans" in problems[0]


def test_missing_cjk_font_is_reported() -> None:
    """中文字族不命中 Noto 时中文会变方块或逐字回退，同样要拦。"""
    env = {**_OK_ENV, "宋体": "DejaVu Sans"}
    problems = render.font_environment_problems(_fake_match(env))

    assert len(problems) == 1
    assert "宋体" in problems[0]


def test_verify_raises_render_error_with_actionable_message() -> None:
    env = {**_OK_ENV, "Times New Roman": "DejaVu Serif"}

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(render, "_fc_match_family", _fake_match(env))
        with pytest.raises(render.RenderError) as excinfo:
            render.verify_font_environment()

    message = str(excinfo.value)
    assert "Times New Roman" in message
    assert "Liberation Serif" in message
    assert "重建镜像" in message


def test_fc_match_family_returns_empty_without_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    """镜像里没有 fontconfig 时不能崩，交给上层当「无匹配」处理。"""
    monkeypatch.setattr(render.shutil, "which", lambda _name: None)

    assert render._fc_match_family("Arial") == ""
