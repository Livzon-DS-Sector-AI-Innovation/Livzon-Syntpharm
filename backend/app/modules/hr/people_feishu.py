"""Feishu directory fetcher for the personnel mirror (ticket #198).

Reuses the department fetcher's authenticated, retrying HTTP machinery and
posts ``directory/v1/employees/mget`` with the retained field set. Secrets are
never logged.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.org_feishu import FeishuOrgDepartmentFetcher, load_hr_platform_credentials

EMPLOYEE_REQUIRED_FIELDS = (
    "base_info.employee_id",
    "base_info.name",
    "base_info.mobile",
    "base_info.email",
    "base_info.enterprise_email",
    "base_info.enterprise_email_aliases",
    "base_info.gender",
    "base_info.description",
    "base_info.avatar",
    "base_info.background_image",
    "base_info.geo_name",
    "base_info.active_status",
    "base_info.is_resigned",
    "base_info.resign_time",
    "base_info.is_admin",
    "base_info.is_primary_admin",
    "base_info.data_source",
    "base_info.departments",
    "base_info.employee_order_in_departments",
    "base_info.department_path_infos",
    "base_info.dotted_line_leader_ids",
    "work_info.job_number",
    "work_info.job_title",
    "work_info.join_date",
    "work_info.employment_type",
    "work_info.staff_status",
    "work_info.work_country_or_region",
    "work_info.work_place",
    "work_info.work_station",
    "work_info.extension_number",
    "work_info.positions",
    "work_info.job_level",
    "work_info.job_family",
    "work_info.resign_date",
    "work_info.resign_type",
    "work_info.resign_reason",
    "work_info.resign_remark",
)


class FeishuEmployeeProfileFetcher(FeishuOrgDepartmentFetcher):
    """Single-batch directory employee mget call."""

    async def fetch_employees(self, open_ids: list[str]) -> list[dict[str, Any]]:
        if not open_ids:
            return []
        data = await self._request(
            "POST",
            "/directory/v1/employees/mget",
            params={
                "employee_id_type": "open_id",
                "department_id_type": "open_department_id",
            },
            json={
                "employee_ids": open_ids,
                "required_fields": list(EMPLOYEE_REQUIRED_FIELDS),
            },
        )
        items = data.get("employees")
        if not isinstance(items, list):
            return []
        return [item for item in items if isinstance(item, dict)]


async def build_default_employee_fetcher(session: AsyncSession) -> FeishuEmployeeProfileFetcher:
    app_id, app_secret = await load_hr_platform_credentials(session)
    return FeishuEmployeeProfileFetcher(app_id=app_id, app_secret=app_secret)
