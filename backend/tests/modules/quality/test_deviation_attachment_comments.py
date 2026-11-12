"""偏差附件批注 / 文档预览 service 层测试（不依赖真实数据库、MinIO 与 libreoffice）。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.core import storage as core_storage
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.modules.quality.qms import deviation_ledger_service as service_module
from app.modules.quality.qms.deviation_ledger_constants import LedgerStatus
from app.modules.quality.qms.deviation_ledger_models import DeviationAttachmentComment
from app.modules.quality.qms.deviation_ledger_schemas import (
    AttachmentCommentCreateRequest,
    AttachmentCommentUpdateRequest,
)
from app.modules.quality.qms.deviation_ledger_service import DeviationLedgerService

_LEDGER_ID = uuid.uuid4()
_FILE_ID = uuid.uuid4()
_AUTHOR_ID = uuid.uuid4()


class _EmptyResult:
    """空查询结果（头像 / 人员档案查询走这里）。"""

    def all(self) -> list[Any]:
        return []

    def scalars(self) -> _EmptyResult:
        return self


class _FakeDB:
    def __init__(self) -> None:
        self.committed = 0

    async def commit(self) -> None:
        self.committed += 1

    async def rollback(self) -> None:
        return None

    async def refresh(self, obj: Any) -> None:
        return None

    async def execute(self, *args: Any, **kwargs: Any) -> _EmptyResult:
        return _EmptyResult()

    async def scalar(self, *args: Any, **kwargs: Any) -> Any:
        return None


class _FakeLedgerRepo:
    def __init__(self, row: Any) -> None:
        self.row = row

    async def get_by_id(self, ledger_id: uuid.UUID) -> Any:
        if self.row is not None and self.row.id == ledger_id:
            return self.row
        return None

    async def get_by_id_for_update(self, ledger_id: uuid.UUID) -> Any:
        return await self.get_by_id(ledger_id)


class _FakeCommentRepo:
    """内存版批注仓储。"""

    def __init__(self, comments: list[DeviationAttachmentComment] | None = None) -> None:
        self.comments = list(comments or [])
        self.created: list[dict[str, Any]] = []
        self.soft_deleted: list[tuple[uuid.UUID, uuid.UUID, uuid.UUID]] = []
        self.summary: list[tuple[uuid.UUID, int, int]] = []

    async def list_by_file(self, ledger_id: uuid.UUID, file_id: uuid.UUID) -> list[DeviationAttachmentComment]:
        return [
            comment
            for comment in self.comments
            if comment.ledger_id == ledger_id and comment.file_id == file_id and not comment.is_deleted
        ]

    async def get(
        self,
        ledger_id: uuid.UUID,
        file_id: uuid.UUID,
        comment_id: uuid.UUID,
    ) -> DeviationAttachmentComment | None:
        for comment in self.comments:
            if (
                comment.id == comment_id
                and comment.ledger_id == ledger_id
                and comment.file_id == file_id
                and not comment.is_deleted
            ):
                return comment
        return None

    async def create(self, **fields: Any) -> DeviationAttachmentComment:
        self.created.append(fields)
        now = datetime.now(UTC)
        comment = DeviationAttachmentComment(
            id=uuid.uuid4(),
            created_at=now,
            updated_at=now,
            is_deleted=False,
            **fields,
        )
        self.comments.append(comment)
        return comment

    async def summary_by_ledger(self, ledger_id: uuid.UUID) -> list[tuple[uuid.UUID, int, int]]:
        return self.summary

    async def soft_delete_by_file(
        self,
        ledger_id: uuid.UUID,
        file_id: uuid.UUID,
        *,
        actor_id: uuid.UUID,
    ) -> int:
        self.soft_deleted.append((ledger_id, file_id, actor_id))
        return len(self.comments)


def _attachment() -> dict[str, Any]:
    return {
        "file_id": str(_FILE_ID),
        "file_name": "调查报告.doc",
        "object_key": f"deviation-ledger/{_LEDGER_ID}/{_FILE_ID}-report.doc",
        "size": 1024,
        "content_type": "application/msword",
        "uploaded_by": str(_AUTHOR_ID),
        "uploaded_by_name": "张三",
        "uploaded_at": "2026-11-01T08:00:00+00:00",
    }


def _row(
    *,
    status: str = LedgerStatus.PENDING_INVESTIGATION.value,
    attachments: list[dict[str, Any]] | None = None,
    records: list[dict[str, Any]] | None = None,
) -> Any:
    return SimpleNamespace(
        id=_LEDGER_ID,
        status=status,
        returned_step=None,
        attachments=[_attachment()] if attachments is None else attachments,
        investigation_records=records or [],
        handler_ids=[_AUTHOR_ID],
        reporter_id=_AUTHOR_ID,
    )


def _comment(
    *,
    content: str = "第二条记录缺少复核人签字",
    status: str = "open",
    created_by: uuid.UUID = _AUTHOR_ID,
    page_no: int | None = 2,
) -> DeviationAttachmentComment:
    now = datetime.now(UTC)
    return DeviationAttachmentComment(
        id=uuid.uuid4(),
        ledger_id=_LEDGER_ID,
        file_id=_FILE_ID,
        file_name="调查报告.doc",
        page_no=page_no,
        anchor_text=None,
        content=content,
        status=status,
        author_name="张三",
        resolved_by=None,
        resolved_by_name=None,
        resolved_at=None,
        created_by=created_by,
        updated_by=created_by,
        created_at=now,
        updated_at=now,
        is_deleted=False,
    )


def _service(row: Any, comments: _FakeCommentRepo | None = None) -> tuple[DeviationLedgerService, _FakeCommentRepo]:
    service = DeviationLedgerService(cast(Any, _FakeDB()))
    comment_repo = comments or _FakeCommentRepo()
    service.repo = cast(Any, _FakeLedgerRepo(row))
    service.comment_repo = cast(Any, comment_repo)
    return service, comment_repo


# ── 新增批注 ──────────────────────────────────────────────────────────


async def test_add_comment_records_snapshot_and_open_status() -> None:
    service, repo = _service(_row())
    item = await service.add_attachment_comment(
        _LEDGER_ID,
        _FILE_ID,
        AttachmentCommentCreateRequest(content="  页 2 缺少复核人签字  ", page_no=2),
        actor_id=_AUTHOR_ID,
        actor_name="张三",
    )
    assert item.status == "open"
    assert item.content == "页 2 缺少复核人签字"
    assert item.file_name == "调查报告.doc"
    assert item.page_no == 2
    assert item.author_id == _AUTHOR_ID
    assert repo.created[0]["ledger_id"] == _LEDGER_ID
    assert repo.created[0]["created_by"] == _AUTHOR_ID


async def test_add_comment_rejects_closed_ledger() -> None:
    service, _ = _service(_row(status=LedgerStatus.CLOSED.value))
    with pytest.raises(BadRequestException):
        await service.add_attachment_comment(
            _LEDGER_ID,
            _FILE_ID,
            AttachmentCommentCreateRequest(content="追加意见"),
            actor_id=_AUTHOR_ID,
            actor_name="张三",
        )


async def test_add_comment_rejects_unknown_attachment() -> None:
    service, _ = _service(_row(attachments=[]))
    with pytest.raises(NotFoundException):
        await service.add_attachment_comment(
            _LEDGER_ID,
            uuid.uuid4(),
            AttachmentCommentCreateRequest(content="追加意见"),
            actor_id=_AUTHOR_ID,
            actor_name="张三",
        )


async def test_add_comment_finds_attachment_inside_investigation_record() -> None:
    record = {"seq": 1, "attachments": [_attachment()]}
    service, _ = _service(_row(attachments=[], records=[record]))
    item = await service.add_attachment_comment(
        _LEDGER_ID,
        _FILE_ID,
        AttachmentCommentCreateRequest(content="记录附件也能批注"),
        actor_id=_AUTHOR_ID,
        actor_name="张三",
    )
    assert item.file_id == _FILE_ID


# ── 列表与汇总 ────────────────────────────────────────────────────────


async def test_list_comments_counts_open_items() -> None:
    repo = _FakeCommentRepo([_comment(), _comment(content="已确认", status="resolved")])
    service, _ = _service(_row(), repo)
    data = await service.list_attachment_comments(_LEDGER_ID, _FILE_ID)
    assert data.total == 2
    assert data.open_count == 1
    assert [item.status for item in data.items] == ["open", "resolved"]


async def test_summary_maps_grouped_counts() -> None:
    repo = _FakeCommentRepo()
    repo.summary = [(_FILE_ID, 2, 5)]
    service, _ = _service(_row(), repo)
    data = await service.attachment_comment_summary(_LEDGER_ID)
    assert len(data.items) == 1
    assert data.items[0].file_id == _FILE_ID
    assert data.items[0].open_count == 2
    assert data.items[0].total_count == 5


# ── 修改与删除 ────────────────────────────────────────────────────────


async def test_update_comment_rejects_other_author_content_edit() -> None:
    service, repo = _service(_row(), _FakeCommentRepo([_comment(created_by=uuid.uuid4())]))
    with pytest.raises(ForbiddenException):
        await service.update_attachment_comment(
            _LEDGER_ID,
            _FILE_ID,
            repo.comments[0].id,
            AttachmentCommentUpdateRequest(content="别人改不了的正文"),
            actor_id=_AUTHOR_ID,
            actor_name="张三",
        )


async def test_update_comment_resolves_and_clears_resolution() -> None:
    comment = _comment()
    service, repo = _service(_row(), _FakeCommentRepo([comment]))
    resolved = await service.update_attachment_comment(
        _LEDGER_ID,
        _FILE_ID,
        comment.id,
        AttachmentCommentUpdateRequest(status="resolved"),
        actor_id=uuid.uuid4(),
        actor_name="李四",
    )
    assert resolved.status == "resolved"
    assert resolved.resolved_by_name == "李四"
    assert resolved.resolved_at is not None

    reopened = await service.update_attachment_comment(
        _LEDGER_ID,
        _FILE_ID,
        comment.id,
        AttachmentCommentUpdateRequest(status="open"),
        actor_id=uuid.uuid4(),
        actor_name="李四",
    )
    assert reopened.status == "open"
    assert reopened.resolved_at is None


async def test_update_comment_requires_content_or_status() -> None:
    comment = _comment()
    service, repo = _service(_row(), _FakeCommentRepo([comment]))
    with pytest.raises(BadRequestException):
        await service.update_attachment_comment(
            _LEDGER_ID,
            _FILE_ID,
            comment.id,
            AttachmentCommentUpdateRequest(),
            actor_id=_AUTHOR_ID,
            actor_name="张三",
        )


async def test_delete_comment_soft_deletes_for_author() -> None:
    comment = _comment()
    service, repo = _service(_row(), _FakeCommentRepo([comment]))
    result = await service.delete_attachment_comment(
        _LEDGER_ID,
        _FILE_ID,
        comment.id,
        actor_id=_AUTHOR_ID,
    )
    assert result.deleted is True
    assert result.id == comment.id
    assert comment.is_deleted is True


async def test_delete_comment_rejects_other_author() -> None:
    comment = _comment(created_by=uuid.uuid4())
    service, repo = _service(_row(), _FakeCommentRepo([comment]))
    with pytest.raises(ForbiddenException):
        await service.delete_attachment_comment(
            _LEDGER_ID,
            _FILE_ID,
            comment.id,
            actor_id=_AUTHOR_ID,
        )


async def test_remove_attachment_cascades_comment_soft_delete(monkeypatch: pytest.MonkeyPatch) -> None:
    service, repo = _service(_row())
    monkeypatch.setattr(core_storage, "is_enabled", lambda: False)

    async def _fake_detail(*args: Any, **kwargs: Any) -> Any:
        return SimpleNamespace(id=_LEDGER_ID)

    monkeypatch.setattr(service, "_build_detail", _fake_detail)
    await service.remove_attachment(_LEDGER_ID, _FILE_ID, actor_id=_AUTHOR_ID, actor_is_superuser=True)
    assert repo.soft_deleted == [(_LEDGER_ID, _FILE_ID, _AUTHOR_ID)]


# ── 预览 ──────────────────────────────────────────────────────────────


class _FakeConversion:
    def __init__(self, result: bytes | None) -> None:
        self.result = result
        self.calls: list[tuple[bytes, str]] = []

    def convert_bytes_to_docx(self, data: bytes, filename: str, timeout: int = 30) -> bytes | None:
        self.calls.append((data, filename))
        return self.result


def _patch_storage(
    monkeypatch: pytest.MonkeyPatch,
    objects: dict[str, tuple[bytes, str]],
    uploads: list[tuple[str, bytes]],
) -> None:
    monkeypatch.setattr(core_storage, "is_enabled", lambda: True)
    monkeypatch.setattr(core_storage, "get_object", lambda module, key: objects.get(key))

    def _upload(module: str, key: str, data: bytes, size: int, content_type: str) -> str:
        uploads.append((key, data))
        return key

    monkeypatch.setattr(core_storage, "upload_object", _upload)


async def test_preview_streams_pdf_without_conversion(monkeypatch: pytest.MonkeyPatch) -> None:
    objects = {_attachment()["object_key"]: (b"%PDF-1.7", "application/pdf")}
    uploads: list[tuple[str, bytes]] = []
    _patch_storage(monkeypatch, objects, uploads)
    row = _row(attachments=[{**_attachment(), "content_type": "application/pdf", "file_name": "报告.pdf"}])
    service, _ = _service(row)

    name, content, content_type = await service.get_attachment_preview(_LEDGER_ID, _FILE_ID)
    assert name == "报告.pdf"
    assert content == b"%PDF-1.7"
    assert content_type == "application/pdf"
    assert uploads == []


async def test_preview_converts_doc_and_caches_result(monkeypatch: pytest.MonkeyPatch) -> None:
    objects = {_attachment()["object_key"]: (b"legacy-doc", "application/msword")}
    uploads: list[tuple[str, bytes]] = []
    _patch_storage(monkeypatch, objects, uploads)
    conversion = _FakeConversion(b"converted-docx")
    monkeypatch.setattr(service_module, "get_file_conversion", lambda: conversion)
    service, _ = _service(_row())

    name, content, content_type = await service.get_attachment_preview(_LEDGER_ID, _FILE_ID)
    assert name == "调查报告.docx"
    assert content == b"converted-docx"
    assert content_type == service_module._DOCX_CONTENT_TYPE
    assert conversion.calls == [(b"legacy-doc", "调查报告.doc")]
    assert uploads[0][0] == f"deviation-ledger/{_LEDGER_ID}/.preview/{_FILE_ID}.docx"


async def test_preview_uses_cached_conversion(monkeypatch: pytest.MonkeyPatch) -> None:
    cache_key = f"deviation-ledger/{_LEDGER_ID}/.preview/{_FILE_ID}.docx"
    objects = {cache_key: (b"cached-docx", service_module._DOCX_CONTENT_TYPE)}
    _patch_storage(monkeypatch, objects, [])
    conversion = _FakeConversion(b"should-not-be-used")
    monkeypatch.setattr(service_module, "get_file_conversion", lambda: conversion)
    service, _ = _service(_row())

    _, content, _ = await service.get_attachment_preview(_LEDGER_ID, _FILE_ID)
    assert content == b"cached-docx"
    assert conversion.calls == []


async def test_preview_raises_when_conversion_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    objects = {_attachment()["object_key"]: (b"legacy-doc", "application/msword")}
    _patch_storage(monkeypatch, objects, [])
    monkeypatch.setattr(service_module, "get_file_conversion", lambda: _FakeConversion(None))
    service, _ = _service(_row())

    with pytest.raises(BadRequestException):
        await service.get_attachment_preview(_LEDGER_ID, _FILE_ID)


async def test_preview_rejects_unsupported_type(monkeypatch: pytest.MonkeyPatch) -> None:
    objects = {_attachment()["object_key"]: (b"PK", "application/zip")}
    _patch_storage(monkeypatch, objects, [])
    row = _row(attachments=[{**_attachment(), "content_type": "application/zip", "file_name": "证据.zip"}])
    service, _ = _service(row)

    with pytest.raises(BadRequestException):
        await service.get_attachment_preview(_LEDGER_ID, _FILE_ID)
