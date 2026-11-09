"""讲稿 AI 配置解析与个人 Key 管理。

对外只有五个入口：

- `resolve(session, project, user_id)`：算出「这次到底用哪个模型」以及来源
- `resolve_guide(session, project)`：算出「这次讲稿要遵守什么风格」
- `create/update/delete_personal(...)`：个人私有 Key 的增删改
- `test_connection(...)`：保存前一键自测连通性
- `discover_models(...)`：按接口地址远程拉取该 Key 可用的模型清单

隐藏的实现是四级模型回落：

    project.llm_config_id  →  全局默认（模块配置）  →  平台活跃配置  →  环境变量

任何一级不可用（已删除、类型不符、越权）都静默跳到下一级，最后一层都没有才报错。
这样「管理员换了平台配置」「用户删了自己的 Key」都不会让项目卡死。
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_model import ModuleSetting
from app.core.llm.config import (
    LLMConfigData,
    LLMConfigModel,
    get_active_config,
    get_config_by_id,
    get_env_config,
    parse_available_models,
)
from app.core.llm.encryption import encrypt_api_key
from app.core.llm.exceptions import LLMConfigError
from app.modules.agent.config import SCRIPT_GUIDE_MAX_CHARS
from app.modules.agent.models import PptVideoProject

logger = logging.getLogger(__name__)

MODULE = "agent"
SETTING_GLOBAL_CONFIG_ID = "AGENT_PPT_VIDEO_SCRIPT_AI_CONFIG_ID"
#: 全局默认模型名；与 SETTING_GLOBAL_CONFIG_ID 配对，空表示用配置自带的 model_name
SETTING_GLOBAL_MODEL = "AGENT_PPT_VIDEO_SCRIPT_AI_MODEL"
SETTING_GLOBAL_GUIDE = "AGENT_PPT_VIDEO_SCRIPT_AI_GUIDE"

#: 单个 Key 最多勾选的模型数，防止网关返回几千条把界面撑爆
MAX_AVAILABLE_MODELS = 50
MAX_MODEL_NAME_CHARS = 128

__all__ = [
    "MAX_AVAILABLE_MODELS",
    "MAX_MODEL_NAME_CHARS",
    "MODULE",
    "SETTING_GLOBAL_CONFIG_ID",
    "SETTING_GLOBAL_GUIDE",
    "SETTING_GLOBAL_MODEL",
    "ResolvedGuide",
    "ResolvedModel",
    "compose_guide_block",
    "create_personal",
    "delete_personal",
    "discover_models",
    "get_personal",
    "masked_key",
    "normalize_models",
    "read_global_settings",
    "resolve",
    "resolve_guide",
    "save_setting",
    "test_connection",
    "update_personal",
    "visible_configs",
]

ModelSource = Literal["project", "global", "active", "env"]


@dataclass(frozen=True)
class ResolvedModel:
    """一次讲稿调用实际使用的模型。config_id 为空表示走环境变量兜底。"""

    config_id: str | None
    model_name: str
    provider: str
    source: ModelSource

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_id": self.config_id,
            "model_name": self.model_name,
            "provider": self.provider,
            "source": self.source,
        }


@dataclass(frozen=True)
class ResolvedGuide:
    """三层风格指南的解析结果，单次指令由调用方单独拼接。"""

    global_guide: str = ""
    project_guide: str = ""

    @property
    def effective(self) -> str:
        """项目级非空时覆盖全局，否则继承全局。"""
        return self.project_guide.strip() or self.global_guide.strip()


def normalize_models(models: Iterable[str] | None, default: str = "") -> list[str]:
    """把前端勾选的模型名归一化：去空、去重、限长、限数量。

    `model_name`（默认模型）必须留在清单里，旧数据只有它一个。
    """
    cleaned: list[str] = []
    for raw in models or ():
        name = str(raw or "").strip()[:MAX_MODEL_NAME_CHARS]
        if name and name not in cleaned:
            cleaned.append(name)
        if len(cleaned) >= MAX_AVAILABLE_MODELS:
            break

    fallback = (default or "").strip()[:MAX_MODEL_NAME_CHARS]
    if fallback and fallback not in cleaned:
        cleaned.insert(0, fallback)
    return cleaned[:MAX_AVAILABLE_MODELS]


def pick_model(selected: str | None, models: Iterable[str], default: str) -> str:
    """选中模型落在清单内才用，否则回落默认模型（脏数据不让调用失败）。"""
    choice = (selected or "").strip()
    if choice and choice in set(models):
        return choice
    return (default or "").strip()


async def _read_setting(session: AsyncSession, key: str) -> str:
    result = await session.execute(
        select(ModuleSetting).where(
            ModuleSetting.module == MODULE,
            ModuleSetting.key == key,
            ~ModuleSetting.is_deleted,
        )
    )
    row = result.scalar_one_or_none()
    return (row.value or "").strip() if row else ""


async def read_global_settings(session: AsyncSession) -> tuple[str, str, str]:
    """返回 (全局默认模型配置 id, 全局默认模型名, 全局提示词指南)。"""
    return (
        await _read_setting(session, SETTING_GLOBAL_CONFIG_ID),
        await _read_setting(session, SETTING_GLOBAL_MODEL),
        await _read_setting(session, SETTING_GLOBAL_GUIDE),
    )


async def save_setting(session: AsyncSession, key: str, value: str, description: str = "") -> None:
    """模块配置 upsert。走 ModuleSetting 而不是新增表，保持与平台配置页一致。"""
    result = await session.execute(
        select(ModuleSetting).where(
            ModuleSetting.module == MODULE,
            ModuleSetting.key == key,
            ~ModuleSetting.is_deleted,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.value = value
        if description:
            row.description = description
        return
    session.add(
        ModuleSetting(
            module=MODULE,
            key=key,
            value=value,
            value_type="string",
            description=description or None,
        )
    )


def _resolve_from_config(
    config: LLMConfigData,
    *,
    selected_model: str | None,
    source: ModelSource,
) -> ResolvedModel:
    return ResolvedModel(
        config_id=config.id,
        model_name=pick_model(selected_model, config.available_models, config.model_name),
        provider=config.api_base_url,
        source=source,
    )


async def resolve(session: AsyncSession, project: PptVideoProject, user_id: uuid.UUID | None) -> ResolvedModel:
    """四级回落，返回本次应使用的模型。"""
    owner = str(user_id) if user_id else None

    if project.llm_config_id:
        config = await get_config_by_id(str(project.llm_config_id), "text", owner)
        if config:
            return _resolve_from_config(
                config,
                selected_model=getattr(project, "llm_model_name", None),
                source="project",
            )
        logger.warning("项目级模型配置不可用，回落到全局: project=%s config=%s", project.id, project.llm_config_id)

    global_id, global_model, _global_guide = await read_global_settings(session)
    if global_id:
        config = await get_config_by_id(global_id, "text", owner)
        if config:
            return _resolve_from_config(config, selected_model=global_model, source="global")
        logger.warning("全局默认模型配置不可用，回落到平台活跃配置: config=%s", global_id)

    active = await get_active_config("text")
    if active:
        return _resolve_from_config(active, selected_model=None, source="active")

    try:
        env = get_env_config()
    except LLMConfigError as exc:
        raise LLMConfigError("未配置任何可用的文本模型，请先在「AI 配置」中选择或添加") from exc
    if env is None:
        raise LLMConfigError("未配置任何可用的文本模型，请先在「AI 配置」中选择或添加")

    return ResolvedModel(
        config_id=None,
        model_name=pick_model(None, env.available_models, env.model_name),
        provider=env.api_base_url,
        source="env",
    )


async def resolve_guide(session: AsyncSession, project: PptVideoProject) -> ResolvedGuide:
    """全局提示词指南 + 项目覆盖。项目级为空表示继承。"""
    _global_id, _global_model, global_guide = await read_global_settings(session)
    return ResolvedGuide(
        global_guide=global_guide,
        project_guide=(project.script_guide or "").strip(),
    )


def compose_guide_block(guide: ResolvedGuide, instruction: str | None, max_chars: int = SCRIPT_GUIDE_MAX_CHARS) -> str:
    """把三层规则拼成一段注入 user 消息的说明。

    优先级写死在文案里，模型才会稳定遵守；单次指令放最后，因为它在注意力末端。
    返回空串表示无额外要求。
    """
    parts: list[str] = []
    if guide.global_guide:
        parts.append(f"【全局讲稿规范】\n{guide.global_guide.strip()[:max_chars]}")
    if guide.project_guide and guide.project_guide != guide.global_guide:
        parts.append(f"【本项目讲稿规范（覆盖全局）】\n{guide.project_guide.strip()[:max_chars]}")
    if instruction and instruction.strip():
        parts.append(f"【本次额外指令（优先级最高，覆盖以上规范）】\n{instruction.strip()[:max_chars]}")
    if not parts:
        return ""
    return (
        "\n\n以上规范按「本次指令 > 本项目规范 > 全局规范」的优先级生效。"
        "规范只约束文风、篇幅与用词，不得违背必须输出 JSON 的格式要求。\n\n" + "\n\n".join(parts)
    )


async def visible_configs(session: AsyncSession, user_id: uuid.UUID | None) -> list[LLMConfigModel]:
    """当前用户可选的配置行：系统预置 + 本人私有。给前端下拉用。

    未登录时只返回系统预置，绝不返回任何人的个人 Key。
    """
    personal_owner = user_id if user_id else uuid.UUID(int=0)
    stmt = select(LLMConfigModel).where(
        LLMConfigModel.config_type == "text",
        ~LLMConfigModel.is_deleted,
        (LLMConfigModel.visibility == "system")
        | ((LLMConfigModel.visibility == "personal") & (LLMConfigModel.owner_user_id == personal_owner)),
    )
    result = await session.execute(stmt.order_by(LLMConfigModel.visibility, LLMConfigModel.created_at))
    return list(result.scalars().all())


def masked_key(config: LLMConfigModel) -> str:
    """只回显掩码，明文 Key 永不出后端。解密失败时退化为占位符。"""
    try:
        from app.core.llm.encryption import decrypt_api_key

        plain = decrypt_api_key(config.encrypted_api_key)
    except Exception:  # noqa: BLE001 - 掩码失败不能影响列表
        return "****"
    if not plain:
        return "****"
    if len(plain) <= 8:
        return "*" * len(plain)
    return f"{plain[:4]}{'*' * 6}{plain[-4:]}"


async def delete_personal(session: AsyncSession, config: LLMConfigModel, user_id: uuid.UUID) -> None:
    """软删除个人配置；同时从全局默认里摘掉，避免指向一条已删的 Key。"""
    config.is_deleted = True
    config.is_active = False
    config.updated_by = user_id
    if await _read_setting(session, SETTING_GLOBAL_CONFIG_ID) == str(config.id):
        await save_setting(session, SETTING_GLOBAL_CONFIG_ID, "", "全局默认讲稿模型配置 id")
        await save_setting(session, SETTING_GLOBAL_MODEL, "", "全局默认讲稿模型名")
    await session.flush()


async def get_personal(session: AsyncSession, config_id: str, user_id: uuid.UUID) -> LLMConfigModel | None:
    """取一条属于该用户的个人配置；系统配置不允许从这里改。"""
    try:
        parsed_id = uuid.UUID(str(config_id))
    except (TypeError, ValueError):
        return None
    result = await session.execute(
        select(LLMConfigModel).where(
            LLMConfigModel.id == parsed_id,
            LLMConfigModel.visibility == "personal",
            LLMConfigModel.owner_user_id == user_id,
            ~LLMConfigModel.is_deleted,
        )
    )
    return result.scalar_one_or_none()


async def create_personal(session: AsyncSession, user_id: uuid.UUID, data: Any) -> LLMConfigModel:
    """新增个人私有配置。强制 visibility=personal、is_active=False。

    前端提交勾选后的模型清单，`model_name` 取清单首项作为默认模型。
    """
    requested = [str(item).strip() for item in (getattr(data, "available_models", None) or []) if str(item).strip()]
    if not requested:
        # 兼容旧客户端：只传了单个 model_name
        legacy = (getattr(data, "model_name", "") or "").strip()
        requested = [legacy] if legacy else []
    models = normalize_models(requested)
    model_name = models[0] if models else (getattr(data, "model_name", "") or "").strip()

    config = LLMConfigModel(
        config_name=data.config_name.strip(),
        config_type="text",
        api_base_url=data.api_base_url.strip(),
        encrypted_api_key=encrypt_api_key(data.api_key.strip()),
        model_name=model_name,
        available_models=models,
        temperature=data.temperature,
        timeout_seconds=data.timeout_seconds,
        is_active=False,
        notes=data.notes,
        visibility="personal",
        owner_user_id=user_id,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(config)
    await session.flush()
    return config


async def update_personal(
    session: AsyncSession, config: LLMConfigModel, data: Any, user_id: uuid.UUID
) -> LLMConfigModel:
    """更新个人配置。api_key 为空表示不修改，避免前端回显掩码时把 Key 抹掉。"""
    if data.config_name is not None:
        config.config_name = data.config_name.strip()
    if data.api_base_url is not None:
        config.api_base_url = data.api_base_url.strip()

    available = getattr(data, "available_models", None)
    if available is not None:
        models = normalize_models(available)
        if models:
            config.available_models = models
            config.model_name = models[0]
    elif data.model_name is not None:
        # 旧客户端只传单个模型名：并入现有清单并设为默认，不丢其它已勾选模型
        model = data.model_name.strip()
        if model:
            existing = parse_available_models(config.available_models, config.model_name)
            config.available_models = normalize_models([model, *(m for m in existing if m != model)], default=model)
            config.model_name = model

    if data.api_key:
        config.encrypted_api_key = encrypt_api_key(data.api_key.strip())
    if data.temperature is not None:
        config.temperature = data.temperature
    if data.timeout_seconds is not None:
        config.timeout_seconds = data.timeout_seconds
    if data.notes is not None:
        config.notes = data.notes
    config.updated_by = user_id
    await session.flush()
    return config


async def test_connection(
    api_base_url: str,
    model_name: str,
    api_key: str,
    timeout_seconds: int = 20,
) -> tuple[bool, str]:
    """最小代价连通性测试：发一条 8 token 的请求，只回报成功或可读的错误原因。"""
    base = api_base_url.rstrip("/")
    url = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 8,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            )
    except httpx.TimeoutException:
        return False, "连接超时，请检查接口地址或网络"
    except httpx.HTTPError as exc:
        return False, f"网络错误：{exc.__class__.__name__}"

    if response.status_code in (401, 403):
        return False, "鉴权失败，请检查 API Key"
    if response.status_code == 404:
        return False, "接口地址不存在，请检查 Base URL（需包含 /v1）"
    if response.status_code >= 400:
        detail = response.text[:200].replace("\n", " ")
        return False, f"服务返回 {response.status_code}：{detail}"
    return True, "连接成功"


def _extract_models(payload: object) -> list[str]:
    """从各家 OpenAI 兼容的 /models 响应里抽出模型名。

    常见形态：`{"data": [{"id": "qwen-max"}]}`、`{"models": [{"name": ...}]}`、`["a","b"]`。
    抽不出来就返回空列表，由调用方给出手填兜底提示。
    """
    raw_items: list[object] = []
    if isinstance(payload, dict):
        for key in ("data", "models"):
            value = payload.get(key)
            if isinstance(value, list):
                raw_items = value
                break
    elif isinstance(payload, list):
        raw_items = payload

    models: list[str] = []
    for item in raw_items:
        name: object = None
        if isinstance(item, str):
            name = item
        elif isinstance(item, dict):
            name = item.get("id") or item.get("name") or item.get("model")
        if isinstance(name, str):
            cleaned = name.strip()[:MAX_MODEL_NAME_CHARS]
            if cleaned and cleaned not in models:
                models.append(cleaned)
        if len(models) >= 200:
            break
    return models


async def discover_models(
    api_base_url: str,
    api_key: str,
    timeout_seconds: int = 20,
) -> tuple[bool, str, list[str]]:
    """按接口地址拉取模型清单（服务端代理，避免 Key 暴露给浏览器）。

    失败一律返回可读中文原因 + 空列表，让前端退化为手动填模型名。
    """
    base = api_base_url.strip().rstrip("/")
    if not base:
        return False, "请先填写接口地址", []
    if base.endswith("/chat/completions"):
        base = base[: -len("/chat/completions")]
    url = base if base.endswith("/models") else f"{base}/models"

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            )
    except httpx.TimeoutException:
        return False, "连接超时，请检查接口地址或网络", []
    except httpx.HTTPError as exc:
        return False, f"网络错误：{exc.__class__.__name__}", []

    if response.status_code in (401, 403):
        return False, "鉴权失败，请检查 API Key", []
    if response.status_code == 404:
        return False, "该接口不支持获取模型列表，可手动填写模型名", []
    if response.status_code >= 400:
        detail = response.text[:200].replace("\n", " ")
        return False, f"服务返回 {response.status_code}：{detail}", []

    try:
        payload = response.json()
    except ValueError:
        return False, "接口返回内容无法解析，可手动填写模型名", []

    models = _extract_models(payload)
    if not models:
        return False, "没有获取到可用模型，可手动填写模型名", []

    logger.info("模型清单获取成功: base=%s count=%s", base.split("/v1")[0], len(models))
    return True, f"获取到 {len(models)} 个模型", models
