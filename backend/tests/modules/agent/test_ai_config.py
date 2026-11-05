"""AI 配置单测：三层提示词拼接、四级模型回落、个人 Key 的可见性与掩码。

需要数据库（个人 Key 的可见性靠 SQL 过滤，mock 掉就测不到漏权）。
模型配置读取与 HTTP 探测全部替换，不连真实服务。
"""

import uuid
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.llm.config import LLMConfigModel, parse_available_models
from app.core.llm.encryption import encrypt_api_key
from app.core.llm.exceptions import LLMConfigError
from app.modules.agent import ai_config
from app.modules.agent.ai_config import ResolvedGuide, compose_guide_block, masked_key
from app.modules.agent.models import PptVideoProject
from app.platform.identity.models import User

OWNER = uuid.uuid4()
OTHER = uuid.uuid4()
HAS_ENCRYPTION_KEY = bool(get_settings().ENCRYPTION_KEY)


@pytest.fixture
async def users(db_session: AsyncSession):
    """llm_configs.created_by/updated_by 有外键，个人 Key 用例必须用真实用户。"""
    owner = User(name="测试用户甲", employee_no=f"T{uuid.uuid4().hex[:8]}")
    other = User(name="测试用户乙", employee_no=f"T{uuid.uuid4().hex[:8]}")
    db_session.add_all([owner, other])
    await db_session.flush()
    return owner, other


def _stored(plain: str) -> str:
    """有 ENCRYPTION_KEY 时按密文存，没有时按历史明文存——两种环境都能跑。"""
    return encrypt_api_key(plain) if HAS_ENCRYPTION_KEY else plain


# ── 提示词拼接 ────────────────────────────────────────────────────────────


def test_compose_guide_block_orders_by_priority() -> None:
    block = compose_guide_block(
        ResolvedGuide(global_guide="全局书面语", project_guide="项目面向审评专家"),
        "本次更口语一点",
    )

    assert block.index("全局书面语") < block.index("项目面向审评专家") < block.index("本次更口语一点")
    assert "优先级" in block


def test_compose_guide_block_empty_when_nothing_set() -> None:
    assert compose_guide_block(ResolvedGuide(), None) == ""
    assert compose_guide_block(ResolvedGuide(), "   ") == ""


def test_compose_guide_block_drops_duplicate_project_guide() -> None:
    block = compose_guide_block(ResolvedGuide(global_guide="同一段规则", project_guide="同一段规则"), None)
    assert block.count("同一段规则") == 1
    assert "覆盖全局" not in block


def test_compose_guide_block_truncates_each_layer() -> None:
    block = compose_guide_block(ResolvedGuide(global_guide="甲" * 5000), None, max_chars=20)
    assert len(block) < 300
    assert block.count("甲") == 20


def test_resolved_guide_effective_priority() -> None:
    assert ResolvedGuide(global_guide="全局", project_guide="项目").effective == "项目"
    assert ResolvedGuide(global_guide="全局", project_guide="  ").effective == "全局"
    assert ResolvedGuide().effective == ""


# ── 掩码 ──────────────────────────────────────────────────────────────────


def _config_row(model_name: str, **overrides) -> LLMConfigModel:
    return LLMConfigModel(
        id=overrides.pop("id", uuid.uuid4()),
        config_name=overrides.pop("config_name", model_name),
        config_type=overrides.pop("config_type", "text"),
        api_base_url="http://unit.test/v1",
        encrypted_api_key=overrides.pop("encrypted_api_key", _stored("sk-1234567890abcdef")),
        model_name=model_name,
        is_active=overrides.pop("is_active", False),
        visibility=overrides.pop("visibility", "system"),
        owner_user_id=overrides.pop("owner_user_id", None),
        **overrides,
    )


def test_masked_key_hides_middle() -> None:
    masked = masked_key(_config_row("qwen", encrypted_api_key=_stored("sk-1234567890abcdef")))
    assert masked == "sk-1******cdef"


