"""母本字节获取：任务快照优先，缺失时回退模板当前文件。

出稿（``agent``）与详情页审阅清单（``review``）必须用同一份母本，否则「当时写在哪」
和「现在列出的位置」会对不上：模板换版后，按当前文件算出来的 p{下标} 已经指向别的段落。
"""

from __future__ import annotations

import logging

from app.modules.research.doc_template import store
from app.modules.research.models import RdDeliverableTemplate, RdReportGenJob

logger = logging.getLogger(__name__)


def load_template_bytes(job: RdReportGenJob, template: RdDeliverableTemplate | None) -> bytes:
    """取母本字节：优先任务快照；没有快照或文件丢失时回退模板当前文件。"""
    if job.template_file_key:
        data = store.load_bytes(str(job.template_file_key))
        if data:
            return data
        logger.warning(
            "report-gen template snapshot missing, fallback to template file",
            extra={"job_id": str(job.id)},
        )
    if template is not None and template.file_object_key:
        data = store.load_bytes(str(template.file_object_key))
        if data:
            return data
    raise RuntimeError("找不到这次生成要用的 Word 模板文件，可能已经被删除。请重新选一份模板再生成。")


def template_cache_key(job: RdReportGenJob, template: RdDeliverableTemplate | None) -> str:
    """缓存键：用实际命中的存储键，快照与模板当前文件不会互相污染。"""
    if job.template_file_key:
        return f"job:{job.id}:{job.template_file_key}"
    key = str(template.file_object_key) if template is not None and template.file_object_key else ""
    return f"template:{key}"


__all__ = ["load_template_bytes", "template_cache_key"]
