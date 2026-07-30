"""Feishu HTTP client with auth and retry."""

import logging
from typing import Any
from uuid import uuid4

import httpx

from app.platform.integrations.base import IntegrationClient
from app.platform.integrations.feishu.auth import FeishuAuth

logger = logging.getLogger(__name__)


class FeishuClient(IntegrationClient):
    system_name = "feishu"
    base_url = "https://open.feishu.cn/open-apis"

    def __init__(self, auth: FeishuAuth | None = None) -> None:
        self._client: httpx.AsyncClient | None = None
        self._auth = auth or FeishuAuth.default()

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
                timeout=httpx.Timeout(120.0, connect=30.0),
            )
        return self._client

    async def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        *,
        parent_type: str = "bitable_file",
        parent_node: str | None = None,
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        """Upload a file to Feishu Drive and return file metadata.

        Args:
            file_bytes: Raw file bytes.
            filename: Original file name.
            parent_type: Feishu parent type, e.g. "bitable_file".
            parent_node: Parent node ID, e.g. Bitable app_token.
            timeout: Upload timeout in seconds.

        Returns:
            Dict with keys like file_token, name, size, type.
        """
        import io

        token = await self._auth.get_token()
        headers = {"Authorization": f"Bearer {token}"}

        files = {"file": (filename, io.BytesIO(file_bytes))}
        data: dict[str, str] = {
            "file_name": filename,
            "size": str(len(file_bytes)),
        }
        if parent_type:
            data["parent_type"] = parent_type
        if parent_node:
            data["parent_node"] = parent_node

        client = await self._get_client()
        resp = await client.post(
            "/drive/v1/medias/upload_all",
            headers=headers,
            files=files,
            data=data,
            timeout=timeout,
        )
        try:
            resp.raise_for_status()
        except Exception:
            error_body = ""
            try:
                error_body = resp.text
            except Exception:
                pass
            logger.error(
                "Feishu upload_file failed: status=%s, body=%s, parent_type=%s, parent_node=%s",
                resp.status_code,
                error_body,
                parent_type,
                parent_node,
            )
            raise
        result = resp.json()
        if result.get("code") != 0:
            raise RuntimeError(f"Feishu upload error: code={result.get('code')}, msg={result.get('msg')}")
        return result.get("data", {})  # type: ignore[no-any-return]

    async def health_check(self) -> dict[str, Any]:
        try:
            token = await self._auth.get_token()
            return {"status": "ok", "token_prefix": token[:10] + "..."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _e2e_response(self, method: str, path: str) -> dict[str, Any]:
        """Return fake Feishu API response when running in e2e mode."""
        if path.startswith("/auth/v3/tenant_access_token/internal"):
            return {"code": 0, "msg": "ok", "tenant_access_token": "e2e-fake-token", "expire": 9999999999}
        if path.startswith("/auth/v3/app_access_token/internal"):
            return {"code": 0, "msg": "ok", "app_access_token": "e2e-fake-app-token", "expire": 9999999999}
        if "/bitable/" in path:
            return {"code": 0, "msg": "ok", "data": {"items": [], "total": 0, "has_more": False}}
        if "contact" in path:
            return {"code": 0, "msg": "ok", "data": {}}
        if "im/v1/messages" in path:
            return {"code": 0, "msg": "ok", "data": {"message_id": f"e2e-msg-{uuid4().hex[:12]}"}}
        if "drive/v1/medias" in path:
            return {"code": 0, "msg": "ok", "data": {"file_token": "e2e-file-token", "tmp_download_url": ""}}
        if "sheets/v2/spreadsheets" in path:
            return {"code": 0, "msg": "ok", "data": {}}
        if "authen/v1" in path:
            return {"code": 0, "msg": "ok", "data": {"access_token": "e2e-oauth-token"}}
        if "websocket" in path or "event/v1" in path:
            return {"code": 0, "msg": "ok", "data": {}}
        return {"code": 0, "msg": "ok", "data": {}}

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        from app.core.config import get_settings

        if get_settings().APP_ENV == "e2e":
            return self._e2e_response(method, path)
        token = await self._auth.get_token()
        default_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        if headers:
            default_headers.update(headers)

        client = await self._get_client()
        resp = await client.request(
            method,
            path,
            headers=default_headers,
            json=json,
            params=params,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Feishu API error: code={data.get('code')}, msg={data.get('msg')}, path={path}")
        return data.get("data", {})  # type: ignore[no-any-return]
