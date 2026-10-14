"""Feishu contact: departments, users with Redis caching."""

import json
import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.redis import cache_get, cache_set

logger = logging.getLogger(__name__)

settings = get_settings()


async def _get_feishu_client() -> Any:
    import lark_oapi as lark

    return (
        lark.Client.builder()
        .app_id(settings.feishu.platform.app_id)
        .app_secret(settings.feishu.platform.app_secret)
        .domain(lark.FEISHU_DOMAIN)
        .app_type(lark.AppType.SELF)
        .build()
    )


async def _get_tenant_token(client) -> Any:  # type: ignore[no-untyped-def]
    import json as _json

    from lark_oapi.api.auth.v3 import (
        InternalTenantAccessTokenRequest,
        InternalTenantAccessTokenRequestBody,
    )

    req = (
        InternalTenantAccessTokenRequest.builder()
        .request_body(
            InternalTenantAccessTokenRequestBody.builder()
            .app_id(settings.feishu.platform.app_id)
            .app_secret(settings.feishu.platform.app_secret)
            .build()
        )
        .build()
    )
    resp = await client.auth.v3.tenant_access_token.ainternal(req)
    if not resp.success():
        raise RuntimeError(
            f"Failed to get tenant token: code={resp.code}, msg={resp.msg}",
        )
    if resp.raw and resp.raw.content:
        data = _json.loads(resp.raw.content.decode("utf-8"))
        return data.get("tenant_access_token", "")
    raise RuntimeError("Empty tenant token response")


def _raise_on_feishu_error(payload: dict[str, Any], api_name: str) -> None:
    """校验飞书原始响应的业务错误码，非 0 直接抛错。

    不校验的后果：权限未生效 / 可见范围为空时飞书返回 `code=40004`，
    而直接取 `data.items` 会表现为「静默返回 0 条」，排查时完全看不出原因
    （曾误判为「租户没有数据」）。
    """
    code = payload.get("code")
    if code is not None and code != 0:
        msg = payload.get("msg", "")
        raise RuntimeError(f"飞书接口 {api_name} 返回错误: code={code}, msg={msg}")


async def get_contact_scope(
    *,
    app_id: str | None = None,
    app_secret: str | None = None,
    tenant_access_token: str | None = None,
) -> dict[str, list[str]]:
    """获取应用「通讯录授权范围」，对应接口 `GET /contact/v3/scopes`。

    返回 `{"department_ids": [...], "user_ids": [...], "group_ids": [...]}`；
    三个列表都为空表示授权范围是「全部成员」（不受限）。

    凭证优先级：显式 `tenant_access_token` > 显式 `app_id`/`app_secret` > 模块默认凭证。
    权限诊断要检查的是「Livzon 助手」这个应用自己的授权范围，
    所以必须支持传入该应用的凭证，不能只依赖模块默认凭证。
    """
    if tenant_access_token:
        token = tenant_access_token
    elif app_id and app_secret:
        from app.platform.integrations.feishu.utils import get_tenant_access_token

        token = await get_tenant_access_token(
            app_id,
            app_secret,
            cache_key=f"livzon-assistant:{app_id}",
        )
    else:
        client = await _get_feishu_client()
        token = await _get_tenant_token(client)

    url = "https://open.feishu.cn/open-apis/contact/v3/scopes"
    params: dict[str, Any] = {
        "user_id_type": "open_id",
        "department_id_type": "open_department_id",
        "page_size": 100,
    }
    headers = {"Authorization": f"Bearer {token}"}

    department_ids: list[str] = []
    user_ids: list[str] = []
    group_ids: list[str] = []
    async with httpx.AsyncClient(timeout=15.0) as http:
        while True:
            resp = await http.get(url, params=params, headers=headers)
            payload = resp.json()
            _raise_on_feishu_error(payload, "contact/v3/scopes")
            data = payload.get("data") or {}
            department_ids.extend(data.get("department_ids") or [])
            user_ids.extend(data.get("user_ids") or [])
            group_ids.extend(data.get("group_ids") or [])
            if not data.get("has_more"):
                break
            page_token = data.get("page_token") or ""
            if not page_token:
                break
            params["page_token"] = page_token

    logger.info(
        "应用通讯录授权范围: 部门 %d 个，用户 %d 名，用户组 %d 个（全为 0 表示范围为全部成员）",
        len(department_ids),
        len(user_ids),
        len(group_ids),
    )
    return {
        "department_ids": department_ids,
        "user_ids": user_ids,
        "group_ids": group_ids,
    }


