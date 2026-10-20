"""权限目录树构建（角色管理界面渲染用）。

树结构：模块 → 资源 → 权限码（叶子）。
数据来源：registry 的权限码注册表（ALL_PERMISSIONS）与业务模块清单（BUSINESS_MODULES）。
业务模块的权限码接入后树会自动生长——只需往 ALL_PERMISSIONS 里加声明。
"""

from collections import Counter
from typing import Any

from app.platform.permission.registry import (
    ALL_PERMISSIONS,
    API_BINDINGS,
    PLATFORM_DOMAIN_LABEL,
    RESOURCE_LABELS,
    PermissionDef,
)
from app.shared.module_registry import BUSINESS_MODULES

_PLATFORM_MODULE = "platform"


def _permission_node(definition: PermissionDef, binding_counts: Counter[str]) -> dict[str, Any]:
    return {
        "key": f"perm:{definition.code}",
        "title": definition.name,
        "type": "permission",
        "code": definition.code,
        "kind": None,
        "status": "active",
        "description": definition.description or None,
        "binding_count": binding_counts.get(definition.code, 0),
        "disabled": False,
        "children": [],
    }


def _module_node(
    module_code: str,
    module_name: str,
    kind: str,
    resources: dict[str, list[PermissionDef]],
    binding_counts: Counter[str],
) -> dict[str, Any]:
    resource_nodes: list[dict[str, Any]] = []
    for resource_code, definitions in resources.items():
        resource_nodes.append(
            {
                "key": f"resource:{module_code}:{resource_code}",
                "title": RESOURCE_LABELS.get(resource_code, resource_code),
                "type": "resource",
                "code": resource_code,
                "kind": None,
                "status": None,
                "description": None,
                "binding_count": 0,
                "disabled": False,
                "children": [_permission_node(d, binding_counts) for d in definitions],
            }
        )
    return {
        "key": f"module:{module_code}",
        "title": module_name,
        "type": "module",
        "code": module_code,
        "kind": kind,
        "status": None,
        "description": None,
        "binding_count": 0,
        "disabled": False,
        "children": resource_nodes,
    }


def build_permission_tree() -> tuple[list[dict[str, Any]], int]:
    """构建权限目录树。

    返回 (tree, total_permissions)。模块顺序：平台域 → 已接入的业务模块 → 未接入的业务模块（置灰）。
    """
    grouped: dict[str, dict[str, list[PermissionDef]]] = {}
    for definition in ALL_PERMISSIONS:
        grouped.setdefault(definition.module, {}).setdefault(definition.resource, []).append(definition)

    binding_counts: Counter[str] = Counter(binding.permission_code for binding in API_BINDINGS)

    tree: list[dict[str, Any]] = []
    if _PLATFORM_MODULE in grouped:
        tree.append(
            _module_node(
                _PLATFORM_MODULE,
                PLATFORM_DOMAIN_LABEL,
                "platform",
                grouped[_PLATFORM_MODULE],
                binding_counts,
            )
        )

    # 已接入权限码的业务模块
    for module in BUSINESS_MODULES:
        if module.code in grouped:
            tree.append(_module_node(module.code, module.name, "business", grouped[module.code], binding_counts))

    # 尚未接入权限码的业务模块（置灰占位，提示"待接入"而不是"没有"）
    for module in BUSINESS_MODULES:
        if module.code not in grouped:
            tree.append(
                {
                    "key": f"module:{module.code}",
                    "title": module.name,
                    "type": "module",
                    "code": module.code,
                    "kind": "business",
                    "status": None,
                    "description": "该模块的权限码尚未登记（存量接口接入阶段完成）",
                    "binding_count": 0,
                    "disabled": True,
                    "children": [],
                }
            )

    return tree, len(ALL_PERMISSIONS)
