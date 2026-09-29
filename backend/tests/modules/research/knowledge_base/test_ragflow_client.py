"""RAGFlow 客户端协议层测试：信封解包、错误映射、分页与召回参数（不发真实请求）。"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.core.config import RagflowSettings
from app.modules.research.knowledge_base.ragflow import (
    RagflowClient,
    RagflowError,
    filename_from_disposition,
)

SETTINGS = RagflowSettings(
    base_url="http://ragflow.local:9380",
    api_key="ragflow-test-key",
    default_embedding_model="text-embedding-v4@tongyi@Tongyi-Qianwen",
)


def _response(payload: Any, status_code: int = 200) -> httpx.Response:
    return httpx.Response(status_code, json=payload, request=httpx.Request("GET", "http://ragflow.local:9380"))


def test_unwrap_returns_data_field() -> None:
    client = RagflowClient(SETTINGS)
    assert client._unwrap(_response({"code": 0, "data": {"id": "ds-1"}}), "/api/v1/datasets") == {"id": "ds-1"}


def test_unwrap_raises_on_business_error() -> None:
    client = RagflowClient(SETTINGS)
    with pytest.raises(RagflowError) as exc:
        client._unwrap(_response({"code": 102, "message": "You don't own the dataset"}), "/api/v1/datasets")
    assert "You don't own the dataset" in str(exc.value)


def test_unwrap_raises_on_http_error() -> None:
    client = RagflowClient(SETTINGS)
    with pytest.raises(RagflowError) as exc:
        client._unwrap(_response({"detail": "nope"}, status_code=500), "/api/v1/datasets")
    assert exc.value.status == 500


def test_unwrap_raises_on_non_json() -> None:
    client = RagflowClient(SETTINGS)
    raw = httpx.Response(200, text="<html>", request=httpx.Request("GET", "http://ragflow.local:9380"))
    with pytest.raises(RagflowError):
        client._unwrap(raw, "/api/v1/datasets")


async def test_request_requires_configuration() -> None:
    client = RagflowClient(RagflowSettings())
    assert not client.configured
    with pytest.raises(RagflowError):
        await client._request("GET", "/api/v1/datasets")


async def test_create_dataset_applies_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    client = RagflowClient(SETTINGS)
    calls: list[dict[str, Any]] = []
    detail = {"id": "ds-9", "embedding_model_name": "text-embedding-v4@tongyi@Tongyi-Qianwen", "chunk_method": "naive"}

    async def fake_request(method: str, path: str, **kwargs: Any) -> Any:
        calls.append({"method": method, "path": path, **kwargs})
        # 第二次调用是回读列表补全向量模型名
        return {"id": "ds-9"} if len(calls) == 1 else [detail]

    monkeypatch.setattr(client, "_request", fake_request)
    dataset = await client.create_dataset("米诺地尔-项目知识库", description="研发项目资料库")

    assert dataset["id"] == "ds-9"
    # 创建响应缺 embedding_model_name，需回读列表补全（否则前端只能显示占位符）
    assert dataset["embedding_model_name"] == detail["embedding_model_name"]
    assert dataset["chunk_method"] == "naive"
    body = calls[0]["json_body"]
    assert calls[0]["path"] == "/api/v1/datasets"
    assert calls[0]["method"] == "POST"
    assert body["name"] == "米诺地尔-项目知识库"
    assert body["embedding_model"] == SETTINGS.default_embedding_model
    assert body["chunk_method"] == "naive"
    assert body["language"] == "Chinese"
    assert calls[1]["path"] == "/api/v1/datasets"


async def test_create_dataset_accepts_list_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """部分版本创建响应把对象包在列表里，客户端要能取出来。"""
    client = RagflowClient(SETTINGS)
    calls: list[str] = []

    async def fake_request(method: str, path: str, **kwargs: Any) -> Any:
        calls.append(path)
        if len(calls) == 1:
            return [{"id": "ds-10", "chunk_method": "naive"}]
        return []

    monkeypatch.setattr(client, "_request", fake_request)
    dataset = await client.create_dataset("测试库")

    assert dataset["id"] == "ds-10"


async def test_list_documents_paginates(monkeypatch: pytest.MonkeyPatch) -> None:
    client = RagflowClient(SETTINGS)
    pages = [
        {"docs": [{"id": "d1"}, {"id": "d2"}], "total": 3},
        {"docs": [{"id": "d3"}], "total": 3},
    ]
    calls: list[dict[str, Any]] = []

    async def fake_request(method: str, path: str, **kwargs: Any) -> Any:
        calls.append(kwargs.get("params", {}))
        return pages[len(calls) - 1]

    monkeypatch.setattr(client, "_request", fake_request)
    docs = await client.list_documents("ds-1", page_size=2)

    assert [doc["id"] for doc in docs] == ["d1", "d2", "d3"]
    assert len(calls) == 2


async def test_parse_requires_document_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    client = RagflowClient(SETTINGS)
    calls: list[Any] = []

    async def fake_request(method: str, path: str, **kwargs: Any) -> Any:
        calls.append(kwargs.get("json_body"))
        return None

    monkeypatch.setattr(client, "_request", fake_request)
    await client.parse_documents("ds-1", [])
    await client.parse_documents("ds-1", ["d1"])

    assert calls == [{"document_ids": ["d1"]}]


async def test_delete_documents_uses_ids_field(monkeypatch: pytest.MonkeyPatch) -> None:
    client = RagflowClient(SETTINGS)
    captured: dict[str, Any] = {}

    async def fake_request(method: str, path: str, **kwargs: Any) -> Any:
        captured.update({"method": method, "path": path, **kwargs})
        return {"deleted": 1}

    monkeypatch.setattr(client, "_request", fake_request)
    await client.delete_documents("ds-1", ["d1"])

    assert captured["method"] == "DELETE"
    assert captured["json_body"] == {"ids": ["d1"]}


async def test_retrieval_passes_search_params(monkeypatch: pytest.MonkeyPatch) -> None:
    client = RagflowClient(SETTINGS)
    captured: dict[str, Any] = {}

    async def fake_request(method: str, path: str, **kwargs: Any) -> Any:
        captured.update({"path": path, **kwargs})
        return {"chunks": [{"content": "命中片段", "document_keyword": "doc.docx"}]}

    monkeypatch.setattr(client, "_request", fake_request)
    chunks = await client.retrieval(
        "原研企业", ["ds-1"], top_k=4, similarity_threshold=0.3, vector_similarity_weight=0.5
    )

    assert chunks[0]["content"] == "命中片段"
    body = captured["json_body"]
    assert body["question"] == "原研企业"
    assert body["dataset_ids"] == ["ds-1"]
    assert body["top_k"] == 4
    assert body["similarity_threshold"] == 0.3
    assert body["vector_similarity_weight"] == 0.5
    assert body["page_size"] == 4


async def test_retrieval_skips_empty_question(monkeypatch: pytest.MonkeyPatch) -> None:
    client = RagflowClient(SETTINGS)

    async def fake_request(*args: Any, **kwargs: Any) -> Any:  # pragma: no cover - 不应被调用
        raise AssertionError("空问题不应发起召回请求")

    monkeypatch.setattr(client, "_request", fake_request)
    assert await client.retrieval("   ", ["ds-1"]) == []
    assert await client.retrieval("问题", []) == []


# ---------------------------------------------------------------------------
# 预览 / 下载（原文文件流与解析切片）
# ---------------------------------------------------------------------------


def test_filename_from_disposition_prefers_rfc5987() -> None:
    encoded = "%E7%B1%B3%E8%AF%BA%E5%9C%B0%E5%B0%94.docx"  # 米诺地尔.docx

    assert filename_from_disposition("") == ""
    assert filename_from_disposition('attachment; filename="report.docx"') == "report.docx"
    assert filename_from_disposition(f"attachment; filename=\"a.docx\"; filename*=UTF-8''{encoded}") == "米诺地尔.docx"


async def test_download_document_returns_bytes_and_meta(monkeypatch: pytest.MonkeyPatch) -> None:
    client = RagflowClient(SETTINGS)
    captured: dict[str, Any] = {}

    async def fake_raw(method: str, path: str, **kwargs: Any) -> httpx.Response:
        captured["method"] = method
        captured["path"] = path
        return httpx.Response(
            200,
            content=b"docx-bytes",
            headers={
                "content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "content-disposition": "attachment; filename*=UTF-8''%E7%B1%B3%E8%AF%BA%E5%9C%B0%E5%B0%94.docx",
            },
            request=httpx.Request("GET", "http://ragflow.local:9380"),
        )

    monkeypatch.setattr(client, "_request_raw", fake_raw)
    content, content_type, filename = await client.download_document("ds-1", "doc-1")

    # 文档详情端点本身就是文件流：路径不能带 /download 子路径
    assert captured["path"] == "/api/v1/datasets/ds-1/documents/doc-1"
    assert content == b"docx-bytes"
    assert content_type.endswith("wordprocessingml.document")
    assert filename == "米诺地尔.docx"


async def test_download_image_uses_documents_images_path(monkeypatch: pytest.MonkeyPatch) -> None:
    client = RagflowClient(SETTINGS)
    captured: dict[str, Any] = {}

    async def fake_raw(method: str, path: str, **kwargs: Any) -> httpx.Response:
        captured["path"] = path
        return httpx.Response(
            200,
            content=b"jpeg-bytes",
            headers={"content-type": "image/jpeg"},
            request=httpx.Request("GET", "http://ragflow.local:9380"),
        )

    monkeypatch.setattr(client, "_request_raw", fake_raw)
    content, content_type = await client.download_image("ds-1-abc123")

    # 注意不是 /datasets/{id}/documents/{id}/... ，图片端点在 documents 下
    assert captured["path"] == "/api/v1/documents/images/ds-1-abc123"
    assert content == b"jpeg-bytes"
    assert content_type == "image/jpeg"


async def test_list_document_chunks_normalizes_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    client = RagflowClient(SETTINGS)
    captured: dict[str, Any] = {}

    async def fake_request(method: str, path: str, **kwargs: Any) -> Any:
        captured["path"] = path
        captured["params"] = kwargs.get("params")
        return {"chunks": [{"id": "c1", "content": "片段"}], "total": 7}

    monkeypatch.setattr(client, "_request", fake_request)
    total, chunks = await client.list_document_chunks("ds-1", "doc-1", page=2, page_size=3)

    assert captured["path"] == "/api/v1/datasets/ds-1/documents/doc-1/chunks"
    assert captured["params"] == {"page": 2, "page_size": 3}
    assert total == 7
    assert chunks[0]["content"] == "片段"


async def test_list_document_chunks_accepts_list_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    client = RagflowClient(SETTINGS)

    async def fake_request(*args: Any, **kwargs: Any) -> Any:
        return [{"id": "c1", "content": "a"}, {"id": "c2", "content": "b"}]

    monkeypatch.setattr(client, "_request", fake_request)
    total, chunks = await client.list_document_chunks("ds-1", "doc-1")

    assert total == 2
    assert [chunk["id"] for chunk in chunks] == ["c1", "c2"]
