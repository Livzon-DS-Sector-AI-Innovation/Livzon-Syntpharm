"""AI 能力平台模块

提供统一的 AI 服务能力，包括 MiniMax 等大模型调用接口。
"""

from app.platform.ai.minimax_util import MinimaxAiUtil, get_ai_util

__all__ = ["MinimaxAiUtil", "get_ai_util"]