def test_masked_key_stars_short_and_empty() -> None:
    assert masked_key(_config_row("qwen", encrypted_api_key=_stored("abc"))) == "***"
    assert masked_key(_config_row("qwen", encrypted_api_key="")) == "****"


@pytest.mark.skipif(not HAS_ENCRYPTION_KEY, reason="未配置 ENCRYPTION_KEY 时读取按明文兼容")
def test_masked_key_never_leaks_ciphertext() -> None:
    # 换过密钥后解不开，也不能把密文回显给前端
    assert masked_key(_config_row("qwen", encrypted_api_key="not-a-fernet-token")) == "****"


# ── 模型回落 ──────────────────────────────────────────────────────────────


async def _make_project(session: AsyncSession, llm_config_id: uuid.UUID | None = None) -> PptVideoProject:
    project = PptVideoProject(
        id=uuid.uuid4(),
        name=f"解析-{uuid.uuid4().hex[:6]}",
        source_object_key=f"agent/ppt-video/source/{uuid.uuid4().hex}.pptx",
        source_filename="deck.pptx",
        source_sha256=uuid.uuid4().hex * 2,
        slide_count=1,
        llm_config_id=llm_config_id,
    )
    session.add(project)
    await session.flush()
    return project


def _patch_lookup(monkeypatch: pytest.MonkeyPatch, rows: dict[str, LLMConfigModel], active=None):
    async def fake_by_id(config_id, config_type="text", owner_user_id=None):
        row = rows.get(str(config_id))
        return row if row and row.config_type == config_type else None

    async def fake_active(config_type="text"):
        return active

    monkeypatch.setattr(ai_config, "get_config_by_id", fake_by_id)
    monkeypatch.setattr(ai_config, "get_active_config", fake_active)


