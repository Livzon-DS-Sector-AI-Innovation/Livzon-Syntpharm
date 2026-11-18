"""注册表：每模块两个内置角色 + 一个模块管理入口码（委派式权限管理）。"""

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


def test_each_module_has_head_and_manager_roles() -> None:
    for code in MODULE_CODES:
        head = _role(f"{code}:head")
        manager = _role(f"{code}:manager")

        assert head.role_type == "head"
        assert head.module_code == code
        assert head.category == "module"

        assert manager.role_type == "manager"
        assert manager.module_code == code
        assert manager.category == "module"


def test_super_admin_role_type_is_system() -> None:
    super_role = _role("super_admin")
    assert super_role.role_type == "system"
    assert super_role.is_superuser is True


def test_head_has_all_module_business_codes_and_admin_entry() -> None:
    for code in MODULE_CODES:
        codes = set(BUILTIN_ROLE_PERMISSIONS[f"{code}:head"])
        module_codes = {p.code for p in ALL_PERMISSIONS if p.module == code and p.code not in ADMIN_ENTRY_CODES}

        assert module_codes <= codes, f"{code}:head 缺少本模块业务权限码"
        assert f"{code}:admin:read" in codes, "模块负责人应能进入模块配置页"
        # 人员查询是唯一的平台级单点能力：负责人在角色/授权页选人需要它，
        # 其余权限码必须限定在本模块内。
        assert PERSON_LOOKUP_CODE in codes, "模块负责人需要在授权页选人"
        assert all(item.startswith(f"{code}:") for item in codes - {PERSON_LOOKUP_CODE})


def test_manager_has_same_permissions_as_head() -> None:
    """2026-11-18 口径：负责人与管理人**权限一致**，区别只在任命关系。"""
    for code in MODULE_CODES:
        assert BUILTIN_ROLE_PERMISSIONS[f"{code}:manager"] == BUILTIN_ROLE_PERMISSIONS[f"{code}:head"]


def test_admin_entry_codes_are_one_per_module() -> None:
    assert len(MODULE_ADMIN_PERMISSIONS) == len(MODULE_CODES)
    assert ADMIN_ENTRY_CODES == {f"{code}:admin:read" for code in MODULE_CODES}
    # 每模块恰好一个管理入口被 head 持有
    for code in MODULE_CODES:
        held = [c for c in BUILTIN_ROLE_PERMISSIONS[f"{code}:head"] if c in ADMIN_ENTRY_CODES]
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
    """角色编码是两段（module:head），权限码是三段，两者形态上不重叠。"""
    role_codes = {r.code for r in ALL_BUILTIN_ROLES}
    permission_codes = {p.code for p in ALL_PERMISSIONS}
    assert not (role_codes & permission_codes)
