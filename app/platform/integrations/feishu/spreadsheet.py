"""Feishu Spreadsheet (电子表格) read operations."""

from __future__ import annotations

import logging
from typing import Any

from app.platform.integrations.feishu.client import FeishuClient

logger = logging.getLogger(__name__)


class SpreadsheetClient:
    """Read data from Feishu spreadsheets (电子表格)."""

    def __init__(self) -> None:
        self.client = FeishuClient()

    async def read_range(
        self,
        spreadsheet_token: str,
        range_address: str,
    ) -> list[list[Any]]:
        """Read cell values from a spreadsheet range.

        Args:
            spreadsheet_token: The spreadsheet token (from URL).
            range_address: Range in the form ``sheetId`` or ``sheetId!A1:Z100``.

        Returns:
            2-D list of cell values (rows x cols). Empty cells are ``""``.
        """
        data = await self.client.request(
            "GET",
            f"/sheets/v2/spreadsheets/{spreadsheet_token}/values/{range_address}",
            timeout=30.0,
        )
        value_range = data.get("valueRange", {})
        return value_range.get("values", [])

    async def read_sheet(
        self,
        spreadsheet_token: str,
        sheet_id: str,
    ) -> list[list[Any]]:
        """Read all data from a sheet (auto-detect range)."""
        return await self.read_range(spreadsheet_token, sheet_id)

    async def get_sheet_meta(
        self,
        spreadsheet_token: str,
    ) -> list[dict[str, Any]]:
        """Get metadata for all sheets in a spreadsheet."""
        data = await self.client.request(
            "GET",
            f"/sheets/v3/spreadsheets/{spreadsheet_token}/sheets/query",
            timeout=15.0,
        )
        return data.get("sheets", [])
