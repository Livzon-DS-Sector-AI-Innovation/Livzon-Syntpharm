from app.modules.research import models as _models  # noqa: F401  先加载 ORM，避免子包反向引用出现部分初始化
from app.modules.research.api import router
from app.modules.research.doc_gen import worker as _doc_gen_worker  # noqa: F401  注册文档生成后台 worker
from app.modules.research.knowledge_base import (  # noqa: F401  注册知识库富化后台 worker
    enrich_worker as _kb_enrich_worker,
)

__all__ = ["router"]
