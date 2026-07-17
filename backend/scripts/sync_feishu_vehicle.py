# ruff: noqa
"""Sync Feishu Bitable vehicle request data to PostgreSQL.

Usage: cd to dazah-backend and run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/sync_feishu_vehicle.py
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import insert, select

from app.core.database import get_db
from app.modules.administration.models import VehicleRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.core.config import get_settings
from app.platform.integrations.feishu.auth import FeishuAuth

_settings = get_settings()
APP_TOKEN = _settings.FEISHU_BITABLE_VEHICLE_REQUEST_APP_TOKEN
TABLE_ID = _settings.FEISHU_BITABLE_VEHICLE_REQUEST_TABLE_ID
BASE_URL = "https://open.feishu.cn/open-apis"

# 同步最近 N 个月的数据
SYNC_MONTHS = 2


async def get_tenant_token(client: httpx.AsyncClient) -> str:
    return await FeishuAuth.vehicle().get_token()


def get_cutoff_timestamp() -> int:
    """Return the millisecond timestamp for N months ago."""
    now = datetime.now(UTC)
    month = now.month - SYNC_MONTHS
    year = now.year
    while month <= 0:
        month += 12
        year -= 1
    try:
        cutoff = datetime(year, month, now.day, tzinfo=UTC)
    except ValueError:
        import calendar

        last_day = calendar.monthrange(year, month)[1]
        cutoff = datetime(year, month, last_day, tzinfo=UTC)
    return int(cutoff.timestamp() * 1000)


def _extract_text(value) -> str:
    """Extract plain text from Feishu rich-text / person / simple fields."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        # Rich text: [{"text": "...", "type": "text"}]
        if len(value) > 0 and isinstance(value[0], dict) and "text" in value[0]:
            return "".join(item.get("text", "") for item in value if isinstance(item, dict))
        # Person array: [{"name": "...", ...}]
        if len(value) > 0 and isinstance(value[0], dict) and "name" in value[0]:
            names = [item.get("name", "") for item in value if isinstance(item, dict)]
            return ", ".join(n for n in names if n)
        # Simple string array
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        # Rich text object: {"type": 1, "value": [{"text": "..."}]}
        if "value" in value and isinstance(value["value"], list):
            return "".join(item.get("text", "") for item in value["value"] if isinstance(item, dict))
        return value.get("text", "")
    return str(value)


def _extract_person_name(value) -> str:
    """Extract person name from Feishu person field."""
    if value is None:
        return ""
    if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
        return value[0].get("name", "")
    return _extract_text(value)


def _parse_datetime(value) -> datetime | None:
    """Parse Feishu date value to naive datetime (matching DB schema)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # Feishu returns millisecond timestamp → naive local datetime
        return datetime.fromtimestamp(value / 1000)
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None


def parse_record(record: dict) -> dict | None:
    """Parse Feishu record fields to VehicleRequest kwargs."""
    fields = record.get("fields", {})
    if not fields:
        return None

    # 计划用车时间 is required in the model
    start_time = _parse_datetime(fields.get("计划用车时间"))
    if start_time is None:
        return None

    # Map fields based on actual Feishu schema
    applicant = _extract_person_name(fields.get("申请人"))
    if not applicant:
        # Fallback to 用车人 if 申请人 is empty
        applicant = _extract_person_name(fields.get("用车人"))

    purpose = _extract_text(fields.get("用车事由"))
    destination = _extract_text(fields.get("目的地"))
    phone = fields.get("用车人电话(座机)") or ""
    status = fields.get("审批结果") or "待审批"
    remarks = _extract_text(fields.get("备注(非重要人员)"))

    # end_time is required in model; default to start_time + 4 hours if missing
    end_time = _parse_datetime(fields.get("确认出车时间（司机填写）"))
    if end_time is None:
        end_time = start_time + timedelta(hours=4)

    return {
        "applicant_name": applicant,
        "applicant_department": "",  # Not present in current table schema
        "applicant_phone": str(phone),
        "purpose": purpose,
        "destination": destination,
        "start_time": start_time,
        "end_time": end_time,
        "passengers": 1,  # Not present in current table schema
        "status": status,
        "remarks": remarks,
    }


async def fetch_and_sync_recent(client: httpx.AsyncClient, token: str) -> dict:
    """Fetch records sorted by time (desc) and sync only recent ones to DB."""
    headers = {"Authorization": f"Bearer {token}"}
    cutoff_ms = get_cutoff_timestamp()
    cutoff_dt = datetime.fromtimestamp(cutoff_ms / 1000)
    logger.info("Cutoff date: %s", cutoff_dt.strftime("%Y-%m-%d"))

    page_token: str | None = None
    total_fetched = 0
    total_synced = 0
    total_skipped = 0
    total_failed = 0
    stop_fetching = False

    async for session in get_db():
        while not stop_fetching:
            payload: dict = {
                "page_size": 500,
                "sort": [{"field_name": "计划用车时间", "desc": True}],
            }
            if page_token:
                payload["page_token"] = page_token

            resp = await client.post(
                f"{BASE_URL}/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/search",
                headers=headers,
                json=payload,
            )
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"Feishu API error: {data}")

            items = data.get("data", {}).get("items", [])
            total_fetched += len(items)

            if not items:
                break

            # Check if the oldest record in this page is still within range
            # Since we sort desc, the last item has the smallest time
            last_item_time = None
            for rec in reversed(items):
                t = _parse_datetime(rec.get("fields", {}).get("计划用车时间"))
                if t:
                    last_item_time = t
                    break

            if last_item_time and last_item_time < cutoff_dt:
                # Some items on this page are too old; filter individually
                stop_fetching = True

            # Process records on this page
            for rec in items:
                parsed = parse_record(rec)
                if not parsed:
                    total_skipped += 1
                    continue

                # Time filter
                if parsed["start_time"] < cutoff_dt:
                    total_skipped += 1
                    continue

                try:
                    # Check duplicate by applicant_name + purpose + start_time
                    stmt = select(VehicleRequest).where(
                        VehicleRequest.applicant_name == parsed["applicant_name"],
                        VehicleRequest.purpose == parsed["purpose"],
                        VehicleRequest.start_time == parsed["start_time"],
                        VehicleRequest.is_deleted.is_(False),
                    )
                    result = await session.execute(stmt)
                    existing = result.scalar_one_or_none()
                    if existing:
                        total_skipped += 1
                        continue

                    # Use Core insert to bypass ORM foreign-key validation
                    await session.execute(insert(VehicleRequest).values(**parsed))
                    total_synced += 1
                except Exception as e:
                    logger.error("Sync failed for record %s: %s", rec.get("record_id"), e)
                    total_failed += 1
                    await session.rollback()

            # Commit every page to avoid huge transactions
            await session.commit()
            logger.info(
                "Page committed — fetched=%s synced=%s skipped=%s failed=%s",
                total_fetched,
                total_synced,
                total_skipped,
                total_failed,
            )

            if not data.get("data", {}).get("has_more"):
                break
            page_token = data.get("data", {}).get("page_token")

        break

    return {
        "fetched": total_fetched,
        "created": total_synced,
        "failed": total_failed,
        "skipped": total_skipped,
    }


async def main():
    async with httpx.AsyncClient() as client:
        logger.info("Getting tenant access token...")
        token = await get_tenant_token(client)
        logger.info("Token acquired.")

        logger.info("Starting sync (last %s months)...", SYNC_MONTHS)
        stats = await fetch_and_sync_recent(client, token)
        logger.info("Sync complete: %s", stats)


if __name__ == "__main__":
    asyncio.run(main())
