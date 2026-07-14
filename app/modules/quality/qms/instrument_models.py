"""Instrument Calibration Models (仪器校准管理数据模型)

仪器设备台账、校准规则配置、校准记录、审批记录
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel


class InstrumentStatus(enum.StrEnum):
    """仪器状态"""

    DRAFT = "draft"  # 草稿
    SUBMITTED = "submitted"  # 已提交
    ADMIN_APPROVED = "admin_approved"  # 设备管理员已审核
    QA_APPROVED = "qa_approved"  # QA已审核
    ACTIVE = "active"  # 已启用
    INACTIVE = "inactive"  # 已停用


class CalibrationMethod(enum.StrEnum):
    """校准方式"""

    EXTERNAL = "external"  # 外委校准
    INTERNAL = "internal"  # 内部校准


class CalibrationCycleUnit(enum.StrEnum):
    """校准周期单位"""

    MONTH = "month"  # 月
    YEAR = "year"  # 年


class IQStatus(enum.StrEnum):
    """IQ确认状态"""

    PENDING = "pending"  # 待确认
    CONFIRMED = "confirmed"  # 已确认
    NOT_REQUIRED = "not_required"  # 不需要


class OQStatus(enum.StrEnum):
    """OQ确认状态"""

    PENDING = "pending"  # 待确认
    CONFIRMED = "confirmed"  # 已确认
    NOT_REQUIRED = "not_required"  # 不需要


class InstrumentCategory(enum.StrEnum):
    """仪器分类"""

    PHYSICOCHEMICAL = "physicochemical"  # 理化
    CHROMATOGRAPHY = "chromatography"  # 色谱
    MICROBIOLOGY = "microbiology"  # 微生物
    BALANCE = "balance"  # 天平
    OVEN = "oven"  # 烘箱
    OTHER = "other"  # 其他


class CalibrationResult(enum.StrEnum):
    """校准结论"""

    QUALIFIED = "qualified"  # 合格
    UNQUALIFIED = "unqualified"  # 不合格
    LIMITED = "limited"  # 限用


class RecordStatus(enum.StrEnum):
    """校准记录状态"""

    DRAFT = "draft"  # 草稿
    SUBMITTED = "submitted"  # 已提交
    ADMIN_APPROVED = "admin_approved"  # 设备管理员已审核
    QA_APPROVED = "qa_approved"  # QA已审核
    COMPLETED = "completed"  # 已完成


class ApprovalType(enum.StrEnum):
    """审批类型"""

    INSTRUMENT = "instrument"  # 仪器档案审批
    RECORD = "record"  # 校准记录审批


class ApprovalStatus(enum.StrEnum):
    """审批状态"""

    PENDING = "pending"  # 待审批
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 已驳回


# ========== 仪器设备台账主表 ==========
class InstrumentCalibration(BaseModel):
    """仪器设备台账"""

    __tablename__ = "instrument_calibrations"
    __table_args__ = (
        Index("idx_instrument_no", "instrument_no", unique=True),
        Index("idx_instrument_name", "instrument_name"),
        Index("idx_instrument_category", "category"),
        Index("idx_instrument_status", "status"),
        Index("idx_instrument_active", "is_active"),
        {"schema": "quality"},
    )

    # 仪器基本信息
    instrument_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, comment="仪器编号")
    instrument_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="仪器名称")
    model: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="型号")
    serial_no: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="出厂编号")
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="制造商")
    # 存放信息
    location: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="存放地点")
    # 仪器分类
    category: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="仪器分类")
    # 出厂日期
    manufacture_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="出厂日期"
    )
    # IQ/OQ确认状态
    iq_status: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="IQ确认状态")
    oq_status: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="OQ确认状态")
    iq_confirm_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="IQ确认日期"
    )
    oq_confirm_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="OQ确认日期"
    )
    # 使用负责人
    responsible_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, comment="使用负责人ID"
    )
    responsible_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="使用负责人")
    # 启用状态
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False, comment="是否启用")
    deactivate_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="停用日期")
    deactivate_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="停用原因")
    # 审核状态
    status: Mapped[str] = mapped_column(String(32), server_default="draft", nullable=False, comment="状态")
    # 备注
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # 关系
    calibration_rules: Mapped[list["InstrumentCalibrationRule"]] = relationship(
        "InstrumentCalibrationRule", back_populates="instrument", lazy="selectin"
    )
    calibration_records: Mapped[list["InstrumentCalibrationRecord"]] = relationship(
        "InstrumentCalibrationRecord", back_populates="instrument", lazy="selectin"
    )


# ========== 仪器校准规则配置表 ==========
class InstrumentCalibrationRule(BaseModel):
    """校准规则配置"""

    __tablename__ = "instrument_calibration_rules"
    __table_args__ = (
        Index("idx_rule_instrument", "instrument_id"),
        Index("idx_rule_next_date", "next_calibration_date"),
        {"schema": "quality"},
    )

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("quality.instrument_calibrations.id"),
        nullable=False,
        comment="关联仪器ID",
    )
    # 校准方式
    calibration_method: Mapped[str] = mapped_column(String(32), nullable=False, comment="校准方式")
    # 校准周期
    calibration_cycle: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="校准周期")
    calibration_unit: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="周期单位")
    # 最近校准信息
    last_calibration_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最近校准日期"
    )
    next_calibration_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="下次校准日期"
    )
    # 校准机构（外校时）
    calibration_agency: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="校准机构名称")
    agency_contact: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="机构联系方式")
    # 内校人员
    internal_calibrator_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, comment="内校人员ID"
    )
    internal_calibrator_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="内校人员")
    # 到期预警
    warning_days: Mapped[int | None] = mapped_column(Integer, server_default="7", nullable=True, comment="提前预警天数")
    # 是否启用
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False, comment="是否启用")

    # 关系
    instrument: Mapped["InstrumentCalibration"] = relationship(
        "InstrumentCalibration", back_populates="calibration_rules"
    )


# ========== 仪器校准记录表 ==========
class InstrumentCalibrationRecord(BaseModel):
    """校准记录"""

    __tablename__ = "instrument_calibration_records"
    __table_args__ = (
        Index("idx_calibration_no", "calibration_no", unique=True),
        Index("idx_calibration_instrument", "instrument_id"),
        Index("idx_calibration_date", "calibration_date"),
        Index("idx_calibration_result", "calibration_result"),
        Index("idx_calibration_status", "status"),
        {"schema": "quality"},
    )

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("quality.instrument_calibrations.id"),
        nullable=False,
        comment="关联仪器ID",
    )
    rule_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, comment="关联校准规则ID")
    # 校准单据信息
    calibration_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, comment="校准单据编号")
    # 校准日期
    calibration_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="校准日期")
    calibration_end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="校准完成日期"
    )
    # 校准方式/机构/人员
    calibration_method: Mapped[str] = mapped_column(String(32), nullable=False, comment="校准方式")
    calibration_agency: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="校准机构")
    calibrator_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, comment="校准人员ID")
    calibrator_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="校准人员")
    # 校准证书
    certificate_no: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="校准证书编号")
    certificate_url: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="校准证书附件URL")
    # 校准结论
    calibration_result: Mapped[str] = mapped_column(String(32), nullable=False, comment="校准结论")
    result_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="结论说明")
    # 有效期
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="有效期起")
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="有效期至")
    # 计划信息
    is_scheduled: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False, comment="是否计划校准")
    scheduled_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="计划校准日期"
    )
    # 审核状态
    status: Mapped[str] = mapped_column(String(32), server_default="draft", nullable=False, comment="状态")
    # 备注
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # 关系
    instrument: Mapped["InstrumentCalibration"] = relationship(
        "InstrumentCalibration", back_populates="calibration_records"
    )


# ========== 审批记录表 ==========
class InstrumentCalibrationApproval(BaseModel):
    """审批记录"""

    __tablename__ = "instrument_calibration_approvals"
    __table_args__ = (
        Index("idx_approval_related", "related_type", "related_id"),
        Index("idx_approval_status", "status"),
        {"schema": "quality"},
    )

    # 关联类型
    related_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="关联类型")
    related_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, comment="关联ID")
    # 审批流程
    approval_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="审批类型")
    sequence: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False, comment="审批顺序")
    # 审批状态
    status: Mapped[str] = mapped_column(String(32), server_default="pending", nullable=False, comment="审批状态")
    approval_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="审批日期")
    comments: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审批意见")
    # 审批人
    approver_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, comment="审批人ID")
    approver_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="审批人")


# ========== 校准到期提醒配置表 ==========
class CalibrationReminderConfig(BaseModel):
    """校准到期提醒配置"""

    __tablename__ = "calibration_reminder_config"
    __table_args__ = (
        Index("idx_reminder_config_is_active", "is_active"),
        {"schema": "quality"},
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="配置名称")
    feishu_app_id: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="飞书应用AppID")
    feishu_app_secret: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="飞书应用AppSecret")
    chat_id: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="飞书群ID或用户ID")
    receive_id_type: Mapped[str] = mapped_column(
        String(20),
        server_default="chat_id",
        nullable=False,
        comment="接收类型: chat_id/user_id",
    )
    # 提醒开关
    remind_30_days: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False, comment="是否在30天前提醒"
    )
    remind_14_days: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False, comment="是否在14天前提醒"
    )
    remind_7_days: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False, comment="是否在7天前提醒"
    )
    remind_overdue: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False, comment="是否在超期后提醒"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False, comment="是否启用")
    # 上次提醒时间
    last_remind_30_days: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="上次30天提醒时间"
    )
    last_remind_14_days: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="上次14天提醒时间"
    )
    last_remind_7_days: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="上次7天提醒时间"
    )
    last_remind_overdue: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="上次超期提醒时间"
    )
