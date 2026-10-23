"""HR 飞书审批回调鉴权单测。

回调由飞书服务器发起、没有用户 JWT，因此鉴权完全依赖
「签名（Encrypt Key）+ verification token」，任何一环缺失都必须拒绝（fail-closed）。
"""

import hashlib
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.modules.hr import api as hr_api

PATH = "/api/v1/hr/webhook/feishu-approval"


def _request(body: bytes, headers: dict[str, str] | None = None) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": PATH,
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "query_string": b"",
    }
    sent = False

    async def receive():  # type: ignore[no-untyped-def]
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(scope, receive)


def _patch_settings(monkeypatch: pytest.MonkeyPatch, *, encrypt_key: str = "", token: str = "") -> None:
    monkeypatch.setattr(
        hr_api,
        "get_settings",
        lambda: SimpleNamespace(
            HR_FEISHU_APPROVAL_ENCRYPT_KEY=encrypt_key,
            HR_FEISHU_APPROVAL_VERIFICATION_TOKEN=token,
        ),
    )


def _signed_headers(
    encrypt_key: str,
    body: bytes,
    *,
    timestamp: str = "1700000000",
    nonce: str = "n1",
) -> dict[str, str]:
    signature = hashlib.sha256(f"{timestamp}{nonce}{encrypt_key}".encode() + body).hexdigest()
    return {
        "X-Lark-Request-Timestamp": timestamp,
        "X-Lark-Request-Nonce": nonce,
        "X-Lark-Signature": signature,
    }


async def test_rejects_when_nothing_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        await hr_api._verify_feishu_approval_callback(_request(b"{}"), {})
    assert exc.value.status_code == 503


async def test_rejects_missing_signature_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch, encrypt_key="k")
    with pytest.raises(HTTPException) as exc:
        await hr_api._verify_feishu_approval_callback(_request(b"{}"), {})
    assert exc.value.status_code == 401


async def test_accepts_valid_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    body = b'{"employee_number": "E0001"}'
    _patch_settings(monkeypatch, encrypt_key="k")
    await hr_api._verify_feishu_approval_callback(
        _request(body, _signed_headers("k", body)),
        {"employee_number": "E0001"},
    )


async def test_rejects_bad_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    body = b'{"employee_number": "E0001"}'
    headers = _signed_headers("k", body)
    headers["X-Lark-Signature"] = "deadbeef"
    _patch_settings(monkeypatch, encrypt_key="k")
    with pytest.raises(HTTPException) as exc:
        await hr_api._verify_feishu_approval_callback(_request(body, headers), {})
    assert exc.value.status_code == 401


async def test_rejects_bad_verification_token(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch, token="expected")
    with pytest.raises(HTTPException) as exc:
        await hr_api._verify_feishu_approval_callback(_request(b"{}"), {"token": "other"})
    assert exc.value.status_code == 401


async def test_accepts_valid_verification_token(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch, token="expected")
    await hr_api._verify_feishu_approval_callback(_request(b"{}"), {"header": {"token": "expected"}})