async def get_scope_department_ids() -> list[str]:
    """获取应用「可见范围内的部门」open_department_id 列表。

    返回空列表表示可见范围是「全部成员」（不受限）。

    用途：应用的通讯录可见范围通常**不包含根部门 "0"**，
    所以不能硬编码从 "0" 开始 BFS（会报 `40004 no dept authority error`），
    而应从可见范围内的部门出发。
    """
    scope = await get_contact_scope()
    return scope["department_ids"]


# ── Department helpers ──────────────────────────────────────────────


async def get_all_departments(root_department_id: str | None = None) -> list[dict[str, Any]]:
    """BFS 递归获取部门（含名称），返回扁平列表。

    起点选择：
    - 显式传入 `root_department_id` → 从它开始；
    - 否则先查应用**可见范围内的部门**并从它们开始（可见范围通常不含根部门 "0"，
      硬编码从 "0" 会报 `40004 no dept authority error`）；
    - 可见范围为「全部成员」时飞书返回空列表，此时退回从根 "0" 开始。
    """
    client = await _get_feishu_client()
    token = await _get_tenant_token(client)

    from lark_oapi.api.contact.v3 import ListDepartmentRequest

    all_depts: list[dict[str, Any]] = []
    # BFS 起点
    if root_department_id and root_department_id != "0":
        queue: list[tuple[str, str]] = [(root_department_id, "")]
    else:
        scope_dept_ids = await get_scope_department_ids()
        queue = [(oid, "") for oid in scope_dept_ids] if scope_dept_ids else [("0", "")]
    visited: set[str] = {oid for oid, _ in queue}

    while queue:
        parent_id, parent_oid = queue.pop(0)

        page_token = ""
        while True:
            req = (
                ListDepartmentRequest.builder()
                .department_id_type("open_department_id")
                .parent_department_id(parent_id)
                .fetch_child(False)
                .page_size(50)
                .page_token(page_token)
                .build()
            )
            req.headers["Authorization"] = f"Bearer {token}"
            resp = await client.contact.v3.department.alist(req)
            raw = resp.raw.content if resp.raw else None
            if not raw:
                break
            payload = json.loads(raw.decode("utf-8"))
            try:
                _raise_on_feishu_error(payload, "contact/v3/departments")
            except RuntimeError as exc:
                if "40004" in str(exc):
                    # 该部门超出应用可见范围：跳过它的子部门，继续其他分支
                    logger.warning("部门 %s 超出应用可见范围，跳过其子部门", parent_id)
                    break
                raise
            data = payload.get("data", {})
            for it in data.get("items", []):
                oid = it.get("open_department_id", "")
                if not oid or oid in visited:
                    continue
                visited.add(oid)
                name = it.get("name", "") or oid
                order_str = it.get("order", "0") or "0"
                try:
                    order_val = int(order_str)
                except (ValueError, TypeError):
                    order_val = 0
                all_depts.append(
                    {
                        "department_id": oid,
                        "name": name,
                        "parent_department_id": parent_oid if parent_id != "0" else "",
                        "leader_user_id": it.get("leader_user_id", "") or "",
                        "member_count": it.get("member_count", 0) or 0,
                        "status_is_deleted": False,
                        "order": order_val,
                    }
                )
                # 继续递归子部门
                queue.append((oid, oid))
            if not data.get("has_more"):
                break
            page_token = data.get("page_token", "")

    logger.info("Fetched %d departments from Feishu (BFS)", len(all_depts))
    return all_depts


