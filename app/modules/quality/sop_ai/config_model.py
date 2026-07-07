"""SOP AI 模块配置模型

定义模块的元数据和配置信息。
"""

from dataclasses import dataclass

from app.shared.module_registry import ModuleDefinition


@dataclass(frozen=True)
class SopAiModuleConfig:
    """SOP AI 模块配置"""

    code: str = "sop_ai"
    name: str = "文件合规校验"
    path: str = "/sop-ai"
    db_schema: str = "sop_ai"
    owner_hint: str = "QA/文档管理员"
    description: str = "基于 SimHash 的文件查重和 AI 辅助校验模块"

    def to_module_definition(self) -> ModuleDefinition:
        """转换为模块定义"""
        return ModuleDefinition(
            code=self.code,
            name=self.name,
            path=self.path,
            db_schema=self.db_schema,
            owner_hint=self.owner_hint,
            description=self.description,
        )


# 模块配置单例
SOP_AI_MODULE = SopAiModuleConfig()