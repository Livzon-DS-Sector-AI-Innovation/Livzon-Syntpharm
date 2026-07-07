"""Natural-language query parser for HR employee database queries.

Extracts structured filter conditions from Chinese user text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any


@dataclass
class EmployeeQueryCriteria:
    """Parsed criteria from natural language."""

    filters: dict[str, Any] = field(default_factory=dict)
    query_type: str = "list"  # "list" or "count"
    name_keyword: str | None = None


# ─── Keyword mappings ───

_STATUS_KEYWORDS = {
    "在职": "在职",
    "在岗": "在职",
    "离职": "离职",
    "辞职": "离职",
    "辞退": "离职",
    "试用期": "试用期",
    "实习": "试用期",
    "待审批": "待审批",
}

_GENDER_KEYWORDS = {
    "男": "男",
    "男性": "男",
    "女": "女",
    "女性": "女",
}

_EDUCATION_KEYWORDS = {
    "高中": "高中",
    "中专": "中专",
    "大专": "大专",
    "专科": "大专",
    "本科": "本科",
    "学士": "本科",
    "研究生": "研究生",
    "硕士": "硕士",
    "博士": "博士",
    "博士后": "博士后",
}

_POLITICAL_STATUS_KEYWORDS = {
    "党员": "党员",
    "中共党员": "党员",
    "共产党员": "党员",
    "群众": "群众",
    "团员": "团员",
    "共青团员": "团员",
    "预备党员": "预备党员",
    "民主党派": "民主党派",
    "无党派": "无党派",
}

_MARITAL_STATUS_KEYWORDS = {
    "已婚": "已婚",
    "未婚": "未婚",
    "离异": "离异",
    "丧偶": "丧偶",
}

_POSITION_KEYWORDS = [
    "工程师",
    "经理",
    "主管",
    "专员",
    "操作员",
    "操作工",
    "文员",
    "总监",
    "助理",
    "厂长",
    "班长",
    "组长",
    "技术员",
    "质检员",
    "会计",
    "出纳",
    "秘书",
    "顾问",
    "研究员",
    "实验员",
    "司机",
    "保安",
    "厨师",
    "保洁",
    "电工",
    "焊工",
    "钳工",
    "车工",
    "铣工",
    "磨工",
    "叉车工",
    "搬运工",
    "包装工",
    "灌装工",
    "配料工",
    "粉碎工",
    "干燥工",
    "结晶工",
    "离心工",
    "蒸馏工",
    "萃取工",
    "合成工",
    "发酵工",
    "精制工",
    "纯化工",
    "造粒工",
    "压片工",
    "包衣工",
    "灯检工",
    "贴标工",
    "灭菌工",
    "清洗工",
    "维修工",
    "机修工",
    "仪表工",
    "水工",
    "锅炉工",
    "空调工",
    "制冷工",
    "污水处理工",
    "环保工",
    "安全员",
    "消防员",
    "仓管员",
    "物料员",
    "统计员",
    "计划员",
    "调度员",
    "采购员",
    "销售员",
    "业务员",
    "客服",
    "前台",
    "人事",
    "行政",
    "财务",
]


# ─── Regex patterns ───

# Department: matches "XX部门", "XX车间", "XX科室", "XX组", "XX部", "XX中心"
# Avoid matching if it's part of a larger entity like "部门经理"
_DEPARTMENT_RE = re.compile(
    r"([一-龥\w\-]{2,20}(?:部门|车间|科室|组|部|中心))(?!经理|主管|主任|专员)"
)

# Team: explicit "XX班组" or bare team names like "一班", "二班", "甲班", "乙班"
_TEAM_RE = re.compile(r"([一-龥甲乙丙丁戊]{1,3}班)(?:组)?")

# Position with prefix
_POSITION_WITH_PREFIX_RE = re.compile(
    r"(?:职位|岗位)[是为:：\s]+([^，。；\n\s]{2,10})"
)

# Age range patterns
_AGE_RANGE_RE = re.compile(r"(\d+)\s*[-~至到]\s*(\d+)\s*(?:岁|周岁)?")
_AGE_MIN_RE = re.compile(r"(\d+)\s*(?:岁|周岁)?\s*(?:以上|起|之后|大于|超过|≥|>=)")
_AGE_MAX_RE = re.compile(r"(\d+)\s*(?:岁|周岁)?\s*(?:以下|以内|之前|小于|低于|≤|<=)")

# Date year patterns
_YEAR_AFTER_RE = re.compile(r"(\d{4})\s*年?\s*(?:之后|以后|以来|后|大于|超过|≥|>=)")
_YEAR_BEFORE_RE = re.compile(r"(\d{4})\s*年?\s*(?:之前|以前|前|小于|低于|≤|<=)")
_YEAR_EXACT_RE = re.compile(r"(\d{4})\s*年(?:出生|入职|进厂)?")

# Relative date patterns (supports Arabic numerals and Chinese numerals)
_RECENT_MONTH_RE = re.compile(r"最近\s*(\d+|一|二|三|四|五|六|七|八|九|十)\s*个月(?:以来|之内|内)?")
_RECENT_YEAR_RE = re.compile(r"最近\s*(\d+|一|二|三|四|五|六|七|八|九|十)\s*年(?:以来|之内|内)?")

# Query type detection
_COUNT_RE = re.compile(r"(?:有多少|共多少|人数|几人|多少个|共计|总共|一共|统计|计数)")

# Name extraction (2-4 Chinese characters, excluding common non-name words)
_NAME_RE = re.compile(r"[一-龥]{2,4}")
_NAME_EXCLUDE = {
    "员工",
    "人员",
    "人事",
    "工厂",
    "公司",
    "部门",
    "车间",
    "科室",
    "班组",
    "团队",
    "职位",
    "岗位",
    "状态",
    "性别",
    "学历",
    "年龄",
    "工龄",
    "司龄",
    "厂龄",
    "入职",
    "离职",
    "试用",
    "合同",
    "工资",
    "薪资",
    "薪酬",
    "绩效",
    "考核",
    "培训",
    "招聘",
    "面试",
    "简历",
    "档案",
    "保险",
    "社保",
    "公积金",
    "福利",
    "假期",
    "请假",
    "加班",
    "调休",
    "出差",
    "报销",
    "预算",
    "成本",
    "费用",
    "利润",
    "收入",
    "支出",
    "资产",
    "负债",
    "股东",
    "董事",
    "监事",
    "经理",
    "主管",
    "专员",
    "助理",
    "秘书",
    "顾问",
    "总监",
    "厂长",
    "班长",
    "组长",
    "工程师",
    "操作员",
    "操作工",
    "文员",
    "会计",
    "出纳",
    "司机",
    "保安",
    "厨师",
    "保洁",
    "电工",
    "焊工",
    "钳工",
    "车工",
    "铣工",
    "磨工",
    "叉车工",
    "搬运工",
    "包装工",
    "技术员",
    "质检员",
    "安全员",
    "消防员",
    "仓管员",
    "物料员",
    "统计员",
    "计划员",
    "调度员",
    "采购员",
    "销售员",
    "业务员",
    "客服",
    "前台",
}


def _extract_department(text: str) -> str | None:
    """Extract department name from text."""
    m = _DEPARTMENT_RE.search(text)
    if m:
        return m.group(1)
    return None


def _extract_team(text: str) -> str | None:
    """Extract team name from text."""
    # Check explicit "班组" first
    m = re.search(r"([^，。；\n\s]{1,6})班组", text)
    if m:
        return m.group(1) + "班"
    # Check bare team patterns
    m = _TEAM_RE.search(text)
    if m:
        return m.group(1)
    return None


def _extract_position(text: str) -> str | None:
    """Extract position from text."""
    # Explicit prefix first
    m = _POSITION_WITH_PREFIX_RE.search(text)
    if m:
        return m.group(1)
    # Check known position keywords
    for pos in _POSITION_KEYWORDS:
        if pos in text:
            return pos
    return None


def _extract_status(text: str) -> str | None:
    """Extract employee status from text."""
    for kw, value in _STATUS_KEYWORDS.items():
        if kw in text:
            return value
    return None


def _extract_gender(text: str) -> str | None:
    """Extract gender from text."""
    for kw, value in _GENDER_KEYWORDS.items():
        if kw in text:
            return value
    return None


def _extract_education(text: str) -> str | None:
    """Extract education level from text."""
    for kw, value in _EDUCATION_KEYWORDS.items():
        if kw in text:
            return value
    return None


def _extract_political_status(text: str) -> str | None:
    """Extract political status from text."""
    for kw, value in _POLITICAL_STATUS_KEYWORDS.items():
        if kw in text:
            return value
    return None


def _extract_marital_status(text: str) -> str | None:
    """Extract marital status from text."""
    for kw, value in _MARITAL_STATUS_KEYWORDS.items():
        if kw in text:
            return value
    return None


def _extract_age_range(text: str) -> tuple[int | None, int | None]:
    """Extract age min and max from text."""
    age_min: int | None = None
    age_max: int | None = None

    m = _AGE_RANGE_RE.search(text)
    if m:
        age_min = int(m.group(1))
        age_max = int(m.group(2))
        return age_min, age_max

    m = _AGE_MIN_RE.search(text)
    if m:
        age_min = int(m.group(1))

    m = _AGE_MAX_RE.search(text)
    if m:
        age_max = int(m.group(1))

    return age_min, age_max


def _chinese_to_number(text: str) -> int | None:
    """Convert simple Chinese numerals to Arabic numbers."""
    mapping = {
        "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
        "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    }
    if text.isdigit():
        return int(text)
    return mapping.get(text)


def _extract_date_conditions(text: str) -> dict[str, date]:
    """Extract date range conditions from text.

    Returns a dict with keys like:
        hire_date_after, hire_date_before,
        factory_entry_date_after, factory_entry_date_before
    """
    conditions: dict[str, date] = {}
    today = date.today()

    # Skip date extraction if text is about birth year (handled separately)
    if "出生" in text:
        return conditions

    # Determine which date field is being referenced
    date_field = "hire_date"  # default
    if "进厂" in text or "入厂" in text:
        date_field = "factory_entry_date"
    elif "参加工作" in text or "工作" in text:
        date_field = "work_start_date"

    # Year after: "2020年后入职"
    m = _YEAR_AFTER_RE.search(text)
    if m:
        year = int(m.group(1))
        conditions[f"{date_field}_after"] = date(year, 1, 1)

    # Year before: "2020年前入职"
    m = _YEAR_BEFORE_RE.search(text)
    if m:
        year = int(m.group(1))
        conditions[f"{date_field}_before"] = date(year, 12, 31)

    # Exact year: "2020年入职"
    if f"{date_field}_after" not in conditions and f"{date_field}_before" not in conditions:
        m = _YEAR_EXACT_RE.search(text)
        if m:
            year = int(m.group(1))
            conditions[f"{date_field}_after"] = date(year, 1, 1)
            conditions[f"{date_field}_before"] = date(year, 12, 31)

    # Recent months: "最近3个月入职" or "最近三个月入职"
    m = _RECENT_MONTH_RE.search(text)
    if m:
        num = _chinese_to_number(m.group(1))
        if num:
            conditions[f"{date_field}_after"] = today - timedelta(days=num * 30)

    # Recent years: "最近1年入职" or "最近一年入职"
    m = _RECENT_YEAR_RE.search(text)
    if m:
        num = _chinese_to_number(m.group(1))
        if num:
            conditions[f"{date_field}_after"] = today - timedelta(days=num * 365)

    return conditions


def _extract_birth_year_conditions(text: str) -> dict[str, int]:
    """Extract birth year range conditions from text."""
    conditions: dict[str, int] = {}

    if "出生" not in text:
        return conditions

    # Year after: "1990年后出生"
    m = _YEAR_AFTER_RE.search(text)
    if m:
        conditions["birth_year_min"] = int(m.group(1))

    # Year before: "1990年前出生"
    m = _YEAR_BEFORE_RE.search(text)
    if m:
        conditions["birth_year_max"] = int(m.group(1))

    # Exact year: "1990年出生"
    if "birth_year_min" not in conditions and "birth_year_max" not in conditions:
        m = _YEAR_EXACT_RE.search(text)
        if m:
            conditions["birth_year_min"] = int(m.group(1))
            conditions["birth_year_max"] = int(m.group(1))

    return conditions


def _detect_query_type(text: str) -> str:
    """Detect if user wants a count or a list."""
    if _COUNT_RE.search(text):
        return "count"
    return "list"


def _extract_names(text: str) -> list[str]:
    """Extract possible Chinese person names from text."""
    matches = _NAME_RE.findall(text)
    return [m for m in matches if m not in _NAME_EXCLUDE]


def _has_employee_query_keywords(text: str) -> bool:
    """Check if text contains any employee-related query keywords."""
    keywords = [
        "员工", "人员", "人事", "名单", "人", "职工", "同事",
        "部门", "班组", "职位", "岗位", "状态", "性别", "学历",
        "年龄", "入职", "进厂", "工龄", "司龄", "厂龄",
        "党员", "群众", "已婚", "未婚",
        "工程师", "经理", "主管", "专员", "操作员", "文员",
        "统计", "查询", "查找", "搜索",
    ]
    return any(kw in text for kw in keywords)


def parse_employee_query(text: str) -> EmployeeQueryCriteria | None:
    """Parse natural language text into structured employee query criteria.

    Returns None if the text does not appear to be an employee query.
    """
    if not _has_employee_query_keywords(text):
        return None

    criteria = EmployeeQueryCriteria()
    criteria.query_type = _detect_query_type(text)

    # Extract department
    dept = _extract_department(text)
    if dept:
        criteria.filters["department"] = dept

    # Extract team
    team = _extract_team(text)
    if team:
        criteria.filters["team"] = team

    # Extract position
    position = _extract_position(text)
    if position:
        criteria.filters["position"] = position

    # Extract status
    status = _extract_status(text)
    if status:
        criteria.filters["status"] = status

    # Extract gender
    gender = _extract_gender(text)
    if gender:
        criteria.filters["gender"] = gender

    # Extract education
    education = _extract_education(text)
    if education:
        criteria.filters["education"] = education

    # Extract political status
    political = _extract_political_status(text)
    if political:
        criteria.filters["political_status"] = political

    # Extract marital status
    marital = _extract_marital_status(text)
    if marital:
        criteria.filters["marital_status"] = marital

    # Extract age range
    age_min, age_max = _extract_age_range(text)
    if age_min is not None:
        criteria.filters["age_min"] = age_min
    if age_max is not None:
        criteria.filters["age_max"] = age_max

    # Extract date conditions
    date_conditions = _extract_date_conditions(text)
    criteria.filters.update(date_conditions)

    # Extract birth year conditions
    birth_conditions = _extract_birth_year_conditions(text)
    criteria.filters.update(birth_conditions)

    # If no structured filters were found, try name extraction as fallback
    if not criteria.filters:
        names = _extract_names(text)
        if names:
            criteria.name_keyword = names[0]
        else:
            return None

    return criteria


def describe_filters(filters: dict[str, Any]) -> str:
    """Convert filter dict to a human-readable Chinese description."""
    if not filters:
        return "全厂"

    parts: list[str] = []
    mapping: dict[str, str] = {
        "department": "部门为{}",
        "team": "班组为{}",
        "position": "职位含{}",
        "status": "状态为{}",
        "gender": "性别为{}",
        "education": "学历为{}",
        "political_status": "政治面貌为{}",
        "marital_status": "婚姻状况为{}",
        "age_min": "年龄在{}岁以上",
        "age_max": "年龄在{}岁以下",
        "birth_year_min": "{}年后出生",
        "birth_year_max": "{}年前出生",
        "hire_date_after": "{}年后入职",
        "hire_date_before": "{}年前入职",
        "factory_entry_date_after": "{}年后进厂",
        "factory_entry_date_before": "{}年前进厂",
        "work_start_date_after": "{}年后参加工作",
        "work_start_date_before": "{}年前参加工作",
    }

    for key, value in filters.items():
        if value is None:
            continue
        if key in mapping:
            # Format date values nicely
            if isinstance(value, date):
                parts.append(mapping[key].format(value.year))
            else:
                parts.append(mapping[key].format(value))

    return "、".join(parts) if parts else "全厂"
