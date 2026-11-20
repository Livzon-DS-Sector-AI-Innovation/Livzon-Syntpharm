"""注册表：每模块两个内置角色 + 一个模块管理入口码（委派式权限管理）。"""

from app.platform.permission.constants import RETIRED_ROLE_TYPES
from app.platform.permission.registry import (
    ADMIN_ENTRY_CODES,
    ALL_BUILTIN_ROLES,
    ALL_PERMISSIONS,
    BUILTIN_ROLE_PERMISSIONS,
    MODULE_ADMIN_PERMISSIONS,
    PERSON_LOOKUP_CODE,
)
from app.shared.module_registry import BUSINESS_MODULES

MODULE_CODES = [m.code for m in BUSINESS_MODULES]


def _role(code: str):
    return next(r for r in ALL_BUILTIN_ROLES if r.code == code)


def test_each_module_has_owner_and_delegate_roles() -> None:
    for code in MODULE_CODES:
        owner = _role(f"{code}:owner")
        delegate = _role(f"{code}:delegate")

        assert owner.role_type == "owner"
        assert owner.module_code == code
        assert owner.category == "module"
        assert owner.name.endswith("负责人")

        assert delegate.role_type == "delegate"
        assert delegate.module_code == code
        assert delegate.category == "module"
        assert delegate.name.endswith("代表")


def test_super_admin_role_type_is_system() -> None:
    super_role = _role("super_admin")
    assert super_role.role_type == "system"
    assert super_role.is_superuser is True


def test_registry_has_no_retired_role_types() -> None:
    """历史类型（head / manager）已由 owner / delegate 取代，注册表不得再声明。"""
    assert not {role.role_type for role in ALL_BUILTIN_ROLES} & RETIRED_ROLE_TYPES


def test_owner_has_all_module_business_codes_and_admin_entry() -> None:
    for code in MODULE_CODES:
        codes = set(BUILTIN_ROLE_PERMISSIONS[f"{code}:owner"])
        module_codes = {p.code for p in ALL_PERMISSIONS if p.module == code and p.code not in ADMIN_ENTRY_CODES}

        assert module_codes <= codes, f"{code}:owner 缺少本模块业务权限码"
        assert f"{code}:admin:read" in codes, "模块负责人应能进入模块配置页"
        # 人员查询是唯一的平台级单点能力：负责人在角色/授权页选人需要它，
        # 其余权限码必须限定在本模块内。
        assert PERSON_LOOKUP_CODE in codes, "模块负责人需要在授权页选人"
        assert all(item.startswith(f"{code}:") for item in codes - {PERSON_LOOKUP_CODE})


def test_delegate_has_same_permissions_as_owner() -> None:
    """2026-11-19 口径：负责人与代表**权限一致**，区别只在任命关系。"""
    for code in MODULE_CODES:
        assert BUILTIN_ROLE_PERMISSIONS[f"{code}:delegate"] == BUILTIN_ROLE_PERMISSIONS[f"{code}:owner"]


def test_admin_entry_codes_are_one_per_module() -> None:
    assert len(MODULE_ADMIN_PERMISSIONS) == len(MODULE_CODES)
    assert ADMIN_ENTRY_CODES == {f"{code}:admin:read" for code in MODULE_CODES}
    # 每模块恰好一个管理入口被 owner 持有
    for code in MODULE_CODES:
        held = [c for c in BUILTIN_ROLE_PERMISSIONS[f"{code}:owner"] if c in ADMIN_ENTRY_CODES]
        assert held == [f"{code}:admin:read"]


def test_role_permission_mapping_references_known_codes() -> None:
    """角色权限映射只能引用已登记权限码与已声明角色（CI 门禁同口径）。"""
    role_codes = {r.code for r in ALL_BUILTIN_ROLES}
    permission_codes = {p.code for p in ALL_PERMISSIONS}

    assert set(BUILTIN_ROLE_PERMISSIONS) <= role_codes
    for role_code, codes in BUILTIN_ROLE_PERMISSIONS.items():
        unknown = set(codes) - permission_codes
        assert not unknown, f"{role_code} 引用了未登记的权限码：{unknown}"


def test_module_role_codes_do_not_collide_with_permission_codes() -> None:
    """角色编码是两段（module:owner），权限码是三段，两者形态上不重叠。"""
    role_codes = {r.code for r in ALL_BUILTIN_ROLES}
    permission_codes = {p.code for p in ALL_PERMISSIONS}
    assert not (role_codes & permission_codes)
