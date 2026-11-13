"""偏差台账常量：状态机、中文标签、超期阈值、分级与原因分类。

口径与妙搭偏差应用对齐（12 态串行状态机 + 8 个待办环节超期阈值）。
本文件是台账（deviation_ledger）唯一的状态定义处；旧 14 态偏差模型与其状态枚举
已随偏差流程下线一并移除，历史表仅保留数据，不再有任何代码读取。
"""

from __future__ import annotations

from enum import StrEnum


class LedgerStatus(StrEnum):
    """偏差台账状态（12 态，串行流转 + 3 个终态/旁路态）。"""

    DRAFT = "draft"
    PENDING_AI_ANALYSIS = "pending_ai_analysis"
    PENDING_INVESTIGATION = "pending_investigation"
    PENDING_DEPT_HEAD_REVIEW = "pending_dept_head_review"
    PENDING_CROSS_DEPT_HEAD_REVIEW = "pending_cross_dept_head_review"
    PENDING_QA_REVIEW = "pending_qa_review"
    PENDING_QA_HEAD_REVIEW = "pending_qa_head_review"
    PENDING_QUALITY_HEAD_REVIEW = "pending_quality_head_review"
    PENDING_FINAL_CODE = "pending_final_code"
    RETURNED = "returned"
    CLOSED = "closed"
    CANCELLED = "cancelled"


#: 所有合法状态值（供 DB CHECK 与应用层校验共用）
LEDGER_STATUSES: tuple[str, ...] = tuple(status.value for status in LedgerStatus)

#: 新建后落库的初始状态：与妙搭一致，创建即进入 AI 分析环节
INITIAL_STATUS = LedgerStatus.PENDING_AI_ANALYSIS.value

#: 状态中文标签
STATUS_LABELS: dict[str, str] = {
    LedgerStatus.DRAFT: "草稿",
    LedgerStatus.PENDING_AI_ANALYSIS: "待AI分析",
    LedgerStatus.PENDING_INVESTIGATION: "待调查",
    LedgerStatus.PENDING_DEPT_HEAD_REVIEW: "待部门负责人审核",
    LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW: "待跨部门负责人审核",
    LedgerStatus.PENDING_QA_REVIEW: "待所属QA审核",
    LedgerStatus.PENDING_QA_HEAD_REVIEW: "待QA负责人审核",
    LedgerStatus.PENDING_QUALITY_HEAD_REVIEW: "待质量负责人审核",
    LedgerStatus.PENDING_FINAL_CODE: "待输入最终编号",
    LedgerStatus.RETURNED: "已退回修改",
    LedgerStatus.CLOSED: "已关闭",
    LedgerStatus.CANCELLED: "已取消",
}

#: 待办环节超期阈值（天）。判定：now - status_updated_at > 阈值 × 24h 且状态为 pending_*
STEP_OVERDUE_DAYS: dict[str, int] = {
    LedgerStatus.PENDING_AI_ANALYSIS: 1,
    LedgerStatus.PENDING_INVESTIGATION: 7,
    LedgerStatus.PENDING_DEPT_HEAD_REVIEW: 3,
    LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW: 3,
    LedgerStatus.PENDING_QA_REVIEW: 5,
    LedgerStatus.PENDING_QA_HEAD_REVIEW: 3,
    LedgerStatus.PENDING_QUALITY_HEAD_REVIEW: 3,
    LedgerStatus.PENDING_FINAL_CODE: 3,
}

#: 环节默认处理人角色名（平台无部门联系人配置时回落到角色名，与妙搭行为一致）
HANDLER_ROLE_LABELS: dict[str, str] = {
    LedgerStatus.PENDING_AI_ANALYSIS: "系统AI分析",
    LedgerStatus.PENDING_INVESTIGATION: "调查人",
    LedgerStatus.PENDING_DEPT_HEAD_REVIEW: "部门负责人",
    LedgerStatus.PENDING_CROSS_DEPT_HEAD_REVIEW: "跨部门负责人",
    LedgerStatus.PENDING_QA_REVIEW: "所属QA",
    LedgerStatus.PENDING_QA_HEAD_REVIEW: "QA负责人",
    LedgerStatus.PENDING_QUALITY_HEAD_REVIEW: "质量负责人",
    LedgerStatus.PENDING_FINAL_CODE: "所属QA",
}

#: 偏差分级 → 中文（库内存英文，界面显示中文，空值显示「-」）
LEVEL_LABELS: dict[str, str] = {
    "minor": "微小",
    "moderate": "中等",
    "major": "严重",
}

#: 合法分级值（DB CHECK 与应用层共用）
DEVIATION_LEVELS: tuple[str, ...] = tuple(LEVEL_LABELS)

#: 原因分类候选（AI 分析后写入，本批不在表单里选）
REASON_CATEGORIES: tuple[str, ...] = ("人员", "设施设备", "产品物料", "文件", "环境", "其它")


def status_label(status: str | None) -> str:
    """状态中文标签，未知状态原样返回。"""
    if not status:
        return "-"
    return STATUS_LABELS.get(status, status)


def level_label(level: str | None) -> str:
    """分级中文标签，空值返回「-」。"""
    if not level:
        return "-"
    return LEVEL_LABELS.get(level, level)