async def get_department_members(dept_id: str) -> list[dict[str, Any]]:
    """获取部门成员列表，优先读 Redis"""
    cache_key = f"feishu:dept:{dept_id}:members"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)  # type: ignore[no-any-return]

    client = await _get_feishu_client()
    token = await _get_tenant_token(client)

    from lark_oapi.api.contact.v3 import ListUserRequest

    all_members = []
    page_token = ""
    while True:
        req = (
            ListUserRequest.builder()
            .department_id(dept_id)
            # page_size 上限 50：传 100 会报 99992402 field validation failed
            .page_size(50)
            .page_token(page_token)
            # user_id_type="open_id"：无需 contact:user.employee_id:readonly（该权限需集团审核）
            .user_id_type("open_id")
            .build()
        )
        req.headers["Authorization"] = f"Bearer {token}"
        resp = await client.contact.v3.user.alist(req)
        if not resp.success():
            logger.error("Failed to list users for dept %s: %s", dept_id, resp.msg)
            break

        raw = resp.raw.content if resp.raw else None
        if raw:
            data = json.loads(raw.decode("utf-8")).get("data", {})
            items = data.get("items", [])
            for item in items:
                all_members.append({**_parse_feishu_user(item), "department_id": dept_id})
            if not data.get("has_more"):
                break
            page_token = data.get("page_token", "")
        else:
            break

    await cache_set(cache_key, json.dumps(all_members, ensure_ascii=False), ex=86400)
    return all_members


async def get_department_leader(dept_id: str) -> dict[str, Any] | None:
    """获取部门主管"""
    cache_key = f"feishu:dept:{dept_id}:leader"
    cached = await cache_get(cache_key)
    if cached:
        return json.loads(cached)  # type: ignore[no-any-return]

    client = await _get_feishu_client()
    token = await _get_tenant_token(client)

    from lark_oapi.api.contact.v3 import GetDepartmentRequest

    req = GetDepartmentRequest.builder().department_id(dept_id).user_id_type("open_id").build()
    req.headers["Authorization"] = f"Bearer {token}"
    resp = await client.contact.v3.department.aget(req)
    if not resp.success():
        logger.error("Failed to get department %s: %s", dept_id, resp.msg)
        return None

    raw = resp.raw.content if resp.raw else None
    if raw:
        dept = json.loads(raw.decode("utf-8")).get("data", {}).get("department", {})
        leader_id = dept.get("leader_user_id")
        if leader_id:
            result = {"user_id": leader_id}
            await cache_set(cache_key, json.dumps(result, ensure_ascii=False), ex=86400)
            return result

    return None


async def is_department_member(user_id: str, dept_id: str) -> bool:
    """检查用户是否为部门成员"""
    members = await get_department_members(dept_id)
    return any(m.get("user_id") == user_id for m in members)


# ── User helpers ────────────────────────────────────────────────────


def _parse_feishu_user(u: dict[str, Any]) -> dict[str, Any]:
    """统一解析飞书用户条目（`contact/v3/users` 与 `find_by_department` 结构一致）。

    权限分级（重要，2026-10 实测）：
    - **无需额外权限**：`open_id` / `union_id` / `name` / `en_name` / `avatar`(72/240/640)；
    - **需额外权限**：`user_id`（`contact:user.employee_id:readonly`，需集团审核）、
      `employee_no` / `job_title` / `enterprise_email`（`contact:user.employee:readonly`）、
      `email`、`mobile`、`department_ids`。
      未开通时这些字段为空，调用方需容忍缺字段。
    """
    avatar = u.get("avatar") or {}
    return {
        "user_id": u.get("user_id") or "",
        "open_id": u.get("open_id") or "",
        "union_id": u.get("union_id") or "",
        "name": (u.get("name") or "").strip(),
        "en_name": (u.get("en_name") or "").strip(),
        "employee_no": u.get("employee_no") or "",
        "email": u.get("email") or "",
        "enterprise_email": u.get("enterprise_email") or "",
        "mobile": u.get("mobile") or "",
        "job_title": u.get("job_title") or "",
        "department_ids": u.get("department_ids") or [],
        "avatar_url": avatar.get("avatar_640") or avatar.get("avatar_240") or "",
        "avatar_thumb": avatar.get("avatar_72") or "",
        "avatar_middle": avatar.get("avatar_240") or "",
        "avatar_big": avatar.get("avatar_640") or "",
    }


