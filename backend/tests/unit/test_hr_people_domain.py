"""Personnel mirror mapping (ticket #198).

Seam: ``parse_directory_employee`` / the small display helpers, with no HTTP or
database. Catches:
- the directory mget flat field set maps to the retained mirror fields;
- omitted keys become empty values, not errors;
- ``place_id``/``resign_time`` of ``"0"`` mean "not set";
- department levels come from the stored path (root → 一级 → 二级).
"""

from __future__ import annotations

from datetime import date

from app.modules.hr.people_domain import (
    EmployeeProfileRecord,
    department_levels,
    gender_label,
    parse_directory_employee,
    staff_status_label,
)

RAW_EMPLOYEE = {
    "open_id": "ou-1001",
    "name": {"default_value": "张三", "i18n_value": {"zh_cn": "张三"}},
    "mobile": "13800000000",
    "email": "zhangsan@example.com",
    "enterprise_email": "zhangsan@livzon.cn",
    "enterprise_email_aliases": ["zs@livzon.cn"],
    "gender": 2,
    "description": "认真做事",
    "avatar": {
        "avatar_72": "https://a/72.png",
        "avatar_240": "https://a/240.png",
        "avatar_640": "https://a/640.png",
        "avatar_origin": "https://a/origin.png",
    },
    "background_image": "https://bg.png",
    "geo_name": "cn",
    "active_status": 2,
    "is_resigned": False,
    "resign_time": "0",
    "is_admin": True,
    "is_primary_admin": False,
    "data_source": 1,
    "job_number": "109000586",
    "job_title": {
        "job_title_id": "jt-1",
        "job_title_name": {"default_value": "车间班长"},
    },
    "join_date": "2018-03-06",
    "employment_type": 1,
    "staff_status": 1,
    "work_country_or_region": "",
    "work_place": {"place_id": "0", "place_name": {"default_value": ""}},
    "work_station": "",
    "dotted_line_leader_ids": ["ou-leader"],
    "resign_date": "",
    "resign_type": "",
    "resign_reason": "",
    "resign_remark": "",
    "positions": [{"position_code": "P-1", "position_name": "班长"}],
    "job_level": {"job_level_id": "jl-1", "job_level_name": {"default_value": "M1"}},
    "job_family": {"job_family_id": "jf-1", "job_family_name": {"default_value": "生产序列"}},
    "employee_order_in_departments": [
        {"department_id": "od-101-1"},
        {"department_id": "od-101"},
    ],
}


def test_parse_maps_every_retained_field() -> None:
    record = parse_directory_employee(RAW_EMPLOYEE)

    assert record is not None
    assert record.open_id == "ou-1001"
    assert record.name == "张三"
    assert record.mobile == "13800000000"
    assert record.email == "zhangsan@example.com"
    assert record.enterprise_email == "zhangsan@livzon.cn"
    assert record.email_aliases == ["zs@livzon.cn"]
    assert record.gender == 2
    assert record.description == "认真做事"
    assert record.avatar_72 == "https://a/72.png"
    assert record.avatar_240 == "https://a/240.png"
    assert record.avatar_640 == "https://a/640.png"
    assert record.avatar_origin == "https://a/origin.png"
    assert record.background_image == "https://bg.png"
    assert record.geo_name == "cn"
    assert record.active_status == 2
    assert record.is_resigned is False
    assert record.resign_time == ""
    assert record.is_admin is True
    assert record.is_primary_admin is False
    assert record.data_source == 1
    assert record.employee_no == "109000586"
    assert record.job_title_id == "jt-1"
    assert record.job_title_name == "车间班长"
    assert record.hire_date == date(2018, 3, 6)
    assert record.employment_type == 1
    assert record.staff_status == 1
    assert record.work_country_or_region == ""
    assert record.work_place_id == ""
    assert record.work_place_name == ""
    assert record.work_station == ""
    assert record.dotted_line_leader_ids == ["ou-leader"]
    assert record.positions == [{"id": "P-1", "name": "班长"}]
    assert record.job_level_id == "jl-1"
    assert record.job_level_name == "M1"
    assert record.job_family_id == "jf-1"
    assert record.job_family_name == "生产序列"
    assert record.department_ids == ["od-101-1", "od-101"]


