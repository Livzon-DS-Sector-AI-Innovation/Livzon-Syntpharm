"""0114_drop_doc_gen_tables

Revision ID: 0114_drop_doc_gen_tables
Revises: 0113_backfill_doc_gen_template_structure
Create Date: 2026-11-07 12:00:00.000000

「AI 生成报告」功能整体下线，删除 doc_gen 的 9 张表：

- ``doc_gen_jobs``：生成任务主表（状态、模板快照、产物地址）
- ``doc_gen_input_files``：任务输入资料
- ``doc_gen_slot_values``：逐填充项的取值与出处
- ``doc_gen_conversations`` / ``doc_gen_messages``：补值对话
- ``doc_gen_sections``：章节成文结果
- ``doc_gen_corpus_documents``：语料文档
- ``doc_gen_parse_cache`` / ``doc_gen_extract_cache``：解析与抽取缓存

代码侧已无任何读写方（子包、路由、前端入口同时移除）。**执行前请先备份**：

    pg_dump -h <host> -U <user> -d <db> -t research.doc_gen_corpus_documents \\
        -t research.doc_gen_jobs -t research.doc_gen_slot_values \\
        -f doc_gen_backup_$(date +%Y%m%d).sql

存量数据只有 ``doc_gen_corpus_documents`` 有实际内容（UAT 4 行），其余为运行时产物。
幂等删除（不存在即跳过）；downgrade 不重建表结构，需要恢复时请从上面的备份导入。
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0114_drop_doc_gen_tables"
down_revision: str | Sequence[str] | None = "0113_backfill_doc_gen_template_structure"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "research"

# 子表在前、父表在后：CASCADE 已能兜住外键，顺序只是为了日志可读
_TABLES = (
    "doc_gen_messages",
    "doc_gen_conversations",
    "doc_gen_sections",
    "doc_gen_slot_values",
    "doc_gen_input_files",
    "doc_gen_corpus_documents",
    "doc_gen_parse_cache",
    "doc_gen_extract_cache",
    "doc_gen_jobs",
)


def upgrade() -> None:
    for table in _TABLES:
        op.execute(f"DROP TABLE IF EXISTS {_SCHEMA}.{table} CASCADE")

    # 生成相关运营参数随功能下线清掉；知识库富化仍在读的 KB_*/模型项保留，
    # 否则会把存量里「关闭富化」「切换模型」的选择悄悄重置回默认值。
    op.execute(
        "DELETE FROM core.module_settings WHERE key LIKE 'DOC_GEN%' "
        "AND key NOT LIKE 'DOC_GEN_KB_%' "
        "AND key NOT IN ('DOC_GEN_FACT_EXTRACT_BATCH_SIZE', 'DOC_GEN_FACT_EXTRACT_CONCURRENCY', "
        "'DOC_GEN_LLM_CALL_TIMEOUT_SECONDS', 'DOC_GEN_EXTRACT_MODEL', 'DOC_GEN_FALLBACK_MODEL')"
    )


def downgrade() -> None:
    """不重建：9 张表的结构已随功能删除，恢复请从执行前的 pg_dump 备份导入。"""
    pass
