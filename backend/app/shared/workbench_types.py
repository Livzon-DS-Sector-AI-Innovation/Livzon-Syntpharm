"""工作台聚合 DTO（跨模块契约）。

首页工作台需要把「审核待办」与「我参与的流程」从各业务模块聚到一起展示。
全仓没有统一待办表，因此由 ``platform/workbench`` 逐模块调用各模块的
``public_api`` 取数，双方共用本文件的 DTO，避免平台层依赖模块内部 schema。

约定：
- ``platform/workbench`` 只 import 各模块 ``public_api``，不碰 service/repository/models；
- 各模块取数函数返回 ``WorkbenchSourceResult``，失败由平台层统一降级；
- 前端路由由模块自己拼好后放进 ``path``，平台层不做路由拼接。

本文件只放 DTO 字段定义；判定码、中文文案与取数上限属工作台业务规则，
见 ``app/platform/workbench/constants.py``。
"""

from __future__ import annotations

from dataclasses import dataclass, field


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
    #: 判定依据，取值见 ``app/platform/workbench/constants.py``（person / role）
    match_kind: str = ""
    age_days: int | None = None
    overdue: bool = False
    path: str | None = None
    my_roles: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True)
class WorkbenchSourceResult:
    """单个数据源的取数结果。

    ``has_more`` 表示源内还有超出 ``items`` 的未返回条目（首页只取前 N 条），
    前端据此把计数显示成「N+」而不是谎报总数。
    """

    items: list[WorkbenchItem] = field(default_factory=list)
    has_more: bool = False
