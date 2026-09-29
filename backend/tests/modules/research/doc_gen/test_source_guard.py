"""资料源守卫测试：新流程允许「零任务级文件」，但必须至少有一个来源。

背景：资料统一进项目知识库后，新建报告不再上传任务级文件。原来
``if not files: raise JobAbortedError("no_files")`` 会把正常流程直接判死，
改为按来源判定；本测试锁住这条边界，避免回归。
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.modules.research.doc_gen.pipeline import JobAbortedError, _ensure_source_available


def _job(**kwargs: Any) -> Any:
    base = {"supplement_text": None, "project_id": None}
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_files_present_passes() -> None:
    _ensure_source_available(_job(), [object()])


def test_project_only_passes() -> None:
    """资料全在项目知识库/项目登记数据里：没有任务级文件也应放行。"""
    _ensure_source_available(_job(project_id="11111111-1111-1111-1111-111111111111"), [])


def test_supplement_only_passes() -> None:
    _ensure_source_available(_job(supplement_text="  本报告基于内部口头确认的参数  "), [])


def test_no_source_raises_with_actionable_message() -> None:
    with pytest.raises(JobAbortedError) as exc:
        _ensure_source_available(_job(supplement_text="   "), [])

    assert exc.value.code == "no_source"
    assert "项目知识库" in exc.value.message
