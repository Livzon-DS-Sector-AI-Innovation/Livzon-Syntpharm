"""v4 导入接口响应契约（防止 `-> ApiResponse` 再次吃掉前端类型）。

`ApiResponse.data` 是 `Any`，一旦端点靠它推断响应，OpenAPI 就退化成裸 object，
`pnpm generate:api` 生成的 `schema.ts` 里对应模型会整块消失——
`ImportV4BatchResponse` / `ImportV4PreviewResponse` / `ImportErrorItem` 曾这样丢过一次。
本文件同时钉住契约声明与实际序列化：envelope 必须能序列化 `build_response()` 的返回，
否则 FastAPI 会在运行时抛校验错误。
"""

from typing import Any

_PREVIEW = "/api/v1/equipment/equipments/import-v4/preview"
_BATCH = "/api/v1/equipment/equipments/import-v4/batch"


def _response_ref(schema: dict[str, Any], path: str) -> str:
    # 应用层把默认响应 media type 设成了 ``application/json; charset=utf-8``
    # （避免中文被按 ISO-8859-1 解析成乱码），这里按前缀匹配，两种写法都接受。
    content = schema["paths"][path]["post"]["responses"]["200"]["content"]
    key = next(k for k in content if k.split(";")[0].strip() == "application/json")
    return str(content[key]["schema"]["$ref"])


def test_openapi_declares_concrete_import_v4_envelopes():
    from app.main import app

    schema = app.openapi()  # type: ignore[attr-defined]
    for path, envelope, payload in [
        (_PREVIEW, "ImportV4PreviewApiResponse", "ImportV4PreviewResponse"),
        (_BATCH, "ImportV4BatchApiResponse", "ImportV4BatchResponse"),
    ]:
        assert _response_ref(schema, path).endswith(envelope), f"{path} 未声明具体 envelope"
        props = schema["components"]["schemas"][envelope]["properties"]
        assert set(props) == {"code", "message", "data", "meta"}
        assert props["data"]["$ref"].endswith(payload), f"{envelope}.data 不是具体模型"

    error_item = schema["components"]["schemas"]["ImportV4BatchResponse"]["properties"]["errors"]
    assert error_item["items"]["$ref"].endswith("ImportErrorItem"), "errors 元素类型丢失"


async def test_preview_returns_envelope_shaped_body(auth_client):
    resp = await auth_client.post(_PREVIEW, json={"data": [{"资产编号": "9900001", "设备名称": "契约测试设备"}]})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["total"] == 1
    assert data["items"][0]["row_index"] == 0
    assert data["items"][0]["validation_status"] in ("pass", "error", "duplicate")
    assert data["headers"], "预览列定义不应为空"
