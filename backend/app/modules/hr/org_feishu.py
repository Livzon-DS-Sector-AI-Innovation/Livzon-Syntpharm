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

from app.core.secrets import decrypt_secret
from app.modules.hr.feishu_values import int_value
from app.modules.hr.org_domain import OrgScope
from app.modules.hr.org_settings import load_org_scopes
from app.platform.integrations.feishu.utils import OPEN_API_BASE_URL, get_tenant_access_token

logger = logging.getLogger(__name__)

APP_ID_SETTING = "FEISHU__PLATFORM__APP_ID"
APP_SECRET_SETTING = "FEISHU__PLATFORM__APP_SECRET"

_PAGE_SIZE = 50
_DETAIL_BATCH_SIZE = 50
_MAX_RETRIES = 3
_RETRY_BACKOFF_SECONDS = (1, 2, 4)
_FETCH_CONCURRENCY = 8
_MAX_DEPARTMENT_DEPTH = 20

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
    """Resolve the 主 Bot credentials from HR system settings only; fail when unset."""
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
            raise RuntimeError("HR 组织同步：飞书 App Secret 解密失败，请在系统设置中重新保存") from None

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
        roots: list[OrgScope],
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        self._roots = list(roots)
        self._client = client or httpx.AsyncClient(
            base_url=OPEN_API_BASE_URL,
            timeout=httpx.Timeout(20.0, connect=5.0),
        )

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=OPEN_API_BASE_URL,
                timeout=httpx.Timeout(20.0, connect=5.0),
            )
        return self._client

    async def _token(self, *, force_refresh: bool = False) -> str:
        return await get_tenant_access_token(
            self._app_id,
            self._app_secret,
            cache_key=f"hr-org:{self._app_id}",
            force_refresh=force_refresh,
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
        token_refreshed = False
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
                if response.status_code == 429:
                    raise RuntimeError(f"飞书接口 {path} 触发限流 (HTTP 429)")
                payload = response.json()
                code = payload.get("code")
                if code == 99991663 and not token_refreshed:
                    token_refreshed = True
                    token = await self._token(force_refresh=True)
                    continue
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

    async def _list_children_many(self, parent_ids: list[str]) -> list[list[dict[str, Any]] | RuntimeError]:
        """Fetch children for a frontier with bounded concurrency.

        40004 (department outside the app's visibility) is returned as an error
        value so the caller can skip that branch; other failures propagate.
        """
        semaphore = asyncio.Semaphore(_FETCH_CONCURRENCY)

        async def fetch_one(parent_id: str) -> list[dict[str, Any]] | RuntimeError:
            async with semaphore:
                try:
                    return await self._list_children(parent_id)
                except RuntimeError as exc:
                    if "40004" in str(exc):
                        return exc
                    raise

        return await asyncio.gather(*(fetch_one(parent_id) for parent_id in parent_ids))

    async def fetch_departments(self) -> list[dict[str, Any]]:
        """Walk every configured root breadth-first until no children remain.

        Each returned row is flat (``parent_department_id`` + ``level``); the
        mirror derives depth from this value. Branches the bot cannot see
        (40004) are skipped; a 40004 on a configured root fails the sync because
        the configured scope itself is invisible.
        """
        departments: list[dict[str, Any]] = []
        seen: set[str] = set()

        for root in self._roots:
            root_id = root.department_id
            if not root_id or root_id in seen:
                continue
            seen.add(root_id)
            departments.append(
                {
                    "department_id": root_id,
                    "name": root.department_name,
                    "parent_department_id": None,
                    "level": 0,
                    "order": 0,
                }
            )

            frontier: list[tuple[str, int]] = [(root_id, 0)]
            while frontier:
                active: list[tuple[str, int]] = []
                for parent_id, depth in frontier:
                    if depth >= _MAX_DEPARTMENT_DEPTH:
                        logger.warning(
                            "部门层级超过上限，跳过其子部门",
                            extra={
                                "biz_module": "hr",
                                "department_id": parent_id,
                                "max_depth": _MAX_DEPARTMENT_DEPTH,
                            },
                        )
                        continue
                    active.append((parent_id, depth))
                if not active:
                    break
                results = await self._list_children_many([parent_id for parent_id, _ in active])
                next_frontier: list[tuple[str, int]] = []
                for (parent_id, depth), children in zip(active, results):
                    if isinstance(children, RuntimeError):
                        if depth == 0:
                            raise RuntimeError(
                                f"HR 组织同步：根部门 {parent_id} 不在飞书应用可见范围内（40004）"
                            ) from children
                        logger.warning(
                            "部门 %s 超出应用可见范围，跳过其子部门",
                            parent_id,
                            extra={
                                "biz_module": "hr",
                                "department_id": parent_id,
                                "skip_reason": "40004",
                            },
                        )
                        continue
                    for raw in children:
                        dept_id = str(raw.get("open_department_id") or raw.get("department_id") or "").strip()
                        if not dept_id or dept_id in seen:
                            continue
                        seen.add(dept_id)
                        departments.append(
                            {
                                "department_id": dept_id,
                                "name": raw.get("name") or "",
                                "parent_department_id": parent_id,
                                "level": depth + 1,
                                "order": int_value(raw.get("order")),
                            }
                        )
                        next_frontier.append((dept_id, depth + 1))
                frontier = next_frontier
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
    scopes = await load_org_scopes(session)
    return FeishuOrgDepartmentFetcher(
        app_id=app_id,
        app_secret=app_secret,
        roots=list(scopes.roots),
    )
