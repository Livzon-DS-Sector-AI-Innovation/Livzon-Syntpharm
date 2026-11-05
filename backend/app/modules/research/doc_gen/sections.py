"""动态章节实例化：触发求值 → 标题合成 → 槽位展开。

三条设计约束：

1. **判定必须可解释**：每次触发求值都产出 trace（命中/未命中哪条规则），随章节一起落库
   并写进生成说明。求值异常一律判为「未触发」并记 warning，绝不让单个片段拖垮整个任务。
2. **结构变化在取值之前摊平**：章节实例化后，其局部槽位立即展开成带实例前缀的扁平 key
   （``route_study__0.yield``），因此解析、检索、模型调用、证据回检、落库全部无需感知章节结构。
3. **标题只取自预设池**：标题一律来自片段的 ``title_pool``，模型不参与标题生成；
   标题文字里不含编号，编号由 Word 标题样式的多级列表生成。
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from app.modules.research.doc_gen import status
from app.modules.research.doc_gen.parsing import TextBlock
from app.modules.research.doc_gen.template_spec import (
    SECTION_INSTANCE_SEP,
    ExtensionPoint,
    SectionFragment,
    Slot,
    TemplateSpec,
    Trigger,
    expand_slot_key,
)

logger = logging.getLogger(__name__)

# 任一扩展点的实例数硬顶：配置写错（如 max_instances=1000）也不允许把任务拖垮
MAX_INSTANCES_HARD_CAP = 30
# 章节嵌套深度硬顶
MAX_DEPTH = 4

# 标题变量：{index} / {meta:xxx} / {slot:xxx} / {repeat:xxx}
_TITLE_VAR_RE = re.compile(r"\{([a-z_]+)(?::([^{}]*))?\}")

# 视为「有实质值」的槽位状态：冲突也算有数据（应当长出章节，让人去解决冲突）
_SUBSTANTIVE_STATES = frozenset({status.STATUS_OK, status.STATUS_DRAFT, status.STATUS_CONFLICT})


@dataclass(slots=True)
class TriggerContext:
    """触发判定可用的数据快照。"""

    results: Mapping[str, Any] = field(default_factory=dict)  # slot_key -> SlotResult
    roles: Mapping[str, Sequence[str]] = field(default_factory=dict)  # file_id -> roles
    meta: Mapping[str, Any] = field(default_factory=dict)  # 任务元数据
    text: str = ""  # 解析文本归一化结果（小写、去空白），供关键词判定

    def has_role(self, role: str) -> bool:
        """是否存在携带该角色的资料文件。"""
        return any(role in roles for roles in self.roles.values())


def build_trigger_context(
    results: Mapping[str, Any],
    blocks: Sequence[TextBlock],
    roles: Mapping[str, Sequence[str]] | None = None,
    meta: Mapping[str, Any] | None = None,
) -> TriggerContext:
    """把解析与取值结果整理成触发判定的上下文（关键词文本只归一化一次）。"""
    normalized = re.sub(r"\s+", "", "".join(block.text for block in blocks)).lower()
    return TriggerContext(results=dict(results), roles=dict(roles or {}), meta=dict(meta or {}), text=normalized)


@dataclass(slots=True)
class SectionInstance:
    """一个已确定的章节实例。"""

    section_key: str  # route_study__0
    fragment_key: str  # route_study
    extension_point_key: str  # 挂载点
    parent_section_key: str | None  # 父实例（多层级）
    level: int
    title: str
    order_index: int
    source: str = "auto"  # auto / manual
    state: str = "enabled"  # enabled / disabled
    trigger_trace: dict[str, Any] = field(default_factory=dict)
    slots: list[Slot] = field(default_factory=list)  # 已展开（key 带实例前缀）

    @property
    def slot_keys(self) -> list[str]:
        """展开后的槽位 key 列表（按声明顺序）。"""
        return [slot.key for slot in self.slots]

    @property
    def anchor_key(self) -> str:
        """渲染时的挂载游标：子章节挂在父实例后，顶层章节挂在扩展点上。"""
        return self.parent_section_key or f"ext:{self.extension_point_key}"

    def describe(self) -> dict[str, Any]:
        """落库与生成说明用的摘要。"""
        return {
            "section_key": self.section_key,
            "fragment_key": self.fragment_key,
            "parent_section_key": self.parent_section_key,
            "level": self.level,
            "title": self.title,
            "order_index": self.order_index,
            "source": self.source,
            "state": self.state,
            "trigger_trace": self.trigger_trace,
        }


@dataclass(slots=True)
class InstantiateResult:
    """实例化产出：章节清单 + 过程中产生的告警。"""

    instances: list[SectionInstance] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # 每个片段的全局实例计数：多层级下同一片段会挂在不同父章节下，
    # 若按「父内序号」编号会产生重复的 section_key（如两个父章节下都是 impurity__0），
    # 因此序号必须按片段全局递增，保证 section_key 唯一。
    counters: dict[str, int] = field(default_factory=dict)

    @property
    def slots(self) -> list[Slot]:
        """全部章节局部槽位（已展开，按章节顺序）。"""
        return [slot for instance in self.instances for slot in instance.slots]


# ---------------------------------------------------------------------------
# 触发求值
# ---------------------------------------------------------------------------


def evaluate_trigger(trigger: Trigger | None, ctx: TriggerContext) -> tuple[bool, dict[str, Any]]:
    """求值触发规则，返回 ``(是否触发, 判定依据)``。

    未声明触发条件视为无条件成立；求值异常一律判为未触发并记录原因——
    判定环节的失败必须是「少生成一节」，而不是「整个任务失败」。
    """
    if trigger is None:
        return True, {"op": "always", "hit": True, "detail": "未声明触发条件"}
    try:
        return _eval_trigger(trigger, ctx)
    except Exception as exc:  # noqa: BLE001 - 判定失败只降级，不中断任务
        logger.warning("章节触发规则求值异常", extra={"op": trigger.op, "error": type(exc).__name__})
        return False, {"op": trigger.op, "hit": False, "detail": f"规则求值异常：{type(exc).__name__}: {exc}"[:200]}


def _eval_trigger(trigger: Trigger, ctx: TriggerContext) -> tuple[bool, dict[str, Any]]:
    """递归求值单个触发规则，返回命中结果与带子节点的依据树。"""
    op = trigger.op

    if op == "slot_filled":
        result = ctx.results.get(trigger.key or "")
        hit = _has_substance(result)
        detail = f"槽位 {trigger.key} 有实质值" if hit else f"槽位 {trigger.key} 无实质值"
        return hit, {"op": op, "key": trigger.key, "hit": hit, "detail": detail}

    if op == "table_rows_at_least":
        result = ctx.results.get(trigger.key or "")
        rows = list(getattr(result, "rows", None) or [])
        hit = len(rows) >= max(1, trigger.count)
        return hit, {
            "op": op,
            "key": trigger.key,
            "hit": hit,
            "detail": f"表格 {trigger.key} 有效行数 {len(rows)}，阈值 {max(1, trigger.count)}",
        }

    if op == "keyword_found":
        for keyword in trigger.keywords:
            needle = re.sub(r"\s+", "", keyword).lower()
            if needle and needle in ctx.text:
                return True, {"op": op, "hit": True, "detail": f"命中关键词「{keyword}」"}
        return False, {"op": op, "hit": False, "detail": f"未命中关键词 {trigger.keywords}"}

    if op == "role_present":
        hit = ctx.has_role(trigger.role or "")
        return hit, {"op": op, "role": trigger.role, "hit": hit, "detail": f"来源角色 {trigger.role} 存在={hit}"}

    if op == "meta_equals":
        actual = str(ctx.meta.get(trigger.key or "") or "")
        hit = actual == str(trigger.value or "")
        return hit, {
            "op": op,
            "key": trigger.key,
            "hit": hit,
            "detail": f"元数据 {trigger.key}={actual!r}，期望 {trigger.value!r}",
        }

    if op in {"all_of", "any_of"}:
        children = [_eval_trigger(child, ctx) for child in trigger.of]
        hits = [hit for hit, _ in children]
        hit = all(hits) if op == "all_of" else any(hits)
        return hit, {
            "op": op,
            "hit": hit,
            "detail": f"{sum(hits)}/{len(hits)} 条子规则成立",
            "children": [trace for _, trace in children],
        }

    if op == "not":
        child_hit, child_trace = _eval_trigger(trigger.of[0], ctx)
        return (not child_hit), {"op": op, "hit": not child_hit, "detail": "取反", "children": [child_trace]}

    return False, {"op": op, "hit": False, "detail": f"未知触发原语 {op}"}


def _has_substance(result: Any) -> bool:
    """槽位是否「有实质值」：表格看行数，标量看状态与文本。"""
    if result is None:
        return False
    if list(getattr(result, "rows", None) or []):
        return True
    if getattr(result, "state", "") not in _SUBSTANTIVE_STATES:
        return False
    text = str(getattr(result, "text", "") or "").strip()
    return bool(text) and not status.is_pending(text)


# ---------------------------------------------------------------------------
# 实例化
# ---------------------------------------------------------------------------


def instantiate(spec: TemplateSpec, ctx: TriggerContext) -> InstantiateResult:
    """按扩展点与片段声明，把「可能的章节」实例化为「确定的章节清单」。

    产出为 DFS 前序：父章节紧跟其子章节，同级按扩展点声明的片段顺序排列，
    该顺序同时就是渲染顺序与大纲默认顺序（人工调整在复核阶段覆盖）。
    """
    result = InstantiateResult()
    if not spec.has_sections:
        return result
    for point in sorted(spec.extension_points, key=lambda p: (p.sequence, p.key)):
        _instantiate_point(spec, point, parent=None, ctx=ctx, result=result, depth=1)
    for index, instance in enumerate(result.instances):
        instance.order_index = index
    if result.instances:
        logger.info(
            "动态章节实例化完成",
            extra={
                "template": spec.code,
                "sections": len(result.instances),
                "slots": len(result.slots),
                "warnings": len(result.warnings),
            },
        )
    return result


def _instantiate_point(
    spec: TemplateSpec,
    point: ExtensionPoint,
    parent: SectionInstance | None,
    ctx: TriggerContext,
    result: InstantiateResult,
    depth: int,
) -> None:
    """处理一个扩展点：逐个片段判定、实例化，并递归其子扩展点。"""
    if depth > MAX_DEPTH:
        result.warnings.append(f"扩展点 {point.key} 超过最大嵌套深度 {MAX_DEPTH}，已跳过")
        return
    limit = min(point.max_instances, MAX_INSTANCES_HARD_CAP)
    created = 0
    for fragment_key in point.fragments:
        if created >= limit:
            result.warnings.append(f"扩展点 {point.key} 已达实例上限 {limit}，其余片段不再生成")
            break
        fragment = spec.fragment(fragment_key)
        if fragment is None:
            result.warnings.append(f"扩展点 {point.key} 引用的片段 {fragment_key} 不存在，已跳过")
            continue
        for instance in _build_instances(spec, point, fragment, parent, ctx, result, limit - created):
            result.instances.append(instance)
            created += 1
            for child_point in sorted(fragment.extension_points, key=lambda p: (p.sequence, p.key)):
                _instantiate_point(spec, child_point, parent=instance, ctx=ctx, result=result, depth=depth + 1)


def _build_instances(
    spec: TemplateSpec,
    point: ExtensionPoint,
    fragment: SectionFragment,
    parent: SectionInstance | None,
    ctx: TriggerContext,
    result: InstantiateResult,
    capacity: int,
) -> list[SectionInstance]:
    """为一个片段产出若干实例：先判定触发，再按重复源展开。"""
    hit, trace = evaluate_trigger(fragment.trigger, ctx)
    if not hit:
        logger.info(
            "章节片段未触发",
            extra={"fragment": fragment.key, "point": point.key, "detail": trace.get("detail")},
        )
        return []

    rows = _repeat_rows(fragment, ctx)
    if rows is None:
        rows = [{}]
    if not rows:
        result.warnings.append(f"片段 {fragment.key} 的重复源 {fragment.repeat_over} 为空，未生成章节")
        return []

    if len(rows) > capacity:
        result.warnings.append(f"片段 {fragment.key} 需要 {len(rows)} 个实例，超过剩余容量 {capacity}，已截断")
        rows = rows[:capacity]

    instances: list[SectionInstance] = []
    for row in rows:
        index = result.counters.get(fragment.key, 0)
        result.counters[fragment.key] = index + 1
        section_key = f"{fragment.key}{SECTION_INSTANCE_SEP}{index}"
        title, title_warnings = compose_title(fragment, index, row, ctx)
        result.warnings.extend(title_warnings)
        instances.append(
            SectionInstance(
                section_key=section_key,
                fragment_key=fragment.key,
                extension_point_key=point.key,
                parent_section_key=parent.section_key if parent is not None else None,
                level=point.level,
                title=title,
                order_index=0,  # 统一在 instantiate 末尾按 DFS 顺序重排
                trigger_trace={
                    **trace,
                    "repeat": {"over": fragment.repeat_over, "row": dict(row)} if fragment.repeat_over else None,
                },
                slots=_expand_slots(fragment, section_key),
            )
        )
    return instances


def _repeat_rows(fragment: SectionFragment, ctx: TriggerContext) -> list[dict[str, Any]] | None:
    """重复源展开：返回每行的字段字典；未声明 repeat_over 时返回 None（单例章节）。"""
    if not fragment.repeat_over:
        return None
    source = ctx.results.get(fragment.repeat_over)
    rows = list(getattr(source, "rows", None) or [])
    return [{str(k): str(v) for k, v in dict(row).items()} for row in rows]


def _expand_slots(fragment: SectionFragment, section_key: str) -> list[Slot]:
    """把片段局部槽位展开为带实例前缀的槽位定义（下游全部无感）。"""
    expanded: list[Slot] = []
    for slot in fragment.slots:
        expanded.append(slot.model_copy(update={"key": expand_slot_key(section_key, slot.key)}))
    return expanded


# ---------------------------------------------------------------------------
# 标题合成
# ---------------------------------------------------------------------------


def compose_title(
    fragment: SectionFragment,
    index: int,
    row: Mapping[str, str],
    ctx: TriggerContext,
    template: str | None = None,
) -> tuple[str, list[str]]:
    """按标题池合成标题，返回 ``(标题, 告警列表)``。

    ``template`` 为空时用池内默认项；人工在大纲里换标题时传入池内另一项。
    变量一律取自白名单来源；解析为空的变量按空串替换并记告警——
    标题缺字比标题留空更容易被发现，因此不做「静默补全」。
    """
    warnings: list[str] = []
    template = template or fragment.default_title

    def _replace(match: re.Match[str]) -> str:
        prefix, arg = match.group(1), match.group(2) or ""
        if prefix == "index":
            return str(index + 1)
        if prefix == "repeat":
            value = str(row.get(arg, "") or "").strip()
            if not value:
                warnings.append(f"片段 {fragment.key} 的标题变量 {{repeat:{arg}}} 在重复源中取值为空")
            return value
        if prefix == "meta":
            value = str(ctx.meta.get(arg, "") or "").strip()
            if not value:
                warnings.append(f"片段 {fragment.key} 的标题变量 {{meta:{arg}}} 取值为空")
            return value
        if prefix == "slot":
            result = ctx.results.get(arg)
            value = str(getattr(result, "text", "") or "").strip()
            if not value or status.is_pending(value):
                warnings.append(f"片段 {fragment.key} 的标题变量 {{slot:{arg}}} 无可用取值")
                return ""
            return value
        return match.group(0)

    title = _TITLE_VAR_RE.sub(_replace, template).strip()
    return title or fragment.label or fragment.key, warnings


def _index_of(section_key: str) -> int:
    """从章节实例 key 里取出序号（``route_study__2`` → 2）。"""
    tail = section_key.rpartition(SECTION_INSTANCE_SEP)[2]
    return int(tail) if tail.isdigit() else 0


def recompose_title(
    fragment: SectionFragment,
    section_key: str,
    template: str,
    results: Mapping[str, Any],
    meta: Mapping[str, Any],
    repeat_row: Mapping[str, str] | None = None,
) -> tuple[str, list[str]]:
    """用指定的标题池项重新合成标题（人工在大纲里换标题时用）。

    标题必须来自片段的预设池——这是「标题从预设池里选」这条约束的落地点，
    不允许人工输入池外文字，防止标题漂移出模板治理范围。
    """
    if template not in fragment.title_pool:
        raise ValueError(f"标题不在片段 {fragment.key} 的预设池内")
    ctx = TriggerContext(results=dict(results), meta=dict(meta))
    return compose_title(fragment, _index_of(section_key), dict(repeat_row or {}), ctx, template=template)


__all__ = [
    "MAX_DEPTH",
    "MAX_INSTANCES_HARD_CAP",
    "InstantiateResult",
    "SectionInstance",
    "TriggerContext",
    "build_trigger_context",
    "compose_title",
    "evaluate_trigger",
    "instantiate",
    "recompose_title",
]
