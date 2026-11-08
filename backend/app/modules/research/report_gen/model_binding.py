"""模型绑定解析：把「配置里填的一个字符串」变成一次调用可用的定位信息。

三种情况（与 knowledge_base/runtime_config 的既有语义一致）：

1. 命中 ``core.llm_configs`` 的配置名或模型名 → 整份切换（端点、密钥、模型都来自该配置）；
2. 未命中 → 只覆盖模型名，端点与密钥沿用当前活跃配置；
3. 留空 → 全部沿用活跃配置。

不直接 import knowledge_base 的实现：模块之间不互相依赖，这里只用 core 层的
``get_named_config``，避免把知识库的运行时细节带进报告生成。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from app.core.llm.config import get_named_config

CONFIG_TYPE = "text"


class ModelCallKwargs(TypedDict):
    """直接 ``**`` 展开给 llm_client 的关键字参数（两个键都必填、互斥生效）。"""

    config_name: str | None
    model_override: str | None


@dataclass(frozen=True, slots=True)
class ModelBinding:
    """一次 LLM 调用该用哪份模型。

    ``raw`` 是运行配置里的原值（配置名或模型名），任务落库时按它写快照，
    执行时再解析一次，保证「重启进程/改配置库」后仍能还原同一档位。
    """

    raw: str | None = None
    config_name: str | None = None
    model: str | None = None

    @property
    def is_empty(self) -> bool:
        return not (self.config_name or self.model)

    @property
    def display(self) -> str | None:
        """页面展示用：模型名优先，只有配置名时退回配置名。"""
        return self.model or self.config_name

    def call_kwargs(self) -> ModelCallKwargs:
        """给 llm_client 的定位参数。

        ``config_name`` 与 ``model_override`` 只传其一：client 里 ``model_override``
        会盖掉配置内的模型名，两者同传等于把整份切换的语义破坏掉。
        """
        if self.config_name:
            return {"config_name": self.config_name, "model_override": None}
        return {"config_name": None, "model_override": self.model}


async def resolve_binding(name: str | None, *, config_type: str = CONFIG_TYPE) -> ModelBinding:
    """解析一个档位：命中配置整份切换，否则只覆盖模型名。"""
    raw = (name or "").strip()
    if not raw:
        return ModelBinding()
    named = await get_named_config(raw, config_type)
    if named is not None:
        return ModelBinding(raw=raw, config_name=named.config_name, model=named.model_name)
    return ModelBinding(raw=raw, model=raw)


async def resolve_bindings(
    main: str | None,
    structure: str | None,
    fallback: str | None,
    *,
    config_type: str = CONFIG_TYPE,
) -> tuple[ModelBinding, ModelBinding, ModelBinding]:
    """一次解析三档；结构识别未单独配置时复用主档（读母本与写正文用同一模型即可）。"""
    main_binding = await resolve_binding(main, config_type=config_type)
    structure_binding = (
        await resolve_binding(structure, config_type=config_type)
        if (structure or "").strip()
        else main_binding
    )
    fallback_binding = await resolve_binding(fallback, config_type=config_type)
    return main_binding, structure_binding, fallback_binding


__all__ = ["CONFIG_TYPE", "ModelBinding", "resolve_binding", "resolve_bindings"]
