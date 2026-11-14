"""Shared org-scope constants for HR org/people tests.

The production code no longer hardcodes the company scope (audit #10): it is
read from ``core.module_settings`` and fails closed when unset. Tests that
exercise pure domain helpers pass this explicit scope instead of relying on a
module-level default.
"""

from app.modules.hr.org_domain import OrgScope

ROOT_ID = "od-9c7089e0d3edc7822c0650a9b2ff4318"
ROOT_NAME = "珠海保税区丽珠合成制药有限公司"

DEFAULT_ORG_SCOPE = OrgScope(department_id=ROOT_ID, department_name=ROOT_NAME)

# 旧测试沿用的名称，避免大范围重命名。
IN_SCOPE_COMPANY_ID = ROOT_ID
IN_SCOPE_COMPANY_NAME = ROOT_NAME

__all__ = [
    "DEFAULT_ORG_SCOPE",
    "IN_SCOPE_COMPANY_ID",
    "IN_SCOPE_COMPANY_NAME",
    "ROOT_ID",
    "ROOT_NAME",
]
