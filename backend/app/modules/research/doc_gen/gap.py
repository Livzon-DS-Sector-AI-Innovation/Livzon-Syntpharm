"""缺口归因与定向重试的决策逻辑（填充完整性改造 · B4 缺口闭环）。

为什么单独拎一层：判断「这个填充项为什么没填上」需要的是**结构化事实**，而不是从
``SlotResult.reason`` 文案里做字符串匹配——文案是给人看的，随时会改，靠它归因迟
早会错。所以 ``extraction`` 在产出每条结果时当场标注 ``gap_reason``（它最清楚失败
发生在检索、模型、证据回检还是取值校验哪一步），本模块只负责把标注翻译成三个决策：
要不要重试、什么算变好、账怎么记。全是纯函数，不碰数据库也不碰模型，可以被单测穷举。

重试门槛：重试是最贵的补救手段（再调一次模型、再打一次知识库），所以只对「换一套
检索口径还有救」的缺口动手。材料本身没写的、与需求描述不符的、多方材料打架的，
重试多少次都是空转，一律交人工判断。
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.modules.research.doc_gen import status

if TYPE_CHECKING:  # pragma: no cover - 仅用于类型标注，避免与 extraction 形成运行时循环导入
    from app.modules.research.doc_gen.extraction import SlotResult

# ---- 缺口归因 ----------------------------------------------------------------
# 检索没找到任何候选（含宽检索兜底）：要么资料里真没有，要么槽位用语与资料脱节
GAP_NO_MATERIAL = "no_material"
# 模型调用彻底失败（重试与兜底模型都没返回可用结果）
GAP_MODEL_FAILED = "model_failed"
# 模型看到了资料并明确回答「没有这一项」
GAP_NOT_FOUND = "not_found"
# 有值但引用无法在原文中定位（回检失败）
GAP_EVIDENCE_REJECTED = "evidence_rejected"
# 引用只经模糊匹配核对（排版/OCR 差异）
GAP_FUZZY_EVIDENCE = "fuzzy_evidence"
# 模型自报置信度低于中阈值
GAP_LOW_CONFIDENCE = "low_confidence"
# 取值不符合槽位期望格式
GAP_FORMAT_ERROR = "format_error"
# 取值与需求描述（量纲/允许取值）不符——数据本身的性质，重试无用
GAP_REQUIREMENT = "requirement_mismatch"
# 多方资料给出不同值——需人工裁决，重试只会换个说法
GAP_CONFLICT = "conflict"
# 人工填写项（manual_only），AI 不参与
GAP_MANUAL = "manual"

GAP_LABELS: dict[str, str] = {
    GAP_NO_MATERIAL: "资料未命中",
    GAP_MODEL_FAILED: "模型未返回",
    GAP_NOT_FOUND: "材料无此内容",
    GAP_EVIDENCE_REJECTED: "依据未核对上",
    GAP_FUZZY_EVIDENCE: "依据仅模糊匹配",
    GAP_LOW_CONFIDENCE: "置信度不足",
    GAP_FORMAT_ERROR: "取值格式不符",
    GAP_REQUIREMENT: "不符合需求描述",
    GAP_CONFLICT: "材料冲突",
    GAP_MANUAL: "需人工填写",
}

# 换一套检索口径再找一遍有可能变好的缺口（其余缺口重试即空转）。
# GAP_NO_MATERIAL（资料未命中）默认不在其中：首轮主口径与宽检索兜底都已试过，
# 同一套词重试只会拿到同一批结果；只有覆盖预检（A2）判「库里确实有料」时才例外，
# 由调用方通过 ``extra_no_material`` 单独放行。
RETRYABLE_GAPS: frozenset[str] = frozenset(
    {
        GAP_MODEL_FAILED,
        GAP_NOT_FOUND,
        GAP_EVIDENCE_REJECTED,
        GAP_FUZZY_EVIDENCE,
        GAP_LOW_CONFIDENCE,
        GAP_FORMAT_ERROR,
    }
)

# 定向补问的目标：有候选资料但没填上（模型在批量 prompt 里可能漏看）。
# 与 RETRYABLE_GAPS 的区别：补问不换检索口径，而是把「槽位 + 它自己的候选」单独再问一次，
# 所以只挑「当时确实有候选」的归因；资料里真没有（no_material）问了也白问。
PROBE_GAPS: frozenset[str] = frozenset(
    {
        GAP_NOT_FOUND,
        GAP_EVIDENCE_REJECTED,
        GAP_FUZZY_EVIDENCE,
        GAP_LOW_CONFIDENCE,
        GAP_FORMAT_ERROR,
    }
)


def probe_keys(results: Mapping[str, SlotResult], *, allowed: Collection[str] | None = None) -> list[str]:
    """定向补问的目标槽位 key（保持 ``results`` 原有顺序）。"""
    keys: list[str] = []
    for key, result in results.items():
        if allowed is not None and key not in allowed:
            continue
        if result.gap_reason in PROBE_GAPS:
            keys.append(key)
    return keys


# 状态高低：只用于判断「重试后的新结果是否真的比原来好」。
# 注意 DRAFT（有值无依据）低于 NEEDS_VERIFY（有值待核对），CONFLICT 与 NEEDS_VERIFY 同级
# 且不参与重试，仅保证比较函数对任意状态都有定义。
_STATE_RANK: dict[str, int] = {
    status.STATUS_FAILED: 0,
    status.STATUS_PENDING: 1,
    status.STATUS_DRAFT: 2,
    status.STATUS_NEEDS_VERIFY: 3,
    status.STATUS_CONFLICT: 3,
    status.STATUS_OK: 4,
    status.STATUS_OVERFLOW: 4,
}


def reason_label(reason: str) -> str:
    """归因的中文标签（未知归因原样返回，便于发现新缺口类型）。"""
    return GAP_LABELS.get(reason, reason)


def state_rank(state: str) -> int:
    """状态高低分；未登记的状态按最低处理，避免被误判为「有提升」。"""
    return _STATE_RANK.get(state, 0)


def is_improvement(old_state: str, new_state: str) -> bool:
    """新结果是否优于旧结果。

    重试只允许「变好」，不允许把已验证的值换成更弱的结果——重试是为了补缺口，
    不是为了刷新内容。
    """
    return state_rank(new_state) > state_rank(old_state)


def gap_reasons(results: Mapping[str, SlotResult]) -> dict[str, int]:
    """归因分布：缺口原因 → 条数（无归因的结果即已填充，不计入）。"""
    counted: dict[str, int] = {}
    for result in results.values():
        if not result.gap_reason:
            continue
        counted[result.gap_reason] = counted.get(result.gap_reason, 0) + 1
    return counted


def retryable_keys(
    results: Mapping[str, SlotResult],
    *,
    allowed: Collection[str] | None = None,
    extra_no_material: Collection[str] | None = None,
) -> list[str]:
    """可重试的缺口槽位 key，保持 ``results`` 的原有顺序。

    ``allowed`` 用于把候选限定在本次确有实例的槽位集合内（动态章节的槽位只在实例化
    之后才存在），避免对不上模板的陈旧结果发起重试。

    ``extra_no_material`` 是覆盖预检判「库里有料」（可填/部分可填）的槽位 key：
    「资料未命中」默认不重试，但这些槽位例外——首轮零命中更可能是检索的临时问题，
    而不是资料里真的没有。
    """
    keys: list[str] = []
    for key, result in results.items():
        if allowed is not None and key not in allowed:
            continue
        reason = result.gap_reason
        if reason in RETRYABLE_GAPS:
            keys.append(key)
        elif reason == GAP_NO_MATERIAL and extra_no_material is not None and key in extra_no_material:
            keys.append(key)
    return keys


def blocked_keys(results: Mapping[str, SlotResult], *, allowed: Collection[str] | None = None) -> list[str]:
    """有归因但**故意不重试**的缺口槽位 key（冲突/需求不符/人工填写/资料未命中）。

    单独记一笔而不是静默跳过：这些缺口只能靠人工收口，数量本身就是需要暴露的信号。
    """
    keys: list[str] = []
    for key, result in results.items():
        if allowed is not None and key not in allowed:
            continue
        if result.gap_reason and result.gap_reason not in RETRYABLE_GAPS:
            keys.append(key)
    return keys


@dataclass(slots=True)
class GapStats:
    """缺口闭环的过程账（并入 ``job.stats``）。"""

    # 首轮可重试的缺口槽位数
    targets: int = 0
    # 归因为「重试无用」而直接交人工的缺口槽位数
    blocked: int = 0
    # 实际执行的重试轮数
    rounds: int = 0
    # 重试后状态确有提升的槽位数
    recovered: int = 0
    # 首轮归因分布（中文标签 → 条数）
    reasons: dict[str, int] = field(default_factory=dict)

    def as_job_stats(self) -> dict[str, object]:
        """并入 ``job.stats`` 的扁平字段。"""
        return {
            "gap_targets": self.targets,
            "gap_blocked": self.blocked,
            "gap_rounds": self.rounds,
            "gap_recovered": self.recovered,
            "gap_reasons": dict(self.reasons),
        }
