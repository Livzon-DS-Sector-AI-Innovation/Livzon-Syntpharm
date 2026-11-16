"""Feishu Bitable (多维表格) CRUD operations."""

import logging
from datetime import UTC, date, datetime
from typing import Any

from app.platform.integrations.feishu.auth import FeishuAuth
from app.platform.integrations.feishu.client import FeishuClient

logger = logging.getLogger(__name__)


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


class BitableClient:
    def __init__(
        self,
        *,
        auth: FeishuAuth | None = None,
        app_token: str,
    ) -> None:
        # 平台层不持有任何模块的默认 app_token：调用方必须显式传入，
        # 否则「没传参」会被静默解释成 HR 表格（audit #7/#13）。
        if not app_token:
            raise ValueError("BitableClient requires an explicit app_token")
        self.client = FeishuClient(auth=auth)
        self.app_token = app_token

    def _path(self, table_id: str, suffix: str = "") -> str:
        base = f"/bitable/v1/apps/{self.app_token}/tables/{table_id}"
        return f"{base}{suffix}"

    async def create_record(self, table_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        """Create a single record."""
        if not self.app_token or not table_id:
            raise RuntimeError("Bitable app_token or table_id not configured")
        data = await self.client.request(
            "POST",
            self._path(table_id, "/records"),
            json={"fields": fields},
        )
        return data.get("record", {})  # type: ignore[no-any-return]

    async def update_record(self, table_id: str, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        """Update a single record."""
        if not self.app_token or not table_id:
            raise RuntimeError("Bitable app_token or table_id not configured")
        data = await self.client.request(
            "PUT",
            self._path(table_id, f"/records/{record_id}"),
            json={"fields": fields},
        )
        return data.get("record", {})  # type: ignore[no-any-return]

    async def delete_record(self, table_id: str, record_id: str) -> None:
        """Delete a single record."""
        if not self.app_token or not table_id:
            raise RuntimeError("Bitable app_token or table_id not configured")
        await self.client.request(
            "DELETE",
            self._path(table_id, f"/records/{record_id}"),
        )

    async def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        **kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """Upload a file to Feishu Drive via the underlying client."""
        return await self.client.upload_file(file_bytes, filename, **kwargs)  # type: ignore[arg-type]

    async def search_records(
        self,
        table_id: str,
        *,
        filter_str: str | None = None,
        page_size: int = 500,
    ) -> list[dict[str, Any]]:
        """Search records with optional filter."""
        if not self.app_token or not table_id:
            raise RuntimeError("Bitable app_token or table_id not configured")
        payload: dict[str, Any] = {"page_size": page_size}
        if filter_str:
            payload["filter"] = filter_str
        data = await self.client.request(
            "POST",
            self._path(table_id, "/records/search"),
            json=payload,
        )
        return data.get("items", [])  # type: ignore[no-any-return]

    async def get_tables(self) -> list[dict[str, Any]]:
        """Get all tables in the bitable app."""
        if not self.app_token:
            raise RuntimeError("Bitable app_token not configured")
        data = await self.client.request(
            "GET",
            f"/bitable/v1/apps/{self.app_token}/tables",
        )
        return data.get("items", [])  # type: ignore[no-any-return]
