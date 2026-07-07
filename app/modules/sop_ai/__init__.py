"""SOP AI 模块 - 文件合规校验

提供基于 SimHash 的文件查重算法和 AI 辅助校验功能。
支持单文件预审、批量巡检、定时任务等业务场景。
"""

from app.modules.sop_ai.api import router

__all__ = ["router"]