"""Doc Check 模块 ORM 模型

doc_check 模块复用 sop_ai 模块的模型。
只定义本模块特有的枚举类型。
"""

from enum import Enum as PyEnum


class CheckStatus(str, PyEnum):
    """校验状态"""

    PENDING = "pending"  # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


class ProblemSeverity(str, PyEnum):
    """问题严重程度"""

    INFO = "info"  # 提示
    WARNING = "warning"  # 警告
    ERROR = "error"  # 错误
    CRITICAL = "critical"  # 严重


class ProblemCategory(str, PyEnum):
    """问题分类"""

    FORMAT = "format"  # 格式问题
    CONTENT = "content"  # 内容问题
    COMPLIANCE = "compliance"  # 合规问题
    LOGIC = "logic"  # 逻辑问题
    MISSING = "missing"  # 缺失问题


class HandleStatus(str, PyEnum):
    """问题处理状态"""

    PENDING = "pending"  # 待处理
    CONFIRMED = "confirmed"  # 已确认
    REJECTED = "rejected"  # 已驳回
    IGNORED = "ignored"  # 已忽略


# 导出 sop_ai 模块的模型供本模块使用
from app.modules.sop_ai.models import (
    SopAiCheckMain as DocCheckMain,
    SopAiCheckProblem as DocCheckProblem,
    SopAiConfig as DocCheckConfig,
)

__all__ = [
    "CheckStatus",
    "ProblemSeverity",
    "ProblemCategory",
    "HandleStatus",
    "DocCheckMain",
    "DocCheckProblem",
    "DocCheckConfig",
]