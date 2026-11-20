"""DOCX 翻译 —— ORM 模型。

- 术语表：翻译时按语言方向自动套用；
- 历史文件：任务产出的每份译文登记一行（object_key 指向 MinIO 对象），
  支持刷新/重启后仍可下载，并可逐条软删除 + 清理对象。
实时任务进度仍只存在进程内（`jobs.py`），不落库。
"""

from uuid import UUID

from sqlalchemy import BigInteger, Boolean, Float, Index, Integer, String, Text, UniqueConstraint, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel

SOURCE_BUILTIN = "builtin"
SOURCE_MANUAL = "manual"
SOURCE_IMPORT = "import"
TERM_SOURCES: tuple[str, ...] = (SOURCE_BUILTIN, SOURCE_MANUAL, SOURCE_IMPORT)


class DocxTranslationTerm(BaseModel):
    """药品注册中英术语（英文为业务主键，大小写不敏感去重）。"""

    __tablename__ = "docx_translation_terms"
    __table_args__ = (
        # 仅对未软删行唯一：软删后可重建同名词条，否则会撞唯一约束抛 500。
        Index(
            "uq_docx_translation_terms_term_en_lower",
            "term_en_lower",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        Index("ix_docx_translation_terms_enabled", "is_enabled"),
        {"schema": "registration"},
    )

    term_en: Mapped[str] = mapped_column(String(300), nullable=False, comment="英文术语")
    term_en_lower: Mapped[str] = mapped_column(String(300), nullable=False, comment="英文术语小写（去重键）")
    term_zh: Mapped[str] = mapped_column(String(300), nullable=False, comment="中文术语")
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", comment="是否启用"
    )
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SOURCE_MANUAL,
        server_default=SOURCE_MANUAL,
        comment="来源: builtin/manual/import",
    )


class DocxTranslationTask(BaseModel):
    """翻译任务：一次提交一行，历史列表的展示单位。

    历史页是「任务级」：一次翻译可能含多个文件，需记录文件数、成功/失败数、
    参数与原件位置（原件用于「再次翻译」与事后核对）。
    """

    __tablename__ = "docx_translation_tasks"
    __table_args__ = (
        UniqueConstraint("job_ref", name="uq_docx_translation_tasks_job_ref"),
        Index("ix_docx_translation_tasks_created_at", "created_at"),
        Index("ix_docx_translation_tasks_created_by", "created_by"),
        {"schema": "registration"},
    )

    job_ref: Mapped[str] = mapped_column(String(64), nullable=False, comment="任务ID（进程内任务同号）")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="running", comment="状态: running/done/failed"
    )
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", comment="文件总数")
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", comment="成功文件数")
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", comment="失败文件数")
    first_source_filename: Mapped[str] = mapped_column(
        String(500), nullable=False, server_default="", comment="首个原文件名（列表展示）"
    )
    source_lang: Mapped[str] = mapped_column(String(8), nullable=False, comment="源语言")
    target_lang: Mapped[str] = mapped_column(String(8), nullable=False, comment="目标语言")
    mode: Mapped[str] = mapped_column(String(20), nullable=False, comment="输出模式")
    batch_size: Mapped[int] = mapped_column(Integer, nullable=False, server_default="30", comment="每批段落数")
    elapsed_seconds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", comment="耗时(秒)")
    source_keys: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb"), comment="原件位置 [{filename,object_key,size}]"
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="任务级错误")


class DocxTranslationFile(BaseModel):
    """翻译文件记录：一行 = 一个输入文件的处理结果（成功或失败）。

    成功行带产出对象（可下载），失败行 object_key 为空并记录 error，
    供历史详情展示「x 成功 · y 失败」与失败原因。
    """

    __tablename__ = "docx_translation_files"
    __table_args__ = (
        UniqueConstraint("job_ref", "object_key", name="uq_docx_translation_files_job_object"),
        Index("ix_docx_translation_files_created_at", "created_at"),
        Index("ix_docx_translation_files_created_by", "created_by"),
        Index("ix_docx_translation_files_source_filename", "source_filename"),
        Index("ix_docx_translation_files_task_id", "task_id"),
        {"schema": "registration"},
    )

    task_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, comment="所属任务ID")
    job_ref: Mapped[str] = mapped_column(String(64), nullable=False, comment="进程内任务ID（排查用）")
    source_filename: Mapped[str] = mapped_column(String(500), nullable=False, comment="上传的原文件名")
    output_filename: Mapped[str] = mapped_column(String(500), nullable=False, comment="产出文件名")
    output_kind: Mapped[str] = mapped_column(String(20), nullable=False, comment="产出类型: bilingual/translated")
    object_key: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="MinIO 对象 key（失败行可空）")
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", comment="文件大小(字节)")
    source_lang: Mapped[str] = mapped_column(String(8), nullable=False, comment="源语言")
    target_lang: Mapped[str] = mapped_column(String(8), nullable=False, comment="目标语言")
    mode: Mapped[str] = mapped_column(String(20), nullable=False, comment="输出模式: bilingual/replace/both")
    success_rate: Mapped[float] = mapped_column(Float, nullable=False, server_default="0", comment="段落成功率(%)")
    translated_units: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", comment="已翻译段落数")
    total_units: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", comment="总段落数")
    warnings: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb"), comment="告警信息"
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true", comment="该文件是否翻译成功")
    error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="失败原因")
