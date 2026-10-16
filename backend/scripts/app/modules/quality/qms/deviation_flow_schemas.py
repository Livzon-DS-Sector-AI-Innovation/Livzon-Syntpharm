"""偏差流程管理 Schemas"""

from pydantic import BaseModel, Field


class DeviationCreateRequest(BaseModel):
    """创建偏差请求"""

    theme: str | None = Field(None, description="偏差主题")
    occurred_date: str | None = Field(None, description="偏差发生日期")
    discovered_date: str | None = Field(None, description="发现日期")
    responsible_department: str | None = Field(None, description="责任部门")
    occurred_area: str | None = Field(None, description="发生区域/车间")
    deviation_type: str | None = Field(None, description="偏差类型")
    urgency_level: str | None = Field(None, description="紧急等级")

    product_name: str | None = Field(None, description="涉及产品/物料")
    batch_no: str | None = Field(None, description="批次号")
    equipment: str | None = Field(None, description="涉及设备/仪器")
    standard_based_on: str | None = Field(None, description="偏离标准依据")
    deviation_description: str | None = Field(None, description="偏差完整经过描述")
    risk_assessment: str | None = Field(None, description="初步风险影响评估")

    temp_measures: str | None = Field(None, description="临时处置措施")
    related_deviation_no: str | None = Field(None, description="关联偏差单号")
    related_capa: str | None = Field(None, description="关联CAPA")
    remarks: str | None = Field(None, description="备注说明")

    qa_feishu_open_id: str | None = Field(None, description="QA人员飞书OpenID")
    qa_feishu_name: str | None = Field(None, description="QA人员姓名")
    dept_leader_feishu_open_id: str | None = Field(None, description="部门负责人飞书OpenID")
    dept_leader_feishu_name: str | None = Field(None, description="部门负责人姓名")

    reporter: str | None = Field(None, description="填报人")
    reporter_department: str | None = Field(None, description="填报部门")
    reporter_feishu_open_id: str | None = Field(None, description="填报人飞书OpenID")


class DeviationUpdateRequest(BaseModel):
    """更新偏差请求"""

    theme: str | None = None
    occurred_date: str | None = None
    discovered_date: str | None = None
    responsible_department: str | None = None
    occurred_area: str | None = None
    deviation_type: str | None = None
    urgency_level: str | None = None

    product_name: str | None = None
    batch_no: str | None = None
    equipment: str | None = None
    standard_based_on: str | None = None
    deviation_description: str | None = None
    risk_assessment: str | None = None

    temp_measures: str | None = None
    related_deviation_no: str | None = None
    related_capa: str | None = None
    remarks: str | None = None

    qa_feishu_open_id: str | None = None
    qa_feishu_name: str | None = None
    dept_leader_feishu_open_id: str | None = None
    dept_leader_feishu_name: str | None = None
    reporter: str | None = None
    reporter_department: str | None = None
    reporter_feishu_open_id: str | None = None


class DeviationSubmitRequest(BaseModel):
    """提交偏差请求"""

    deviation_id: str = Field(..., description="偏差ID")
    target_status: str = Field(..., description="目标状态: basic_completed/detail_completed/completed")


class AttachmentResponse(BaseModel):
    """附件响应"""

    id: str
    deviation_id: str
    file_name: str
    file_path: str
    file_type: str | None
    is_report: bool
    file_size: int | None
    uploaded_by: str | None
    uploaded_at: str


class DeviationResponse(BaseModel):
    """偏差响应"""

    id: str
    deviation_no: str
    theme: str
    occurred_date: str
    discovered_date: str
    responsible_department: str | None
    occurred_area: str | None
    deviation_type: str | None
    deviation_type_label: str | None
    urgency_level: str | None
    urgency_level_label: str | None
    status: str
    status_label: str

    product_name: str | None
    batch_no: str | None
    equipment: str | None
    standard_based_on: str | None
    deviation_description: str | None
    risk_assessment: str | None

    temp_measures: str | None
    related_deviation_no: str | None
    related_capa: str | None
    remarks: str | None

    qa_feishu_open_id: str | None
    qa_feishu_name: str | None
    dept_leader_feishu_open_id: str | None
    dept_leader_feishu_name: str | None

    reporter: str | None
    reporter_department: str | None
    report_time: str | None

    attachments: list[AttachmentResponse]

    created_at: str
    updated_at: str | None
