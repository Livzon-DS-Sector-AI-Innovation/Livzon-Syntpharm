"""Domain vocabulary for the 2026 入职台账 (ticket #199).

Single source of truth for the option lists in the 2026 field specification.
Request schemas use these literal types so invalid options are rejected with
a 422 and the OpenAPI enum matches the specification.
"""

from __future__ import annotations

from typing import Literal

PositionLevel = Literal["员工级", "主管级", "经理级", "总监级", "副总经理级", "总经理级"]
PersonnelIdentity = Literal["正式工", "实习生", "返聘人员"]
JoinCategory = Literal["社招", "校招", "猎头推荐", "内部推荐", "集团内部调动", "事业部内部调动"]
EducationLevel = Literal["博士", "硕士", "本科", "大专", "大专以下"]
Gender = Literal["男", "女"]
GroupClassification = Literal[
    "职能管理",
    "生产一线",
    "生产一线：管理",
    "生产辅助",
    "研发一线",
    "技术一线",
    "后勤服务",
]

POSITION_LEVELS: tuple[str, ...] = (
    "员工级",
    "主管级",
    "经理级",
    "总监级",
    "副总经理级",
    "总经理级",
)
PERSONNEL_IDENTITIES: tuple[str, ...] = ("正式工", "实习生", "返聘人员")
JOIN_CATEGORIES: tuple[str, ...] = (
    "社招",
    "校招",
    "猎头推荐",
    "内部推荐",
    "集团内部调动",
    "事业部内部调动",
)
EDUCATION_LEVELS: tuple[str, ...] = ("博士", "硕士", "本科", "大专", "大专以下")
GENDERS: tuple[str, ...] = ("男", "女")
GROUP_CLASSIFICATIONS: tuple[str, ...] = (
    "职能管理",
    "生产一线",
    "生产一线：管理",
    "生产辅助",
    "研发一线",
    "技术一线",
    "后勤服务",
)