async def get_all_users() -> list[dict[str, Any]]:
    """获取所有可见用户（全公司范围，分页）。

    每个元素包含 user_id, open_id, name, employee_no, email, mobile,
    department_ids, job_title, positions, department_path 等。
    """
    client = await _get_feishu_client()
    token = await _get_tenant_token(client)

    from lark_oapi.api.contact.v3 import ListUserRequest

    all_users: list[dict[str, Any]] = []
    page_token = ""
    while True:
        # user_id_type="open_id"：无需 contact:user.employee_id:readonly（该权限需集团审核）
        # page_size 上限 50：传 100 会报 99992402 field validation failed
        req = ListUserRequest.builder().user_id_type("open_id").page_size(50).page_token(page_token).build()
        req.headers["Authorization"] = f"Bearer {token}"
        resp = await client.contact.v3.user.alist(req)
        raw = resp.raw.content if resp.raw else None
        if raw:
            payload = json.loads(raw.decode("utf-8"))
            _raise_on_feishu_error(payload, "contact/v3/users")
            data = payload.get("data", {})
            for u in data.get("items", []):
                all_users.append(_parse_feishu_user(u))
            if not data.get("has_more"):
                break
            page_token = data.get("page_token", "")
        else:
            break

    logger.info("Fetched %d users from Feishu", len(all_users))
    return all_users


async def find_users_by_department(department_id: str) -> list[dict[str, Any]]:
    """按部门获取所有用户详情（含 department_ids、position、job_title 等）。

    每个元素包含：
    - user_id, open_id, name, employee_no, email, mobile,
    - department_ids (list[str]), job_title, positions, department_path
    """
    client = await _get_feishu_client()
    token = await _get_tenant_token(client)

    from lark_oapi.api.contact.v3 import FindByDepartmentUserRequest

    all_users: list[dict[str, Any]] = []
    page_token = ""
    while True:
        req = (
            FindByDepartmentUserRequest.builder()
            # user_id_type="open_id"：无需 contact:user.employee_id:readonly（该权限需集团审核）
            .user_id_type("open_id")
            .department_id_type("open_department_id")
            .department_id(department_id)
            # page_size 上限 50：传 100 会报 99992402 field validation failed
            .page_size(50)
            .page_token(page_token)
            .build()
        )
        req.headers["Authorization"] = f"Bearer {token}"
        resp = await client.contact.v3.user.afind_by_department(req)
        if not resp.success():
            logger.error(
                "Failed to find users by department %s: code=%s, msg=%s",
                department_id,
                resp.code,
                resp.msg,
            )
            break

        if resp.data and resp.data.items:
            for u in resp.data.items:
                positions: list[dict[str, Any]] = []
                if u.positions:
                    for p in u.positions:
                        positions.append(
                            {
                                "position_code": p.position_code,
                                "position_name": p.position_name,
                                "department_id": p.department_id,
                                "is_major": p.is_major,
                            }
                        )

                department_path: list[dict[str, Any]] = []
                if u.department_path:
                    for dp in u.department_path:
                        dept_name = ""
                        if dp.department_name:
                            dept_name = dp.department_name.name or ""
                        dept_id_val = str(dp.department_id) if dp.department_id else ""
                        department_path.append(
                            {
                                "department_id": dept_id_val,
                                "department_name": dept_name,
                            }
                        )

                all_users.append(
                    {
                        "user_id": u.user_id or "",
                        "open_id": u.open_id or "",
                        "union_id": u.union_id or "",
                        "name": u.name or "",
                        "en_name": u.en_name or "",
                        "email": u.email or "",
                        "mobile": u.mobile or "",
                        "employee_no": u.employee_no or "",
                        "job_title": u.job_title or "",
                        "department_ids": u.department_ids or [],
                        "positions": positions,
                        "department_path": department_path,
                        "avatar_key": u.avatar_key or "",
                        "avatar_url": (u.avatar.avatar_640 or u.avatar.avatar_240) if u.avatar else "",
                        "avatar_thumb": (u.avatar.avatar_72 or "") if u.avatar else "",
                        "avatar_middle": (u.avatar.avatar_240 or "") if u.avatar else "",
                        "avatar_big": (u.avatar.avatar_640 or "") if u.avatar else "",
                        "join_time": u.join_time or 0,
                        "is_frozen": u.is_frozen if u.is_frozen is not None else False,
                    }
                )

            if not resp.data.has_more:
                break
            page_token = resp.data.page_token or ""
        else:
            break

    logger.info(
        "Fetched %d users from department %s",
        len(all_users),
        department_id,
    )
    return all_users


