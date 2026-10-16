"""Feishu Bitable operations for product output sync."""

import logging
from datetime import UTC, date, datetime
from typing import Any

import httpx

from app.modules.production.product.feishu.client import get_production_tenant_token

logger = logging.getLogger(__name__)

BITABLE_BASE = "https://open.feishu.cn/open-apis/bitable/v1"


def _to_ms_timestamp(value: date | datetime | str | None) -> int | str:
    """Convert date/datetime to Feishu Bitable millisecond timestamp (UTC)."""
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return value  # type: ignore[return-value]
    if isinstance(value, (date, datetime)):
        if isinstance(value, date) and not isinstance(value, datetime):
            dt = datetime(value.year, value.month, value.day, tzinfo=UTC)
        else:
            dt = value if value.tzinfo else value.replace(tzinfo=UTC)
        return int(dt.timestamp() * 1000)
    return value


def _extract_text(raw_value: Any) -> str:
    """Extract text from Feishu Bitable field value."""
    if raw_value is None:
        return ""
    if isinstance(raw_value, str):
        return raw_value
    if isinstance(raw_value, list):
        return "".join(item.get("text", "") for item in raw_value if isinstance(item, dict))
    return str(raw_value)


def _extract_number(raw_value: Any) -> float:
    """Extract number from Feishu Bitable field value."""
    if raw_value is None:
        return 0.0
    if isinstance(raw_value, (int, float)):
        return float(raw_value)
    if isinstance(raw_value, str):
        try:
            return float(raw_value)
        except ValueError:
            return 0.0
    return 0.0


def _extract_date(raw_value: Any) -> str:
    """Extract date string from Feishu Bitable field value."""
    if raw_value is None:
        return ""
    if isinstance(raw_value, int):
        try:
            dt = datetime.fromtimestamp(raw_value / 1000, tz=UTC)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, OSError):
            return ""
    if isinstance(raw_value, str):
        return raw_value
    return str(raw_value)


class ProductBitableClient:
    """Product output specific Bitable client."""

    def __init__(self, app_token: str, table_id: str) -> None:
        self.app_token = app_token
        self.table_id = table_id

    def _path(self, suffix: str = "") -> str:
        base = f"{BITABLE_BASE}/apps/{self.app_token}/tables/{self.table_id}"
        return f"{base}{suffix}"

    async def _token(self) -> str:
        return await get_production_tenant_token()

    async def create_record(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Create a single record."""
        token = await self._token()
        async with httpx.AsyncClient(timeout=15) as http:
            resp = await http.post(
                self._path("/records"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json={"fields": fields},
            )
            data: dict[str, Any] = resp.json()
            if data.get("code") != 0:
                logger.error("Bitable create_record failed: %s", data.get("msg"))
                return {}
            return data.get("data", {}).get("record", {})  # type: ignore[no-any-return]

    async def update_record(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        """Update a single record."""
        token = await self._token()
        async with httpx.AsyncClient(timeout=15) as http:
            resp = await http.put(
                self._path(f"/records/{record_id}"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json={"fields": fields},
            )
            data: dict[str, Any] = resp.json()
            if data.get("code") != 0:
                logger.error("Bitable update_record failed: %s", data.get("msg"))
                return {}
            return data.get("data", {}).get("record", {})  # type: ignore[no-any-return]

    async def delete_record(self, record_id: str) -> None:
        """Delete a single record."""
        token = await self._token()
        async with httpx.AsyncClient(timeout=15) as http:
            resp = await http.delete(
                self._path(f"/records/{record_id}"),
                headers={"Authorization": f"Bearer {token}"},
            )
            data: dict[str, Any] = resp.json()
            if data.get("code") != 0:
                logger.error("Bitable delete_record failed: %s", data.get("msg"))

    async def search_records(
        self,
        *,
        filter_str: str | None = None,
        page_size: int = 500,
    ) -> list[dict[str, Any]]:
        """Search records with optional filter."""
        token = await self._token()
        payload: dict[str, Any] = {"page_size": page_size}
        if filter_str:
            payload["filter"] = filter_str
        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.post(
                self._path("/records/search"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json=payload,
            )
            data: dict[str, Any] = resp.json()
            if data.get("code") != 0:
                logger.error("Bitable search_records failed: %s", data.get("msg"))
                return []
            return data.get("data", {}).get("items", [])  # type: ignore[no-any-return]

    async def list_records(self, page_size: int = 500) -> list[dict[str, Any]]:
        """List all records with pagination."""
        all_records: list[dict[str, Any]] = []
        page_token: str | None = None
        token = await self._token()
        while True:
            payload: dict[str, Any] = {"page_size": page_size}
            if page_token:
                payload["page_token"] = page_token
            async with httpx.AsyncClient(timeout=30) as http:
                resp = await http.get(
                    self._path("/records"),
                    headers={"Authorization": f"Bearer {token}"},
                    params=payload,
                )
                data: dict[str, Any] = resp.json()
                if data.get("code") != 0:
                    logger.error("Bitable list_records failed: %s", data.get("msg"))
                    break
            items = data.get("data", {}).get("items", [])
            all_records.extend(items)
            page_token = data.get("data", {}).get("page_token")
            has_more = data.get("data", {}).get("has_more", False)
            if not has_more or not page_token:
                break
        return all_records
