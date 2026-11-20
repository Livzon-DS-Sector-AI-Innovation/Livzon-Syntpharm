"""智能体模块（agent）。

当前能力：PPT 配音视频（PPT + 逐页讲稿 + 中英文旁白 → MP4）。

对外只暴露 `router`；跨模块如需调用请走 `public_api.py`（当前无跨模块调用方）。
"""

from app.modules.agent.api import router

__all__ = ["router"]