async def get_user_detail(user_id: str, user_id_type: str = "user_id") -> dict[str, Any] | None:
    """获取单个用户详细信息。

    返回包含 department_ids, positions, department_path 等完整字段。
    """
    client = await _get_feishu_client()
    token = await _get_tenant_token(client)

    from lark_oapi.api.contact.v3 import GetUserRequest

    req = GetUserRequest.builder().user_id_type(user_id_type).user_id(user_id).build()
    req.headers["Authorization"] = f"Bearer {token}"
    resp = await client.contact.v3.user.aget(req)
    if not resp.success():
        logger.error(
            "Failed to get user %s: code=%s, msg=%s",
            user_id,
            resp.code,
            resp.msg,
        )
        return None

    if resp.data and resp.data.user:
        u = resp.data.user
        positions: list[dict[str, Any]] = []
        if u.positions:
            for p in u.positions:
                positions.append(
                    {
                        "position_code": p.position_code,
                        "position_name": p.position_name,
                        "department_id": p.department_id,
                        "is_major": p.is_major,
                    }
                )

        department_path: list[dict[str, Any]] = []
        if u.department_path:
            for dp in u.department_path:
                dept_name = ""
                if dp.department_name:
                    dept_name = dp.department_name.name or ""
                department_path.append(
                    {
                        "department_id": str(dp.department_id) if dp.department_id else "",
                        "department_name": dept_name,
                    }
                )

        return {
            "user_id": u.user_id or "",
            "open_id": u.open_id or "",
            "union_id": u.union_id or "",
            "name": u.name or "",
            "en_name": u.en_name or "",
            "email": u.email or "",
            "enterprise_email": getattr(u, "enterprise_email", "") or "",
            "mobile": u.mobile or "",
            "employee_no": u.employee_no or "",
            "job_title": u.job_title or "",
            "department_ids": u.department_ids or [],
            "positions": positions,
            "department_path": department_path,
            "avatar_key": u.avatar_key or "",
            "avatar_url": (u.avatar.avatar_640 or u.avatar.avatar_240) if u.avatar else "",
            "avatar_thumb": (u.avatar.avatar_72 or "") if u.avatar else "",
            "avatar_middle": (u.avatar.avatar_240 or "") if u.avatar else "",
            "avatar_big": (u.avatar.avatar_640 or "") if u.avatar else "",
            "join_time": u.join_time or 0,
            "is_frozen": u.is_frozen if u.is_frozen is not None else False,
        }

    return None
