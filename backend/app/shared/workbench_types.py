"""工作台聚合 DTO（跨模块契约）。

首页工作台需要把「审核待办」与「我参与的流程」从各业务模块聚到一起展示。
全仓没有统一待办表，因此由 ``platform/workbench`` 逐模块调用各模块的
``public_api`` 取数，双方共用本文件的 DTO，避免平台层依赖模块内部 schema。

约定：
- ``platform/workbench`` 只 import 各模块 ``public_api``，不碰 service/repository/models；
- 各模块取数函数返回 ``WorkbenchSourceResult``，失败由平台层统一降级；
- 前端路由由模块自己拼好后放进 ``path``，平台层不做路由拼接。
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── 判定依据 ─────────────────────────────────────────────────────
#: 精确：当前环节处理人（或可操作人）就是我
MATCH_PERSON = "person"
#: 兜底：单据处于待审状态且我具备对应审批权限码（判不出具体人时使用）
MATCH_ROLE = "role"

MATCH_KIND_LABELS: dict[str, str] = {
    MATCH_PERSON: "待我审批",
    MATCH_ROLE: "同角色待办",
}

# ── 模块 key / 名称（与 app/shared/module_registry.py 的模块码一致）──
MODULE_QUALITY = "quality"
MODULE_SAFETY = "safety"

# ── 取数上限 ─────────────────────────────────────────────────────
#: 单数据源返回条数上限（首页只展示前几条，更详细的内容去模块列表页看）
SOURCE_ITEM_LIMIT = 5
#: 单数据源候选扫描上限：内存匹配型数据源（偏差 / 隐患）一次最多载入的行数
CANDIDATE_SCAN_LIMIT = 300
#: 接口查询参数上限
OVERVIEW_ITEM_LIMIT_MAX = 20


@dataclass(frozen=True, slots=True)
class WorkbenchItem:
    """一条待办或流程事项。

    ``id`` 用字符串（UUID 的 str 形式），避免跨模块传递 UUID 类型时前端序列化差异。
    ``path`` 为 ``None`` 表示该单据暂无可跳转的前端页面（如尚未建页面的 CAPA）。
    """

    id: str
    source: str
    module_key: str
    module_label: str
    doc_type_label: str
    title: str
    doc_no: str | None = None
    status: str = ""
    status_label: str = ""
    step_label: str | None = None
    match_kind: str = MATCH_ROLE
    age_days: int | None = None
    overdue: bool = False
    path: str | None = None
    my_roles: tuple[str, ...] = field(default_factory=tuple)

    @property
    def match_kind_label(self) -> str:
        return MATCH_KIND_LABELS.get(self.match_kind, self.match_kind)


@dataclass(slots=True)
class WorkbenchSourceResult:
    """单个数据源的取数结果。

    ``has_more`` 表示源内还有超出 ``items`` 的未返回条目（首页只取前 N 条），
    前端据此把计数显示成「N+」而不是谎报总数。
    """

    items: list[WorkbenchItem] = field(default_factory=list)
    has_more: bool = False
