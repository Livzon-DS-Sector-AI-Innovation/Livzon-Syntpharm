"""质量管理模块 — 公共 API。

供其他模块（当前为 ``platform/workbench`` 首页工作台）调用的稳定接口。
不要直接 import quality 模块内部的 ``service`` / ``repository`` / ``models``，
实现细节统一放在 ``qms/workbench_query.py``，本文件只做导出。
"""

from app.modules.quality.qms.workbench_query import (
    list_capa_todos,
    list_deviation_processes,
    list_deviation_todos,
    list_inspection_processes,
    list_inspection_todos,
)

__all__ = [
    "list_deviation_todos",
    "list_deviation_processes",
    "list_inspection_todos",
    "list_inspection_processes",
    "list_capa_todos",
]
