"""Feishu fetchers for the HR org department mirror (ticket #197).

Department tree comes from ``contact/v3/departments`` (names, ids, parents);
the detail fields come from ``directory/v1/departments/mget`` (leaders, counts,
path, enabled status, order weight, data source, custom fields).

Credentials are the platform 主 Bot app id/secret configured in HR system
settings (``hr.system_settings``), falling back to the deployment settings.
Secrets are never logged.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.secrets import decrypt_secret
from app.modules.hr.feishu_values import int_value
from app.modules.hr.org_domain import DEFAULT_SYNC_ROOT_DEPARTMENT_ID
from app.modules.hr.org_settings import load_org_scope
from app.platform.integrations.feishu.utils import OPEN_API_BASE_URL, get_tenant_access_token

logger = logging.getLogger(__name__)

APP_ID_SETTING = "FEISHU__PLATFORM__APP_ID"
APP_SECRET_SETTING = "FEISHU__PLATFORM__APP_SECRET"

_PAGE_SIZE = 50
_DETAIL_BATCH_SIZE = 50
_MAX_RETRIES = 3
_RETRY_BACKOFF_SECONDS = (1, 2, 4)

REQUIRED_DETAIL_FIELDS = (
    "department_id",
    "name",
    "parent_department_id",
    "enabled_status",
    "order_weight",
    "leaders",
    "department_count",
    "department_path_infos",
    "data_source",
    "custom_field_values",
    "delete_status",
    "has_child",
)


async def load_hr_platform_credentials(session: AsyncSession) -> tuple[str, str]:
    """Resolve the 主 Bot credentials from HR settings, then deployment env."""
    app_id = ""
    app_secret = ""
    result = await session.execute(
        text(
            "SELECT key, value FROM hr.system_settings WHERE key IN (:app_id_key, :app_secret_key)",
        ),
        {"app_id_key": APP_ID_SETTING, "app_secret_key": APP_SECRET_SETTING},
    )
    stored = {row[0]: row[1] for row in result.fetchall()}

    raw_app_id = stored.get(APP_ID_SETTING)
    if raw_app_id:
        app_id = str(raw_app_id).strip()

    raw_secret = stored.get(APP_SECRET_SETTING)
    if raw_secret:
        try:
            app_secret = decrypt_secret(str(raw_secret)).strip()
        except RuntimeError:
            logger.warning("HR 组织同步：飞书 App Secret 解密失败，回退到部署配置")

    settings = get_settings()
    if not app_id:
        app_id = settings.feishu.platform.app_id
    if not app_secret:
        app_secret = settings.feishu.platform.app_secret

    if not app_id or not app_secret:
        raise RuntimeError("HR 组织同步未配置飞书平台应用凭证（主 Bot App ID / App Secret）")
    return app_id, app_secret


class FeishuOrgDepartmentFetcher:
    """Two-level contact walk + directory mget detail fetch."""

    def __init__(
        self,
        *,
        app_id: str,
        app_secret: str,
        root_department_id: str = DEFAULT_SYNC_ROOT_DEPARTMENT_ID,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        self._root_department_id = root_department_id
        self._client = client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=OPEN_API_BASE_URL,
                timeout=httpx.Timeout(20.0, connect=5.0),
            )
        return self._client

    async def _token(self) -> str:
        return await get_tenant_access_token(
            self._app_id,
            self._app_secret,
            cache_key=f"hr-org:{self._app_id}",
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        token = await self._token()
        client = await self._get_client()
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = await client.request(
                    method,
                    path,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json; charset=utf-8",
                    },
                    params=params,
                    json=json,
                )
                if response.status_code >= 500:
                    raise RuntimeError(f"飞书接口 {path} 返回 HTTP {response.status_code}")
                payload = response.json()
                code = payload.get("code")
                if code not in (0, None):
                    raise RuntimeError(f"飞书接口 {path} 返回错误: code={code}, msg={payload.get('msg', '')}")
                return payload.get("data") or {}
            except (httpx.HTTPError, RuntimeError) as exc:
                last_error = exc
                if attempt >= _MAX_RETRIES - 1:
                    break
                await asyncio.sleep(_RETRY_BACKOFF_SECONDS[attempt])
        assert last_error is not None
        raise last_error

    async def _list_children(self, parent_id: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page_token = ""
        while True:
            params: dict[str, Any] = {
                "department_id_type": "open_department_id",
                "parent_department_id": parent_id,
                "fetch_child": "false",
                "page_size": _PAGE_SIZE,
            }
            if page_token:
                params["page_token"] = page_token
            data = await self._request("GET", "/contact/v3/departments", params=params)
            for item in data.get("items") or []:
                if isinstance(item, dict):
                    items.append(item)
            if not data.get("has_more"):
                break
            page_token = str(data.get("page_token") or "")
            if not page_token:
                break
        return items

    async def fetch_departments(self) -> list[dict[str, Any]]:
        """Return the company's 一级部门 + 二级部门 as flat contact rows."""
        level_one_raw = await self._list_children(self._root_department_id)
        departments: list[dict[str, Any]] = []
        level_one_ids: list[str] = []
        for raw in level_one_raw:
            dept_id = str(raw.get("open_department_id") or raw.get("department_id") or "").strip()
            if not dept_id or dept_id == self._root_department_id:
                continue
            level_one_ids.append(dept_id)
            departments.append(
                {
                    "department_id": dept_id,
                    "name": raw.get("name") or "",
                    "parent_department_id": self._root_department_id,
                    "order": int_value(raw.get("order")),
                }
            )

        for parent_id in level_one_ids:
            try:
                children = await self._list_children(parent_id)
            except RuntimeError as exc:
                if "40004" in str(exc):
                    logger.warning("部门 %s 超出应用可见范围，跳过其子部门", parent_id)
                    continue
                raise
            for raw in children:
                dept_id = str(raw.get("open_department_id") or raw.get("department_id") or "").strip()
                if not dept_id:
                    continue
                departments.append(
                    {
                        "department_id": dept_id,
                        "name": raw.get("name") or "",
                        "parent_department_id": parent_id,
                        "order": int_value(raw.get("order")),
                    }
                )
        return departments

    async def fetch_departments_detail(self, department_ids: list[str]) -> list[dict[str, Any]]:
        details: list[dict[str, Any]] = []
        for start in range(0, len(department_ids), _DETAIL_BATCH_SIZE):
            batch = department_ids[start : start + _DETAIL_BATCH_SIZE]
            data = await self._request(
                "POST",
                "/directory/v1/departments/mget",
                params={
                    "department_id_type": "open_department_id",
                    "employee_id_type": "open_id",
                },
                json={
                    "department_ids": batch,
                    "required_fields": list(REQUIRED_DETAIL_FIELDS),
                },
            )
            for item in data.get("departments") or []:
                if isinstance(item, dict):
                    details.append(item)
        return details


async def build_default_fetcher(session: AsyncSession) -> FeishuOrgDepartmentFetcher:
    app_id, app_secret = await load_hr_platform_credentials(session)
    scope = await load_org_scope(session)
    return FeishuOrgDepartmentFetcher(
        app_id=app_id,
        app_secret=app_secret,
        root_department_id=scope.department_id,
    )
