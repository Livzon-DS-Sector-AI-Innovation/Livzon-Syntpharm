"""交付物模板的 Word 母本管理（上传、版本留档、下载、回滚）。

母本管理只处理文件本身：上传不解析结构、不推断填充项、不生成示例稿。
母本里写哪里，由生成时的智能体读母本自己决定（见 ``report_gen/outline.py``）。
"""

from app.modules.research.doc_template.api import router

__all__ = ["router"]