def test_omitted_keys_become_empty_values() -> None:
    record = parse_directory_employee({"open_id": "ou-empty", "name": "李四"})

    assert record is not None
    assert record.name == "李四"
    assert record.mobile == ""
    assert record.email == ""
    assert record.enterprise_email == ""
    assert record.email_aliases == []
    assert record.gender is None
    assert record.description == ""
    assert record.avatar_72 == ""
    assert record.background_image == ""
    assert record.geo_name == ""
    assert record.active_status is None
    assert record.is_resigned is False
    assert record.resign_time == ""
    assert record.is_admin is False
    assert record.is_primary_admin is False
    assert record.data_source is None
    assert record.employee_no == ""
    assert record.job_title_name == ""
    assert record.hire_date is None
    assert record.employment_type is None
    assert record.staff_status is None
    assert record.work_country_or_region == ""
    assert record.work_place_id == ""
    assert record.work_place_name == ""
    assert record.work_station == ""
    assert record.extension_number == ""
    assert record.dotted_line_leader_ids == []
    assert record.resign_date is None
    assert record.resign_type == ""
    assert record.resign_reason == ""
    assert record.resign_remark == ""
    assert record.positions == []
    assert record.job_level_name == ""
    assert record.job_family_name == ""
    assert record.department_ids == []


def test_parse_skips_employee_without_open_id() -> None:
    assert parse_directory_employee({"name": "无 open id"}) is None


def test_gender_and_staff_status_labels() -> None:
    assert gender_label(1) == "男"
    assert gender_label(2) == "女"
    assert gender_label(0) == "未知"
    assert gender_label(None) == "未知"
    assert staff_status_label(1) == "在职"
    assert staff_status_label(2) == "离职"
    assert staff_status_label(None) == "—"


def test_department_levels_read_the_path_after_the_company_root() -> None:
    record = EmployeeProfileRecord(
        open_id="ou-1",
        name="张三",
        department_names=["101车间", "合成工段"],
        department_path=[
            {"id": "od-company", "name": "珠海保税区丽珠合成制药有限公司"},
            {"id": "od-101", "name": "101车间"},
            {"id": "od-101-1", "name": "合成工段"},
        ],
    )

    assert department_levels(record) == ("101车间", "合成工段")

    level_one_only = EmployeeProfileRecord(
        open_id="ou-2",
        name="李四",
        department_names=["质量保证部"],
        department_path=[
            {"id": "od-company", "name": "珠海保税区丽珠合成制药有限公司"},
            {"id": "od-qa", "name": "质量保证部"},
        ],
    )
    assert department_levels(level_one_only) == ("质量保证部", "")


def test_parse_directory_employee_handles_nested_mget_payload() -> None:
    raw = {
        "base_info": {
            "employee_id": "ou-123",
            "name": {"name": {"default_value": "蔡丽英"}},
            "mobile": "+86 13800000000",
            "enterprise_email_aliases": [],
            "departments": [
                {"department_id": "od-qa", "name": {"default_value": "注册部"}},
            ],
            "department_path_infos": [
                [
                    {"department_id": "od-company", "department_name": {"default_value": "公司"}},
                    {"department_id": "od-qa", "department_name": {"default_value": "注册部"}},
                ]
            ],
            "dotted_line_leader_ids": [],
            "is_resigned": False,
            "resign_time": "0",
        },
        "work_info": {
            "job_number": "109000586",
            "job_title": {"job_title_id": "jt-1", "job_title_name": {"default_value": "注册主管"}},
            "join_date": "2023-12-01",
            "staff_status": 1,
            "work_place": {"place_id": "0"},
            "work_station": {"default_value": ""},
        },
    }

    record = parse_directory_employee(raw)

    assert record is not None
    assert record.open_id == "ou-123"
    assert record.name == "蔡丽英"
    assert record.employee_no == "109000586"
    assert record.job_title_name == "注册主管"
    assert record.hire_date == date(2023, 12, 1)
    assert record.department_ids == ["od-qa"]
    assert record.department_names == ["注册部"]
    assert record.resign_time == ""
    assert record.work_place_id == ""


def test_employee_required_fields_use_directory_paths() -> None:
    from app.modules.hr.people_feishu import EMPLOYEE_REQUIRED_FIELDS

    assert EMPLOYEE_REQUIRED_FIELDS
    assert all(field.startswith(("base_info.", "work_info.")) for field in EMPLOYEE_REQUIRED_FIELDS)
