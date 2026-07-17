"""
法规分类服务

根据 AI 分析结果计算法规分类（document_category）。
分类逻辑由系统决定，不由 AI 输出。
"""

import logging

logger = logging.getLogger(__name__)


# 分类常量（英文代码）
CATEGORY_ATTENTION = "attention"  # 重点关注
CATEGORY_GENERAL = "general"  # 一般法规
CATEGORY_ARCHIVE = "archive"  # 法规档案
CATEGORY_FAILED = "failed"  # 分析失败


def compute_document_category(
    ai_analysis_status: str | None,
    impact_level: str | None,
    focus_required: bool | None,
    archive_recommended: bool | None,
) -> str:
    """
    根据 AI 分析结果计算法规分类

    分类规则：
    1. AI 分析失败 → failed
    2. 高影响 或 focus_required=True → attention
    3. 无影响 或 archive_recommended=True → archive
    4. 其他（中/低影响）→ general

    Args:
        ai_analysis_status: AI 分析状态 (pending/completed/failed/None)
        impact_level: 影响等级 (high/medium/low/none)
        focus_required: 是否需要重点关注
        archive_recommended: 是否建议归档

    Returns:
        分类代码: attention/general/archive/failed
    """
    # AI 分析失败
    if ai_analysis_status == "failed":
        return CATEGORY_FAILED

    # AI 未完成
    if ai_analysis_status != "completed":
        return CATEGORY_GENERAL  # 默认分类

    # 高影响或需要重点关注
    if impact_level == "high" or focus_required is True:
        return CATEGORY_ATTENTION

    # 无影响或建议归档
    if impact_level == "none" or archive_recommended is True:
        return CATEGORY_ARCHIVE

    # 中/低影响
    return CATEGORY_GENERAL


def get_category_display_name(category: str) -> str:
    """
    获取分类的中文显示名称

    Args:
        category: 分类代码

    Returns:
        中文名称
    """
    display_map = {
        CATEGORY_ATTENTION: "重点关注",
        CATEGORY_GENERAL: "一般法规",
        CATEGORY_ARCHIVE: "法规档案",
        CATEGORY_FAILED: "分析失败",
    }
    return display_map.get(category, "未知分类")
