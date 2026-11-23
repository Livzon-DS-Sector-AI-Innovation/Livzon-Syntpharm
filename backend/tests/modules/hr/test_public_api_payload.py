"""#219：HR ``public_api`` 的人员 payload 是跨模块展示的唯一来源。

用户管理页的姓名 / 手机 / 邮箱 / 是否在职全部从这里取；字段一旦缺失，
页面会静默退化成本地旧值或「未建档案」，因此这里锁定输出契约。
"""

from __future__ import annotations

from typing import Any

from app.modules.hr.models import EmployeeProfile
from app.modules.hr.public_api import _profile_payload


def _profile(**overrides: Any) -> EmployeeProfile:
    payload: dict[str, Any] = {
        "open_id": "ou-test",
        "name": "张三",
        "mobile": "13800000000",
        "email": "zhangsan@example.com",
        "employee_no": "E001",
        "department_names": ["101车间", "合成工段"],
        "department_path": [{"id": "od-101", "name": "101车间"}],
        "job_title_name": "车间班长",
        "avatar_240": "https://example.com/240.png",
        "is_current": True,
        "staff_status": 1,
    }
    payload.update(overrides)
    return EmployeeProfile(**payload)


def test_payload_exposes_identity_display_fields() -> None:
    """用户管理页依赖的字段必须全部出现在 payload 里。"""
    data = _profile_payload(_profile())

    assert data["name"] == "张三"
    assert data["mobile"] == "13800000000"
    assert data["email"] == "zhangsan@example.com"
    assert data["employee_no"] == "E001"
    assert data["department_names"] == ["101车间", "合成工段"]
    assert data["job_title_name"] == "车间班长"
    assert data["avatar_url"] == "https://example.com/240.png"


def test_payload_carries_employment_status() -> None:
    """在职口径来自 is_current + staff_status，两者都要对外可见。"""
    data = _profile_payload(_profile(is_current=True, staff_status=1))
    assert data["is_current"] is True
    assert data["staff_status"] == 1
    assert data["staff_status_label"] == "在职"


def test_payload_marks_removed_profile_without_fabricating_status() -> None:
    """已移出目录的行 is_current=False；staff_status 为空时标签是占位符而非「在职」。"""
    data = _profile_payload(_profile(is_current=False, staff_status=None))
    assert data["is_current"] is False
    assert data["staff_status"] is None
    assert data["staff_status_label"] == "—"
