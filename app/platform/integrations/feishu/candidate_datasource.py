"""Candidate (招聘-候选人) Bitable datasource adapter.

Adapts Feishu Bitable API for the candidate table:
- Text fields read as [{"text": ..., "type": "text"}]
- Single-select fields read as plain strings
- Attachment fields (简历 PDF) read as [{"file_token": ..., "name": ..., "size": ...}]
- AI match report read from text field
"""

import logging
from datetime import date
from typing import Any

from app.platform.integrations.feishu.bitable import BitableClient
from app.platform.integrations.feishu.datasource import BitableDataSource
from app.core.config import get_settings

logger = logging.getLogger(__name__)
_settings = get_settings()

# ─── Field extraction helpers ───


def _extract_text(value: Any) -> str:
    """Extract plain text from Feishu text-field array format."""
    if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
        return value[0].get("text", "")
    if isinstance(value, dict):
        if "text" in value:
            return value.get("text", "")
        if "value" in value and isinstance(value["value"], list) and len(value["value"]) > 0:
            inner = value["value"][0]
            if isinstance(inner, dict) and "text" in inner:
                return inner.get("text", "")
            return str(inner)
    if isinstance(value, str):
        return value
    return str(value) if value is not None else ""


def _extract_single_select(value: Any) -> str:
    """Extract single-select option (plain string in Feishu)."""
    if isinstance(value, str):
        return value
    return str(value) if value is not None else ""


def _extract_attachments(value: Any) -> list[dict]:
    """Extract attachment array from Feishu attachment field."""
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    return []


# ─── Candidate datasource ───


class CandidateBitableDataSource:
    """Candidate datasource backed by Feishu Bitable."""

    def __init__(self) -> None:
        app_token = _settings.FEISHU_BITABLE_CANDIDATE_APP_TOKEN
        table_id = _settings.FEISHU_BITABLE_CANDIDATE_TABLE_ID
        self._ds = BitableDataSource(app_token=app_token, table_id=table_id)
        self.client = self._ds.client
        self.table_id = table_id

    # ─── Internal raw API ───

    async def _query(self, page_size: int = 500) -> list[dict[str, Any]]:
        return await self._ds.query(page_size=page_size)

    # ─── Public query API ───

    async def fetch_all(self, page_size: int = 500) -> list["CandidateRecord"]:
        """Fetch all candidate records from Bitable."""
        items = await self._query(page_size=page_size)
        return [CandidateRecord.from_api(item) for item in items]

    async def update_recommendation_level(
        self, record_id: str, level: str
    ) -> None:
        """Update recommendation level in Feishu Bitable."""
        await self._ds.update(
            record_id=record_id,
            fields={"推荐等级": level},
        )
        logger.info("Updated recommendation level in Feishu: %s -> %s", record_id, level)

    async def update(self, record_id: str, fields: dict[str, Any]) -> None:
        """Update candidate fields in Feishu Bitable."""
        await self._ds.update(record_id=record_id, fields=fields)
        logger.info("Updated candidate fields in Feishu: %s", record_id)

    async def delete(self, record_id: str) -> None:
        """Delete candidate record from Feishu Bitable."""
        await self._ds.delete(record_id=record_id)
        logger.info("Deleted candidate record from Feishu: %s", record_id)

    async def create(self, fields: dict[str, Any]) -> str:
        """Create a candidate record in Feishu Bitable."""
        record_id = await self._ds.create(fields)
        logger.info("Created candidate record in Feishu: %s", record_id)
        return record_id

    async def upload_resume(self, file_bytes: bytes, filename: str) -> dict:
        """Upload a resume PDF to Feishu Drive and return file metadata."""
        data = await self.client.upload_file(
            file_bytes=file_bytes,
            filename=filename,
            parent_type="bitable_file",
            parent_node=self._ds.app_token,
        )
        logger.info("Uploaded resume to Feishu Drive: %s", data.get("file_token"))
        return data

    async def get_resume_download_url(self, file_token: str) -> str:
        """Get temporary download URL for a resume attachment.

        Calls Feishu Drive API: GET /open-apis/drive/v1/medias/batch_get_tmp_download_url
        """
        from app.platform.integrations.feishu.client import FeishuClient

        client = FeishuClient()
        data = await client.request(
            "GET",
            "/drive/v1/medias/batch_get_tmp_download_url",
            params={"file_tokens": file_token},
        )
        items = data.get("tmp_download_urls", [])
        if not items:
            raise RuntimeError("No download URL returned from Feishu Drive API")
        return items[0].get("tmp_download_url", "")


class CandidateRecord:
    """Parsed candidate record from Bitable API."""

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw
        self.record_id: str = raw.get("record_id", "")
        fields = raw.get("fields", {})

        # Basic info
        self.name: str = _extract_text(fields.get("候选人姓名"))
        self.position: str = _extract_single_select(fields.get("应聘职位名称"))
        self.gender: str = _extract_text(fields.get("性别"))

        # Education
        self.school: str = _extract_text(fields.get("学校名称"))
        self.education: str = _extract_text(fields.get("学历"))
        self.major: str = _extract_text(fields.get("专业"))

        # AI report
        self.match_report: str = _extract_text(fields.get("候选人匹配度报告-AI.输出结果"))

        # Recommendation level
        self.recommendation_level: str = _extract_single_select(fields.get("推荐等级"))

        # Resume attachments
        self.resume_attachments: list[dict] = _extract_attachments(fields.get("简历 PDF"))

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> "CandidateRecord":
        return cls(raw)

    def to_dict(self) -> dict[str, Any]:
        """Export to plain dict suitable for local DB storage."""
        return {
            "feishu_record_id": self.record_id,
            "name": self.name,
            "position": self.position,
            "gender": self.gender,
            "school": self.school,
            "education": self.education,
            "major": self.major,
            "match_report": self.match_report,
            "recommendation_level": self.recommendation_level,
            "resume_attachments": self.resume_attachments,
        }
