from __future__ import annotations

from app.core.job_store import JobStore

# HR 模块后台任务状态表（进程内）：hr/api.py 与 ai_exam 子包共用同一个实例，
# 保证 GET /api/v1/hr/jobs/{job_id} 能查到所有 HR 后台任务。
hr_job_store = JobStore()
