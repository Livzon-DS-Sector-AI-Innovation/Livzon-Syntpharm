"""权限树中文说明与接口清单懒加载的单元测试。

覆盖四件容易回归的事：
1. 515 个权限码都必须有中文说明（模板兜底，不依赖逐条手写）；
2. 手写说明优先于模板生成；
3. 资源节点标题必须是中文，且与说明里的资源段同源（不能回到英文资源码）；
4. 单码接口清单只取本码绑定、排序稳定、未知码返回空。
"""

from collections.abc import Iterator
from typing import Any

from app.platform.permission.registry import ALL_PERMISSIONS, PERMISSIONS_BY_CODE, PermissionDef
from app.platform.permission.service.catalog import build_api_binding_items, build_permission_tree
from app.platform.permission.service.description import build_permission_summary, build_resource_label


def _walk(nodes: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    for node in nodes:
        yield node
        yield from _walk(node.get("children") or [])


def _leaves() -> list[dict[str, Any]]:
    tree, _ = build_permission_tree()
    return [node for node in _walk(tree) if node["type"] == "permission"]


def test_every_permission_leaf_has_chinese_summary() -> None:
    leaves = _leaves()
    assert len(leaves) == len(ALL_PERMISSIONS)

    for leaf in leaves:
        summary = leaf["description"]
        assert summary, f"{leaf['code']} 缺少说明"
        assert any("\u4e00" <= char <= "\u9fff" for char in summary), f"{leaf['code']} 说明无中文：{summary}"
        # 手写说明可以是任意措辞，模板生成的必须是「模块 · 资源 — 动作」三段式
        if not PERMISSIONS_BY_CODE[leaf["code"]].description:
            assert " · " in summary, f"{leaf['code']} 说明缺少模块/资源段：{summary}"
            assert " — " in summary, f"{leaf['code']} 说明缺少动作段：{summary}"


def test_handwritten_description_wins() -> None:
    leaf = next(node for node in _leaves() if node["code"] == "production:module:read")
    assert leaf["description"] == "模块菜单可见性与页面准入（接口级权限后续追加）"


def test_summary_strips_action_prefix_when_resource_label_missing() -> None:
    # 未登记中文资源名时，说明应从「查看幽灵资源」剥出「幽灵资源」而不是回落英文资源码
    definition = PermissionDef("x:ghost-res:read", "查看幽灵资源", "x", "ghost-res", "read")
    summary = build_permission_summary(definition)

    assert summary.endswith("幽灵资源 — 可查看列表与详情")
    assert definition.resource not in summary


def test_resource_label_prefers_module_prefixed_entry() -> None:
    # RESOURCE_LABELS 里 quality 模块用「模块:资源码」写法，裸键 capa 并不存在；
    # 查找必须先试带前缀的键，否则资源节点会显示英文资源码
    assert build_resource_label("quality", "capa") == "CAPA管理"


def test_resource_label_falls_back_to_derived_name() -> None:
    definition = PermissionDef("x:ghost-res:read", "查看幽灵资源", "x", "ghost-res", "read")
    assert build_resource_label("x", "ghost-res", (definition,)) == "幽灵资源"


def test_resource_label_uses_mode_across_definitions() -> None:
    # 同一资源下多个权限名剥掉动作前缀后应一致；括号里的动作清单要被清掉
    first = PermissionDef("x:multi:read", "查看多动作资源", "x", "multi", "read")
    second = PermissionDef("x:multi:manage", "管理多动作资源（创建/修改/删除）", "x", "multi", "manage")
    third = PermissionDef("x:multi:export", "导出多动作资源", "x", "multi", "export")

    assert build_resource_label("x", "multi", (first, second, third)) == "多动作资源"


def test_resource_label_handles_dash_naming() -> None:
    definition = PermissionDef("x:dash:read", "幽灵资源管理 - 查看", "x", "dash", "read")
    assert build_resource_label("x", "dash", (definition,)) == "幽灵资源管理"


def test_resource_label_falls_back_to_code_when_nothing_derived() -> None:
    definition = PermissionDef("x:zzz:read", "zzz", "x", "zzz", "read")
    assert build_resource_label("x", "zzz", (definition,)) == "zzz"


def test_tree_resource_nodes_have_chinese_titles() -> None:
    tree, _ = build_permission_tree()
    resources = [node for node in _walk(tree) if node["type"] == "resource"]

    assert resources, "权限树应包含资源节点"
    for node in resources:
        assert any("\u4e00" <= char <= "\u9fff" for char in node["title"]), f"{node['code']} 资源标题无中文"
        assert node["title"] != node["code"], f"{node['code']} 资源标题仍是英文资源码"


def test_resource_title_matches_summary_segment() -> None:
    # 资源节点标题与叶子说明里的资源段共用 build_resource_label，两处不能漂移
    tree, _ = build_permission_tree()
    for node in _walk(tree):
        if node["type"] != "resource":
            continue
        _, module, resource = node["key"].split(":", 2)
        assert node["title"] == build_resource_label(module, resource)


def test_summary_uses_module_label_for_platform() -> None:
    definition = PermissionDef("platform:x:read", "查看配置", "platform", "config", "read")
    assert build_permission_summary(definition) == "平台管理 · 平台配置 — 可查看列表与详情"


def test_summary_keeps_unknown_action_readable() -> None:
    definition = PermissionDef("x:y:weird", "奇招", "x", "y", "weird")
    assert "可执行 weird 操作" in build_permission_summary(definition)


def test_build_api_binding_items_only_returns_own_bindings() -> None:
    code = "quality:static-data:read"
    items = build_api_binding_items(code)

    assert items, "该权限码应有绑定接口"
    assert all(set(item) == {"method", "route_template", "scope_required"} for item in items)
    assert items == sorted(items, key=lambda item: (item["route_template"], item["method"]))


def test_build_api_binding_items_unknown_code_is_empty() -> None:
    assert build_api_binding_items("no:such:code") == []


def test_unbound_permission_code_reports_zero_binding_count() -> None:
    leaves = {node["code"]: node for node in _leaves()}
    assert leaves["safety:training-record:read"]["binding_count"] == 0
    assert build_api_binding_items("safety:training-record:read") == []
