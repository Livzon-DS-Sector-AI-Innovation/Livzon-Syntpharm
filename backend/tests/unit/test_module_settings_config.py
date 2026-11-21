"""模块运行时配置的校验、掩码与批量更新单元测试。

覆盖三块纯逻辑：
- ``_normalize_value``：bool / int / json 的通过与失败文案；
- ``_mask_secret`` / ``_to_response``：密钥类只回掩码、非密钥原样返回；
- ``put_batch``：成功与失败分组、密钥空值拒绝、不存在项报错。

批量接口用假会话直接调用，不连真实数据库；``ModuleSetting`` 只作为普通
对象使用，不 flush 到任何引擎。
"""

import uuid
from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.core.config_api import (
    ModuleSettingBatchItem,
    ModuleSettingBatchUpdate,
    _mask_secret,
    _normalize_value,
    _to_response,
    put_batch,
)
from app.core.config_model import ModuleSetting
from app.core.exceptions import BadRequestException


class _FakeScalars:
    def __init__(self, items: list[ModuleSetting]) -> None:
        self._items = items

    def all(self) -> list[ModuleSetting]:
        return self._items


class _FakeResult:
    def __init__(self, items: list[ModuleSetting]) -> None:
        self._items = items

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._items)


class _FakeSession:
    """只实现 ``execute`` / ``commit`` 的会话替身。"""

    def __init__(self, items: list[ModuleSetting]) -> None:
        self._items = items
        self.committed = False

    async def execute(self, _stmt: Any) -> _FakeResult:
        return _FakeResult(self._items)

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, _obj: Any) -> None:
        return None


def _setting(
    key: str,
    value: str,
    value_type: str = "string",
    *,
    is_secret: bool = False,
    label: str | None = None,
    updated_by: uuid.UUID | None = None,
    module: str = "safety",
) -> ModuleSetting:
    return ModuleSetting(
        id=uuid.uuid4(),
        module=module,
        key=key,
        value=value,
        value_type=value_type,
        is_secret=is_secret,
        label=label,
        updated_by=updated_by,
    )


# ── _normalize_value ──────────────────────────────────────────


@pytest.mark.parametrize("raw", ["true", "TRUE", "1", "yes", "on"])
def test_normalize_bool_accepts_true_variants(raw: str) -> None:
    assert _normalize_value("bool", raw) == "true"


@pytest.mark.parametrize("raw", ["false", "0", "no", "off"])
def test_normalize_bool_accepts_false_variants(raw: str) -> None:
    assert _normalize_value("bool", raw) == "false"


def test_normalize_bool_rejects_garbage() -> None:
    with pytest.raises(BadRequestException) as exc:
        _normalize_value("bool", "abc")
    assert "布尔型配置" in exc.value.message


def test_normalize_int_returns_canonical_form() -> None:
    assert _normalize_value("int", " 017 ") == "17"


def test_normalize_int_rejects_non_numeric() -> None:
    with pytest.raises(BadRequestException) as exc:
        _normalize_value("int", "1.5")
    assert "整数" in exc.value.message


def test_normalize_json_accepts_valid_document() -> None:
    payload = '{"enabled": true, "chat_id": "oc_1"}'
    assert _normalize_value("json", payload) == payload


def test_normalize_json_rejects_invalid_document() -> None:
    with pytest.raises(BadRequestException) as exc:
        _normalize_value("json", '{"enabled": tru}')
    message = exc.value.message
    assert "JSON 格式不正确" in message
    assert "第 1 行" in message


def test_normalize_string_passes_through() -> None:
    assert _normalize_value("string", "deepseek-v4-flash") == "deepseek-v4-flash"


# ── 掩码与响应 ────────────────────────────────────────────────


def test_mask_secret_keeps_head_and_tail_for_long_value() -> None:
    assert _mask_secret("abcdef1234567890") == "abcdef****7890"


def test_mask_secret_hides_short_value() -> None:
    assert _mask_secret("short") == "******"


def test_to_response_masks_secret_value() -> None:
    setting = _setting("SAFETY_FEISHU_BITABLE_APP_TOKEN", "abcdef1234567890", is_secret=True)
    response = _to_response(setting, "张三")
    assert response.value == ""
    assert response.value_masked == "abcdef****7890"
    assert response.has_value is True
    assert response.is_secret is True
    assert response.updated_by_name == "张三"


def test_to_response_keeps_plain_value() -> None:
    setting = _setting("SAFETY_AI_TEXT_MODEL", "deepseek-v4-flash")
    response = _to_response(setting)
    assert response.value == "deepseek-v4-flash"
    assert response.value_masked is None
    assert response.manually_adjusted is False


def test_to_response_marks_manually_adjusted() -> None:
    setting = _setting("SAFETY_AI_TEXT_MODEL", "gpt-4o", updated_by=uuid.uuid4())
    assert _to_response(setting).manually_adjusted is True


# ── 批量更新 ──────────────────────────────────────────────────


def _user() -> Any:
    return SimpleNamespace(id=uuid.uuid4(), name="张三")


async def test_put_batch_splits_success_and_failure() -> None:
    enabled = _setting("ENERGY_AUTO_COLLECT_ENABLED", "false", "bool")
    secret = _setting("SAFETY_FEISHU_BITABLE_APP_TOKEN", "old-token", is_secret=True)
    session = _FakeSession([enabled, secret])

    response = await put_batch(
        ModuleSettingBatchUpdate(
            items=[
                ModuleSettingBatchItem(module="safety", key="ENERGY_AUTO_COLLECT_ENABLED", value="启用"),
                ModuleSettingBatchItem(module="safety", key="SAFETY_FEISHU_BITABLE_APP_TOKEN", value=""),
                ModuleSettingBatchItem(module="safety", key="MISSING_KEY", value="true"),
            ]
        ),
        current_user=_user(),
        ctx=cast(Any, None),
        db=cast(Any, session),
    )

    result = response.data
    assert result.succeeded == ["safety:ENERGY_AUTO_COLLECT_ENABLED"]
    assert enabled.value == "true"
    reasons = {item.key: item.reason for item in result.failed}
    assert "密钥类配置不能为空" in reasons["SAFETY_FEISHU_BITABLE_APP_TOKEN"]
    assert reasons["MISSING_KEY"] == "配置项不存在"
    assert session.committed is True


async def test_put_batch_reports_validation_error_per_item() -> None:
    hour = _setting("ENERGY_BITABLE_SYNC_HOUR", "17", "int")
    session = _FakeSession([hour])

    response = await put_batch(
        ModuleSettingBatchUpdate(
            items=[ModuleSettingBatchItem(module="safety", key="ENERGY_BITABLE_SYNC_HOUR", value="晚上")]
        ),
        current_user=_user(),
        ctx=cast(Any, None),
        db=cast(Any, session),
    )

    assert response.data.succeeded == []
    assert "整数" in response.data.failed[0].reason
    assert hour.value == "17"
    assert session.committed is False
