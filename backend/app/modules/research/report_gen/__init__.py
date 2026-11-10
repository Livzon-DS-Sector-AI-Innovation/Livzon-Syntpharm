"""AI 报告生成（Agent 版）。

子模块职责：
- ``structure``：母本解析与槽位定义（含缓存）
- ``tools``：Agent 可调用的工具集
- ``agent``：Agent 循环（tools / JSON-action 双轨）
- ``render``：按锚点回写母本并生成对照表
- ``service``：任务状态机、查询与下载
"""

__all__: list[str] = []
