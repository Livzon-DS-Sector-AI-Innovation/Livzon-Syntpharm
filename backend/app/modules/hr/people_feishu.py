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
    "open_id",
    "name",
    "mobile",
    "email",
    "enterprise_email",
    "enterprise_email_aliases",
    "gender",
    "description",
    "avatar",
    "background_image",
    "geo_name",
    "active_status",
    "is_resigned",
    "resign_time",
    "is_admin",
    "is_primary_admin",
    "data_source",
    "job_number",
    "job_title",
    "join_date",
    "employment_type",
    "staff_status",
    "work_country_or_region",
    "work_place",
    "work_station",
    "extension_number",
    "dotted_line_leader_ids",
    "resign_date",
    "resign_type",
    "resign_reason",
    "resign_remark",
    "positions",
    "job_level",
    "job_family",
    "employee_order_in_departments",
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
