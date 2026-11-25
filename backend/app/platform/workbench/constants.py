"""工作台的业务口径常量。

这些是「待办判定 + 中文展示文案 + 取数上限」的业务规则，归平台层的工作台能力；
``app/shared/workbench_types.py`` 只保留跨模块 DTO（字段定义），不放业务取值。
"""

from __future__ import annotations

# ── 判定依据 ─────────────────────────────────────────────────────
#: 精确：当前环节处理人（或可操作人）就是我
MATCH_PERSON = "person"
#: 兜底：单据处于待审状态且我具备对应审批权限码（判不出具体人时使用）
MATCH_ROLE = "role"

MATCH_KIND_LABELS: dict[str, str] = {
    MATCH_PERSON: "待我审批",
    MATCH_ROLE: "同角色待办",
}


def match_kind_label(match_kind: str) -> str:
    """判定依据的中文展示名；未知值原样返回。"""
    return MATCH_KIND_LABELS.get(match_kind, match_kind)


# ── 模块 key（与 app/shared/module_registry.py 的模块码一致）────────
MODULE_QUALITY = "quality"
MODULE_SAFETY = "safety"

# ── 取数上限 ─────────────────────────────────────────────────────
#: 单数据源返回条数上限（首页只展示前几条，更详细的内容去模块列表页看）
SOURCE_ITEM_LIMIT = 5
#: 单数据源候选扫描上限：内存匹配型数据源（偏差 / 隐患）一次最多载入的行数
CANDIDATE_SCAN_LIMIT = 300
#: 接口查询参数上限
OVERVIEW_ITEM_LIMIT_MAX = 20

__all__ = [
    "CANDIDATE_SCAN_LIMIT",
    "MATCH_KIND_LABELS",
    "MATCH_PERSON",
    "MATCH_ROLE",
    "MODULE_QUALITY",
    "MODULE_SAFETY",
    "OVERVIEW_ITEM_LIMIT_MAX",
    "SOURCE_ITEM_LIMIT",
    "match_kind_label",
]