async def test_resolve_prefers_project_config(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    project_cfg = _config_row("project-model")
    _patch_lookup(monkeypatch, {str(project_cfg.id): project_cfg}, active=_config_row("active-model"))
    project = await _make_project(db_session, llm_config_id=project_cfg.id)

    resolved = await ai_config.resolve(db_session, project, OWNER)

    assert (resolved.model_name, resolved.source) == ("project-model", "project")
    assert resolved.config_id == project_cfg.id


async def test_resolve_falls_back_to_global_setting(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    global_cfg = _config_row("global-model")
    _patch_lookup(monkeypatch, {str(global_cfg.id): global_cfg}, active=_config_row("active-model"))
    await ai_config.save_setting(db_session, ai_config.SETTING_GLOBAL_CONFIG_ID, str(global_cfg.id))
    project = await _make_project(db_session, llm_config_id=uuid.uuid4())

    resolved = await ai_config.resolve(db_session, project, OWNER)

    # 项目配置已删除 → 静默降级到全局默认，不让项目卡死
    assert (resolved.model_name, resolved.source) == ("global-model", "global")


async def test_resolve_falls_back_to_active_then_env(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    active_cfg = _config_row("active-model")
    _patch_lookup(monkeypatch, {}, active=active_cfg)
    project = await _make_project(db_session)

    resolved = await ai_config.resolve(db_session, project, OWNER)
    assert (resolved.model_name, resolved.source) == ("active-model", "active")

    _patch_lookup(monkeypatch, {}, active=None)
    monkeypatch.setattr(ai_config, "get_env_config", lambda: _config_row("env-model"))

    resolved = await ai_config.resolve(db_session, project, OWNER)
    assert (resolved.model_name, resolved.source) == ("env-model", "env")
    assert resolved.config_id is None


async def test_resolve_raises_when_nothing_available(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_lookup(monkeypatch, {}, active=None)

    def boom():
        raise LLMConfigError("no env")

    monkeypatch.setattr(ai_config, "get_env_config", boom)

    with pytest.raises(LLMConfigError):
        await ai_config.resolve(db_session, await _make_project(db_session), OWNER)


async def test_resolve_passes_owner_for_personal_key(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    """个人 Key 必须带 owner 去查，否则后端拿不到解密后的明文。"""
    seen: dict[str, Any] = {}
    personal = _config_row("personal-model", visibility="personal", owner_user_id=OWNER)

    async def fake_by_id(config_id, config_type="text", owner_user_id=None):
        seen["owner"] = owner_user_id
        return personal

    monkeypatch.setattr(ai_config, "get_config_by_id", fake_by_id)
    monkeypatch.setattr(ai_config, "get_active_config", lambda *a, **k: None)
    project = await _make_project(db_session, llm_config_id=personal.id)

    await ai_config.resolve(db_session, project, OWNER)
    assert seen["owner"] == str(OWNER)


# ── 个人 Key CRUD 与可见性 ────────────────────────────────────────────────


async def _add_config(
    session: AsyncSession,
    name: str,
    *,
    owner_id: uuid.UUID | None = None,
    **overrides,
) -> LLMConfigModel:
    config = _config_row(
        overrides.pop("model_name", name),
        config_name=name,
        visibility=overrides.pop("visibility", "personal"),
        owner_user_id=overrides.pop("owner_user_id", owner_id),
        config_type=overrides.pop("config_type", "text"),
        created_by=owner_id,
        updated_by=owner_id,
        **overrides,
    )
    session.add(config)
    await session.flush()
    return config


async def test_visible_configs_hides_other_peoples_keys(db_session: AsyncSession, users) -> None:
    owner, other = users
    system = await _add_config(db_session, "sys", visibility="system", owner_user_id=None)
    mine = await _add_config(db_session, "mine", owner_id=owner.id)
    await _add_config(db_session, "theirs", owner_id=other.id)
    await _add_config(db_session, "vision", owner_id=owner.id, config_type="vision")

    visible = await ai_config.visible_configs(db_session, owner.id)
    assert {item.id for item in visible} == {system.id, mine.id}


async def test_visible_configs_anonymous_sees_only_system(db_session: AsyncSession, users) -> None:
    owner, _ = users
    system = await _add_config(db_session, "sys-anon", visibility="system", owner_user_id=None)
    await _add_config(db_session, "mine-anon", owner_id=owner.id)

    visible = await ai_config.visible_configs(db_session, None)
    assert [item.id for item in visible] == [system.id]


async def test_get_personal_filters_by_owner_and_visibility(db_session: AsyncSession, users) -> None:
    owner, other = users
    system = await _add_config(db_session, "sys2", visibility="system", owner_user_id=None)
    foreign = await _add_config(db_session, "foreign", owner_id=other.id)
    mine = await _add_config(db_session, "mine2", owner_id=owner.id)

    assert await ai_config.get_personal(db_session, str(system.id), owner.id) is None
    assert await ai_config.get_personal(db_session, str(foreign.id), owner.id) is None
    assert await ai_config.get_personal(db_session, "not-a-uuid", owner.id) is None
    found = await ai_config.get_personal(db_session, str(mine.id), owner.id)
    assert found is not None and found.id == mine.id


async def test_create_personal_forces_private_and_encrypts(db_session: AsyncSession, users) -> None:
    owner, _ = users
    created = await ai_config.create_personal(
        db_session,
        owner.id,
        SimpleNamespace(
            config_name=" 我的 Key ",
            api_base_url="https://example.test/v1",
            api_key="sk-abcdefghijklmnop",
            model_name="qwen-plus",
            temperature=0.2,
            timeout_seconds=60,
            notes="个人",
        ),
    )

    assert created.visibility == "personal"
    assert created.owner_user_id == owner.id
    # 个人 Key 不参与「平台启用」，也不该被当成全局默认
    assert created.is_active is False
    assert created.config_name == "我的 Key"
    assert created.encrypted_api_key != "sk-abcdefghijklmnop"


async def test_update_personal_keeps_key_when_blank(db_session: AsyncSession, users) -> None:
    owner, _ = users
    config = await _add_config(db_session, "keep", owner_id=owner.id)
    before = config.encrypted_api_key

    updated = await ai_config.update_personal(
        db_session,
        config,
        SimpleNamespace(
            config_name="改名",
            api_base_url=None,
            api_key=None,
            model_name=None,
            temperature=None,
            timeout_seconds=None,
            notes=None,
        ),
        owner.id,
    )

    assert updated.config_name == "改名"
    assert updated.encrypted_api_key == before


async def test_update_personal_reencrypts_new_key(db_session: AsyncSession, users) -> None:
    owner, _ = users
    config = await _add_config(db_session, "rotate", owner_id=owner.id)
    before = config.encrypted_api_key

    updated = await ai_config.update_personal(
        db_session,
        config,
        SimpleNamespace(
            config_name=None,
            api_base_url=None,
            api_key="sk-new-key-0987654321",
            model_name=None,
            temperature=None,
            timeout_seconds=None,
            notes=None,
        ),
        owner.id,
    )

    assert updated.encrypted_api_key != before
    assert updated.encrypted_api_key != "sk-new-key-0987654321"


# ── 一 Key 多模型：清单归一化与选择 ─────────────────────────────────────


def test_normalize_models_dedupes_and_keeps_default_first() -> None:
    models = ai_config.normalize_models([" qwen-max ", "qwen-plus", "qwen-max", ""], default="qwen-plus")
    # 默认模型（原 model_name）即使没勾选也必须留在清单里；已在清单内则保持勾选顺序
    assert models == ["qwen-max", "qwen-plus"]


def test_normalize_models_caps_count_and_length() -> None:
    models = ai_config.normalize_models([f"m{i}" for i in range(80)])
    assert len(models) == ai_config.MAX_AVAILABLE_MODELS
    long_name = ai_config.normalize_models(["x" * 300])
    assert len(long_name[0]) == ai_config.MAX_MODEL_NAME_CHARS


def test_pick_model_falls_back_when_not_in_list() -> None:
    assert ai_config.pick_model("m2", ["m1", "m2"], "m1") == "m2"
    # 脏数据（模型名不在清单）不能让讲稿任务直接失败
    assert ai_config.pick_model("gone", ["m1"], "m1") == "m1"
    assert ai_config.pick_model(None, ["m1"], "m1") == "m1"


def test_parse_available_models_handles_legacy_shapes() -> None:
    assert parse_available_models(None, "only") == ["only"]
    assert parse_available_models('["a", "b"]', "a") == ["a", "b"]
    assert parse_available_models("a,b", "b") == ["a", "b"]
    assert parse_available_models("   ", "a") == ["a"]


async def test_resolve_uses_project_selected_model(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config_row("m1", available_models=["m1", "m2"])
    _patch_lookup(monkeypatch, {str(config.id): config})
    project = await _make_project(db_session, llm_config_id=config.id)
    project.llm_model_name = "m2"

    resolved = await ai_config.resolve(db_session, project, OWNER)

    assert (resolved.model_name, resolved.source) == ("m2", "project")


async def test_resolve_ignores_project_model_outside_list(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config_row("m1", available_models=["m1", "m2"])
    _patch_lookup(monkeypatch, {str(config.id): config})
    project = await _make_project(db_session, llm_config_id=config.id)
    project.llm_model_name = "stale-model"

    resolved = await ai_config.resolve(db_session, project, OWNER)

    assert resolved.model_name == "m1"


async def test_create_personal_saves_all_selected_models(db_session: AsyncSession, users) -> None:
    owner, _ = users
    created = await ai_config.create_personal(
        db_session,
        owner.id,
        SimpleNamespace(
            config_name="多模型 Key",
            api_base_url="https://example.test/v1",
            api_key="sk-abcdefghijklmnop",
            available_models=["qwen-max", "qwen-plus", "qwen-max"],
            model_name=None,
            temperature=0.2,
            timeout_seconds=60,
            notes=None,
        ),
    )

    assert created.available_models == ["qwen-max", "qwen-plus"]
    assert created.model_name == "qwen-max"


async def test_update_personal_replaces_model_list(db_session: AsyncSession, users) -> None:
    owner, _ = users
    config = await _add_config(db_session, "replace", owner_id=owner.id, model_name="old")

    updated = await ai_config.update_personal(
        db_session,
        config,
        SimpleNamespace(
            config_name=None,
            api_base_url=None,
            api_key=None,
            available_models=["new-1", "new-2"],
            model_name=None,
            temperature=None,
            timeout_seconds=None,
            notes=None,
        ),
        owner.id,
    )

    assert updated.available_models == ["new-1", "new-2"]
    assert updated.model_name == "new-1"


async def test_update_personal_legacy_model_name_keeps_other_models(
    db_session: AsyncSession, users
) -> None:
    owner, _ = users
    config = await _add_config(
        db_session, "legacy", owner_id=owner.id, model_name="old", available_models=["old", "keep"]
    )

    updated = await ai_config.update_personal(
        db_session,
        config,
        SimpleNamespace(
            config_name=None,
            api_base_url=None,
            api_key=None,
            model_name="fresh",
            temperature=None,
            timeout_seconds=None,
            notes=None,
        ),
        owner.id,
    )

    assert updated.model_name == "fresh"
    assert set(updated.available_models) == {"fresh", "old", "keep"}


async def test_delete_personal_clears_global_model(db_session: AsyncSession, users) -> None:
    owner, _ = users
    config = await _add_config(db_session, "to-delete", owner_id=owner.id)
    await ai_config.save_setting(db_session, ai_config.SETTING_GLOBAL_CONFIG_ID, str(config.id))
    await ai_config.save_setting(db_session, ai_config.SETTING_GLOBAL_MODEL, config.model_name)

    await ai_config.delete_personal(db_session, config, owner.id)

    global_id, global_model, _ = await ai_config.read_global_settings(db_session)
    assert global_id == ""
    assert global_model == ""


# ── 模型探测（/models 代理） ─────────────────────────────────────────────


class _ModelsResponse:
    def __init__(self, status_code: int, payload: Any = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text or str(payload)

    def json(self) -> Any:
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def _patch_discover_http(monkeypatch: pytest.MonkeyPatch, handler) -> None:
    class _FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "_FakeClient":
            return self

        async def __aexit__(self, *args: Any) -> bool:
            return False

        async def get(self, url: str, headers: dict[str, str] | None = None) -> _FakeResponse:
            return await handler(url, headers)

    monkeypatch.setattr(ai_config.httpx, "AsyncClient", _FakeClient)


async def test_discover_models_reads_openai_style_list(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(url: str, headers: dict[str, str] | None):
        assert url == "https://example.test/v1/models"
        assert headers and headers["Authorization"].startswith("Bearer ")
        return _ModelsResponse(200, {"data": [{"id": "qwen-max"}, {"id": "qwen-plus"}, {"id": "qwen-max"}]})

    _patch_discover_http(monkeypatch, handler)

    ok, message, models = await ai_config.discover_models("https://example.test/v1/", "sk-test")

    assert ok is True
    assert models == ["qwen-max", "qwen-plus"]
    assert "2" in message


async def test_discover_models_strips_chat_completions_suffix(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, str] = {}

    async def handler(url: str, headers: dict[str, str] | None):
        seen["url"] = url
        return _ModelsResponse(200, {"models": [{"name": "a"}]})

    _patch_discover_http(monkeypatch, handler)

    ok, _, models = await ai_config.discover_models("https://example.test/v1/chat/completions", "sk-test")

    assert ok is True
    assert seen["url"] == "https://example.test/v1/models"
    assert models == ["a"]


async def test_discover_models_reports_auth_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(url: str, headers: dict[str, str] | None):
        return _ModelsResponse(401, {})

    _patch_discover_http(monkeypatch, handler)

    ok, message, models = await ai_config.discover_models("https://example.test/v1", "sk-bad")

    assert (ok, models) == (False, [])
    assert "鉴权失败" in message


async def test_discover_models_reports_unsupported_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(url: str, headers: dict[str, str] | None):
        return _ModelsResponse(404, None, "not found")

    _patch_discover_http(monkeypatch, handler)

    ok, message, _ = await ai_config.discover_models("https://example.test/v1", "sk-test")

    assert ok is False
    assert "手动填写" in message


async def test_discover_models_reports_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(url: str, headers: dict[str, str] | None):
        raise httpx.ConnectError("boom")

    _patch_discover_http(monkeypatch, handler)

    ok, message, models = await ai_config.discover_models("https://example.test/v1", "sk-test")

    assert (ok, models) == (False, [])
    assert "网络错误" in message


async def test_discover_models_requires_base_url() -> None:
    ok, message, models = await ai_config.discover_models("  ", "sk-test")
    assert (ok, models) == (False, [])
    assert "接口地址" in message


async def test_delete_personal_clears_global_default(db_session: AsyncSession, users) -> None:
    owner, _ = users
    config = await _add_config(db_session, "todelete", owner_id=owner.id)
    await ai_config.save_setting(db_session, ai_config.SETTING_GLOBAL_CONFIG_ID, str(config.id))

    await ai_config.delete_personal(db_session, config, owner.id)

    assert config.is_deleted is True
    assert config.is_active is False
    # 全局默认不能指向一条已删的 Key
    assert await ai_config._read_setting(db_session, ai_config.SETTING_GLOBAL_CONFIG_ID) == ""


# ── 连通性探测 ────────────────────────────────────────────────────────────


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


class _FakeClient:
    response: _FakeResponse = _FakeResponse(200)
    error: Exception | None = None

    def __init__(self, **_kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def post(self, *_args, **_kwargs):
        if self.error:
            raise self.error
        return self.response


def _patch_http(monkeypatch: pytest.MonkeyPatch, *, status: int = 200, text: str = "", error=None) -> None:
    _FakeClient.response = _FakeResponse(status, text)
    _FakeClient.error = error
    monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)


async def test_connection_reports_auth_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_http(monkeypatch, status=401)
    ok, message = await ai_config.test_connection("https://example.test/v1", "qwen-plus", "sk-x")
    assert ok is False
    assert "鉴权失败" in message


async def test_connection_reports_missing_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_http(monkeypatch, status=404)
    ok, message = await ai_config.test_connection("https://example.test/v1", "qwen-plus", "sk-x")
    assert ok is False
    assert "Base URL" in message


async def test_connection_reports_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_http(monkeypatch, status=200, text='{"choices":[]}')
    ok, message = await ai_config.test_connection("https://example.test/v1", "qwen-plus", "sk-x")
    assert ok is True
    assert "成功" in message


async def test_connection_maps_timeout_and_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_http(monkeypatch, error=httpx.TimeoutException("slow"))
    ok, message = await ai_config.test_connection("https://example.test/v1", "qwen-plus", "sk-x")
    assert ok is False and "超时" in message

    _patch_http(monkeypatch, error=httpx.ConnectError("refused"))
    ok, message = await ai_config.test_connection("https://example.test/v1", "qwen-plus", "sk-x")
    assert ok is False and "网络错误" in message


async def test_connection_appends_chat_completions(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    class _Recorder(_FakeClient):
        async def post(self, url, **_kwargs):
            seen["url"] = url
            return _FakeResponse(200)

    monkeypatch.setattr(httpx, "AsyncClient", _Recorder)

    await ai_config.test_connection("https://example.test/v1/", "qwen-plus", "sk-x")
    assert seen["url"] == "https://example.test/v1/chat/completions"
