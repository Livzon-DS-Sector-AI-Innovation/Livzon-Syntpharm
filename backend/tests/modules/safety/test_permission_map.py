"""safety 路由权限码解析（`permission_map`）回归测试。

背景：新增资源若忘了进 `SAFETY_RESOURCE_CODES`，`resolve_code` 会回落到
`safety:module:read`，写接口实际只校验只读码（PR #183 的 `hazard-categories`
即为此类回归）。这里把「表 → 解析结果」与「registry 绑定 → 解析结果」两个
方向都钉住。
"""

from app.modules.safety.api.permission_map import SAFETY_RESOURCE_CODES, resolve_code
from app.platform.permission.registry import API_BINDINGS

_SAFETY_PREFIX = "/api/v1/safety/"


def test_each_resource_resolves_to_its_own_codes() -> None:
    """表里每个资源段都必须解析出自己那对码，不能落回模块粗码。"""
    for resource, (read_code, write_code) in SAFETY_RESOURCE_CODES.items():
        assert resolve_code("GET", f"{_SAFETY_PREFIX}{resource}") == read_code
        if read_code != write_code:
            assert resolve_code("POST", f"{_SAFETY_PREFIX}{resource}") == write_code
            assert resolve_code("PUT", f"{_SAFETY_PREFIX}{resource}/abc") == write_code
            assert resolve_code("DELETE", f"{_SAFETY_PREFIX}{resource}/abc") == write_code


def test_hazard_categories_shares_hazard_codes() -> None:
    """隐患类别字典与隐患共用权限码（与 registry 绑定一致）。"""
    assert resolve_code("GET", f"{_SAFETY_PREFIX}hazard-categories") == "safety:hazard:read"
    assert resolve_code("POST", f"{_SAFETY_PREFIX}hazard-categories") == "safety:hazard:manage"


def test_registry_bindings_agree_with_resolved_codes() -> None:
    """registry 里每条 safety 绑定登记的码，必须等于运行时解析出的码。

    两套口径一旦分叉，授权页展示与真实校验就会不一致；`check_permissions.py`
    只校验绑定是否存在，不校验码是否一致，故由本用例兜住。
    """
    safety_bindings = [b for b in API_BINDINGS if b.route_template.startswith(_SAFETY_PREFIX)]
    assert safety_bindings, "safety 绑定未登记，registry 装配可能已损坏"

    mismatched = [
        (b.method, b.route_template, b.permission_code, resolve_code(b.method, b.route_template))
        for b in safety_bindings
        if resolve_code(b.method, b.route_template) != b.permission_code
    ]
    assert not mismatched, f"绑定码与解析结果不一致：{mismatched[:10]}"


def test_unknown_resource_falls_back_to_module_codes() -> None:
    """未登记的资源仍回落到模块粗码（保留兜底语义，避免直接 500）。"""
    assert resolve_code("GET", f"{_SAFETY_PREFIX}unknown-resource") == "safety:module:read"
    assert resolve_code("POST", f"{_SAFETY_PREFIX}unknown-resource") == "safety:module:read"
