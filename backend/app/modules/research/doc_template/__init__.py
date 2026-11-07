"""交付物模板的 Word 母本管理（上传、版本留档、下载、回滚）。

这里只处理文件本身：不解析模板结构、不推断填充项，也不涉及任何文档生成能力。
"""

from app.modules.research.doc_template.api import router

__all__ = ["router"]
