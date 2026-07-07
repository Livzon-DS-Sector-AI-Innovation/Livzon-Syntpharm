"""SOP AI 定时任务模型

定义定时任务的数据结构。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ScheduledJob:
    """定时任务模型"""

    job_id: str
    job_name: str
    cron_expression: str
    file_pattern: str
    enabled: bool = True
    next_run_time: Optional[datetime] = None
    last_run_time: Optional[datetime] = None
    run_count: int = 0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "job_id": self.job_id,
            "job_name": self.job_name,
            "cron_expression": self.cron_expression,
            "file_pattern": self.file_pattern,
            "enabled": self.enabled,
            "next_run_time": self.next_run_time.isoformat() if self.next_run_time else None,
            "last_run_time": self.last_run_time.isoformat() if self.last_run_time else None,
            "run_count": self.run_count,
        }