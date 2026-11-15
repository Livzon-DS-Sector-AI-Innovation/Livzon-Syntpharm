"""Domain vocabulary for the 2026 入职台账 (ticket #199).

Single source of truth for the option lists in the 2026 field specification.
Request schemas use these literal types so invalid options are rejected with
a 422 and the OpenAPI enum matches the specification. The runtime tuples are
derived from the literals so the two never drift.
"""

from __future__ import annotations

from typing import Literal, cast, get_args

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

POSITION_LEVELS: tuple[str, ...] = cast(tuple[str, ...], get_args(PositionLevel))
PERSONNEL_IDENTITIES: tuple[str, ...] = cast(tuple[str, ...], get_args(PersonnelIdentity))
JOIN_CATEGORIES: tuple[str, ...] = cast(tuple[str, ...], get_args(JoinCategory))
EDUCATION_LEVELS: tuple[str, ...] = cast(tuple[str, ...], get_args(EducationLevel))
GENDERS: tuple[str, ...] = cast(tuple[str, ...], get_args(Gender))
GROUP_CLASSIFICATIONS: tuple[str, ...] = cast(tuple[str, ...], get_args(GroupClassification))
