"""RAGFlow HTTP 客户端：只做协议转换与错误映射，不含业务规则、不碰数据库。

RAGFlow v0.27.x 的 REST 约定：

- 统一信封 ``{"code": 0, "data": ..., "message": "success"}``，``code != 0`` 视为业务失败
- 鉴权 ``Authorization: Bearer <api_key>``
- 数据集（= 知识库）→ ``/api/v1/datasets``；文档 → ``/api/v1/datasets/{id}/documents``
- 解析 → ``POST /api/v1/datasets/{id}/documents/parse``（异步，进度从文档列表读）
- 召回 → ``POST /api/v1/retrieval``

外部调用的容错按仓库规范：最多 3 次重试、指数退避（1s/2s/4s），只重试网络与 5xx，
业务错误（code != 0）不重试——重试也不会变好，只会拖长用户等待。
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import unquote

import httpx

from app.core.config import RagflowSettings, get_settings

logger = logging.getLogger(__name__)

# 重试退避序列：3 次尝试、指数退避
_RETRY_DELAYS = (1.0, 2.0, 4.0)
_RETRYABLE_STATUS = (429, 500, 502, 503, 504)

# Content-Disposition 里的文件名：优先 RFC 5987 的 filename*，回退普通 filename
_FILENAME_STAR_RE = re.compile(r"filename\*\s*=\s*UTF-8''([^;]+)", flags=re.IGNORECASE)
_FILENAME_RE = re.compile(r'filename\s*=\s*"?([^";]+)"?', flags=re.IGNORECASE)


def filename_from_disposition(value: str) -> str:
    """从 Content-Disposition 解析文件名；解析不出返回空串（调用方用本地记录兜底）。"""
    if not value:
        return ""
    match = _FILENAME_STAR_RE.search(value)
    if match:
        return unquote(match.group(1)).strip()
    match = _FILENAME_RE.search(value)
    return match.group(1).strip() if match else ""


class RagflowError(RuntimeError):
    """RAGFlow 调用失败：携带用户可读原因，供 API 层转成业务异常。"""

    def __init__(self, message: str, *, status: int = 0, code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code


class RagflowClient:
    """RAGFlow 异步客户端（短生命周期，按调用创建）。"""

    def __init__(self, settings: RagflowSettings | None = None) -> None:
        self._settings = settings or get_settings().ragflow

    @property
    def settings(self) -> RagflowSettings:
        return self._settings

    @property
    def configured(self) -> bool:
        return bool(self._settings.base_url and self._settings.api_key)

    def _url(self, path: str) -> str:
        return f"{self._settings.base_url.rstrip('/')}{path}"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._settings.api_key}"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        files: list[tuple[str, tuple[str, bytes, str]]] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        """发一次请求并解包信封，返回 ``data`` 字段。

        Raises:
            RagflowError: 未配置 / 网络失败 / HTTP 非 2xx / 业务 code != 0
        """
        if not self.configured:
            raise RagflowError("知识库服务未配置（缺少 RAGFLOW__BASE_URL 或 RAGFLOW__API_KEY）")
        effective_timeout = timeout or self._settings.timeout_seconds
        last_error: Exception | None = None
        for attempt, delay in enumerate(_RETRY_DELAYS, start=1):
            try:
                async with httpx.AsyncClient(timeout=effective_timeout) as client:
                    response = await client.request(
                        method,
                        self._url(path),
                        headers=self._headers(),
                        json=json_body,
                        files=files,
                        params=params,
                    )
                if response.status_code in _RETRYABLE_STATUS and attempt < len(_RETRY_DELAYS):
                    logger.warning(
                        "知识库服务返回可重试状态，稍后重试",
                        extra={"path": path, "status": response.status_code, "attempt": attempt},
                    )
                    await asyncio.sleep(delay)
                    continue
                return self._unwrap(response, path)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt < len(_RETRY_DELAYS):
                    logger.warning(
                        "知识库服务请求失败，稍后重试", extra={"path": path, "attempt": attempt, "error": str(exc)}
                    )
                    await asyncio.sleep(delay)
                    continue
                raise RagflowError(f"知识库服务连接失败：{exc}") from exc
        raise RagflowError(f"知识库服务请求失败：{last_error}")

    async def _request_raw(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        """发一次请求并返回原始响应，用于响应体不是 JSON 的文件流。

        与 ``_request`` 同一套重试策略，但不解信封、不解析 JSON。

        Raises:
            RagflowError: 未配置 / 网络失败（重试后仍失败）/ HTTP 非 2xx
        """
        if not self.configured:
            raise RagflowError("知识库服务未配置（缺少 RAGFLOW__BASE_URL 或 RAGFLOW__API_KEY）")
        effective_timeout = timeout or self._settings.timeout_seconds
        last_error: Exception | None = None
        for attempt, delay in enumerate(_RETRY_DELAYS, start=1):
            try:
                async with httpx.AsyncClient(timeout=effective_timeout) as client:
                    response = await client.request(method, self._url(path), headers=self._headers(), params=params)
                if response.status_code in _RETRYABLE_STATUS and attempt < len(_RETRY_DELAYS):
                    logger.warning(
                        "知识库服务返回可重试状态，稍后重试",
                        extra={"path": path, "status": response.status_code, "attempt": attempt},
                    )
                    await asyncio.sleep(delay)
                    continue
                if response.status_code >= 400:
                    raise RagflowError(
                        f"知识库服务返回 {response.status_code}：{response.text[:300]}",
                        status=response.status_code,
                    )
                return response
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt < len(_RETRY_DELAYS):
                    logger.warning(
                        "知识库服务请求失败，稍后重试", extra={"path": path, "attempt": attempt, "error": str(exc)}
                    )
                    await asyncio.sleep(delay)
                    continue
                raise RagflowError(f"知识库服务连接失败：{exc}") from exc
        raise RagflowError(f"知识库服务请求失败：{last_error}")

    def _unwrap(self, response: httpx.Response, path: str) -> Any:
        """HTTP 状态与业务信封两层校验。"""
        if response.status_code >= 400:
            detail = response.text[:300]
            raise RagflowError(f"知识库服务返回 {response.status_code}：{detail}", status=response.status_code)
        try:
            payload = response.json()
        except ValueError as exc:
            raise RagflowError("知识库服务返回了非 JSON 响应") from exc
        if isinstance(payload, dict) and "code" in payload and payload.get("code") not in (0, None):
            raise RagflowError(
                f"知识库服务处理失败：{payload.get('message') or payload.get('error') or payload['code']}",
                code=int(payload["code"]) if isinstance(payload["code"], int) else None,
            )
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload

    # ------------------------------------------------------------------
    # 数据集（知识库）
    # ------------------------------------------------------------------

    async def create_dataset(
        self,
        name: str,
        *,
        description: str = "",
        embedding_model: str = "",
        chunk_method: str = "",
        language: str = "",
    ) -> dict[str, Any]:
        """新建数据集，返回含 ``id`` 的数据集对象。"""
        body: dict[str, Any] = {"name": name, "permission": "me"}
        if description:
            body["description"] = description
        model = embedding_model or self._settings.default_embedding_model
        if model:
            body["embedding_model"] = model
        body["chunk_method"] = chunk_method or self._settings.default_chunk_method
        body["language"] = language or self._settings.default_language
        data = await self._request("POST", "/api/v1/datasets", json_body=body)
        # 不同版本创建响应可能直接给对象或包一层列表，统一取对象
        created: dict[str, Any] = {}
        if isinstance(data, dict):
            created = data
        elif isinstance(data, list) and data and isinstance(data[0], dict):
            created = data[0]
        dataset_id = str(created.get("id") or "")
        if not dataset_id:
            raise RagflowError("知识库服务未返回数据集 ID")
        # 创建响应只有 ID 与解析参数；向量模型名（embedding_model_name）只有列表接口才回填，
        # 故回读一次列表补全，供前端展示与留档
        try:
            rows = await self.list_datasets(dataset_id=dataset_id, page_size=10)
        except RagflowError:
            rows = []
        row = next((item for item in rows if str(item.get("id")) == dataset_id), {})
        for key, value in row.items():
            # 创建响应里 embedding_model_name 常常是 null，占位不算已填，需要被列表值覆盖
            if value and not created.get(key):
                created[key] = value
        return created

    async def list_datasets(
        self, *, page: int = 1, page_size: int = 30, dataset_id: str = "", name: str = ""
    ) -> list[dict[str, Any]]:
        """数据集列表（可按 id / 名称过滤）。"""
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if dataset_id:
            params["id"] = dataset_id
        if name:
            params["name"] = name
        data = await self._request("GET", "/api/v1/datasets", params=params)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            items = data.get("items") or data.get("datasets") or []
            return [item for item in items if isinstance(item, dict)]
        return []

    async def get_dataset(self, dataset_id: str) -> dict[str, Any]:
        data = await self._request("GET", f"/api/v1/datasets/{dataset_id}")
        return data if isinstance(data, dict) else {}

    async def delete_datasets(self, dataset_ids: list[str]) -> None:
        if not dataset_ids:
            return
        await self._request("DELETE", "/api/v1/datasets", json_body={"ids": dataset_ids})

    # ------------------------------------------------------------------
    # 文档
    # ------------------------------------------------------------------

    async def upload_document(
        self, dataset_id: str, filename: str, content: bytes, mime: str = "application/octet-stream"
    ) -> list[dict[str, Any]]:
        """上传一份文档，返回该文件对应的文档对象列表（正常为 1 条）。"""
        data = await self._request(
            "POST",
            f"/api/v1/datasets/{dataset_id}/documents",
            files=[("file", (filename, content, mime))],
            timeout=self._settings.upload_timeout_seconds,
        )
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            return [data]
        return []

    async def list_documents(
        self, dataset_id: str, *, page_size: int = 100, max_pages: int = 20
    ) -> list[dict[str, Any]]:
        """分页拉全量文档（含 run/progress/progress_msg 等解析状态）。"""
        documents: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            data = await self._request(
                "GET",
                f"/api/v1/datasets/{dataset_id}/documents",
                params={"page": page, "page_size": page_size, "orderby": "create_time", "desc": False},
            )
            docs: list[Any] = []
            total = 0
            if isinstance(data, dict):
                docs = data.get("docs") or data.get("data") or []
                total = int(data.get("total") or 0)
            elif isinstance(data, list):
                docs = data
            documents.extend(doc for doc in docs if isinstance(doc, dict))
            if len(docs) < page_size or (total and len(documents) >= total):
                break
        return documents

    async def parse_documents(self, dataset_id: str, document_ids: list[str]) -> None:
        """触发解析（异步，立即返回）。"""
        if not document_ids:
            return
        await self._request(
            "POST",
            f"/api/v1/datasets/{dataset_id}/documents/parse",
            json_body={"document_ids": document_ids},
        )

    async def stop_documents(self, dataset_id: str, document_ids: list[str]) -> None:
        """中断解析（用于删除前或人工中止）。"""
        if not document_ids:
            return
        await self._request(
            "POST",
            f"/api/v1/datasets/{dataset_id}/documents/stop",
            json_body={"document_ids": document_ids},
        )

    async def delete_documents(self, dataset_id: str, document_ids: list[str]) -> None:
        if not document_ids:
            return
        await self._request(
            "DELETE",
            f"/api/v1/datasets/{dataset_id}/documents",
            json_body={"ids": document_ids},
        )

    async def download_document(self, dataset_id: str, document_id: str) -> tuple[bytes, str, str]:
        """取文档原始文件，返回 ``(字节流, Content-Type, 响应里的文件名)``。

        注意：v0.27 的 SDK **没有** ``/download`` 子路径（实测 404）——文档详情端点
        ``GET /api/v1/datasets/{ds}/documents/{doc}`` 本身就是文件字节流。
        文件名可能解析不出（部分版本不回 Content-Disposition），由调用方用本地记录兜底。
        """
        response = await self._request_raw("GET", f"/api/v1/datasets/{dataset_id}/documents/{document_id}")
        content_type = response.headers.get("content-type", "") or "application/octet-stream"
        filename = filename_from_disposition(response.headers.get("content-disposition", ""))
        return response.content, content_type, filename

    async def download_image(self, image_id: str) -> tuple[bytes, str]:
        """取切片关联的图片字节流（PDF 页图 / 图注配图）。

        v0.27 的端点：``GET /api/v1/documents/images/{image_id}``，其中
        ``image_id`` 形如 ``{dataset_id}-{存储对象名}``，服务端只按第一个连字符
        拆成 bucket / object 去对象存储取，**不做库级归属校验**（所以调用方要自己校验）。
        取不到时返回业务错误（`Image not found.`）而不是 404。
        """
        response = await self._request_raw("GET", f"/api/v1/documents/images/{image_id}")
        content_type = response.headers.get("content-type", "") or "application/octet-stream"
        if "json" in content_type.lower():
            # 图片不存在时 RAGFlow 也是 HTTP 200 + JSON 错误信封，不能当图片透传
            detail = "Image not found."
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    detail = str(payload.get("message") or payload.get("error") or detail)
            except ValueError:
                detail = response.text[:120] or detail
            raise RagflowError(f"知识库服务未返回图片：{detail}")
        return response.content, content_type

    async def list_document_chunks(
        self,
        dataset_id: str,
        document_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
        keywords: str = "",
    ) -> tuple[int, list[dict[str, Any]]]:
        """解析切片分页，返回 ``(总数, 切片列表)``；切片含 ``content`` / ``positions``。"""
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if keywords:
            params["keywords"] = keywords
        data = await self._request(
            "GET",
            f"/api/v1/datasets/{dataset_id}/documents/{document_id}/chunks",
            params=params,
        )
        if isinstance(data, dict):
            raw = data.get("chunks") or []
            total = int(data.get("total") or len(raw))
        elif isinstance(data, list):
            raw, total = data, len(data)
        else:
            raw, total = [], 0
        return total, [chunk for chunk in raw if isinstance(chunk, dict)]

    # ------------------------------------------------------------------
    # 召回
    # ------------------------------------------------------------------

    async def retrieval(
        self,
        question: str,
        dataset_ids: list[str],
        *,
        top_k: int = 6,
        similarity_threshold: float = 0.2,
        vector_similarity_weight: float = 0.3,
        page_size: int = 0,
    ) -> list[dict[str, Any]]:
        """按问题召回切片，返回 RAGFlow 原始 chunk 列表（含 content / document_keyword）。"""
        if not question.strip() or not dataset_ids:
            return []
        body: dict[str, Any] = {
            "question": question,
            "dataset_ids": dataset_ids,
            "top_k": top_k,
            "similarity_threshold": similarity_threshold,
            "vector_similarity_weight": vector_similarity_weight,
            "page": 1,
            "page_size": page_size or top_k,
        }
        data = await self._request("POST", "/api/v1/retrieval", json_body=body)
        if isinstance(data, dict):
            chunks = data.get("chunks") or []
        elif isinstance(data, list):
            chunks = data
        else:
            chunks = []
        return [chunk for chunk in chunks if isinstance(chunk, dict)]
