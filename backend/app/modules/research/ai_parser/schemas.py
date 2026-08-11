"""AI Parser schemas for experiment record parsing."""

from typing import Any

from pydantic import BaseModel, Field


class ExperimentParseRequest(BaseModel):
    """实验记录解析请求"""

    parse_type: str = Field(
        ..., description="解析类型: lab_confirmation 或 scale_up"
    )
    content: str | None = Field(None, description="文本内容")


class LabConfirmationParsedData(BaseModel):
    """小试工艺确认解析结果"""

    batch_no: str | None = Field(None, description="批号")
    scale_kg: float | None = Field(None, description="规模(kg)")
    date: str | None = Field(None, description="日期")
    operator: str | None = Field(None, description="操作人")
    process_parameters: dict[str, Any] | None = Field(
        None, description="工艺参数"
    )
    yield_rate: float | None = Field(None, description="收率(%)")
    purity: float | None = Field(None, description="纯度(%)")
    impurities: list[dict[str, Any]] | None = Field(None, description="杂质数据")
    appearance: str | None = Field(None, description="外观")
    conclusion: str | None = Field(None, description="结论")


class ScaleUpParsedData(BaseModel):
    """公斤级放大试验解析结果"""

    batch_no: str | None = Field(None, description="批号")
    target_scale_kg: float | None = Field(None, description="目标规模(kg)")
    actual_scale_kg: float | None = Field(None, description="实际规模(kg)")
    date: str | None = Field(None, description="日期")
    operator: str | None = Field(None, description="操作人")
    equipment: dict[str, Any] | None = Field(None, description="设备信息")
    material_balance: str | None = Field(None, description="物料衡算")
    yield_rate: float | None = Field(None, description="收率(%)")
    purity: float | None = Field(None, description="纯度(%)")
    key_indicators: dict[str, Any] | None = Field(None, description="关键指标")
    comparison_with_lab: str | None = Field(None, description="与小试对比")
    conclusion: str | None = Field(None, description="结论")


class ExperimentParseResponse(BaseModel):
    """实验记录解析响应"""

    parse_type: str = Field(..., description="解析类型")
    confidence: float = Field(..., description="置信度(0-1)")
    data: LabConfirmationParsedData | ScaleUpParsedData = Field(
        ..., description="解析数据"
    )
    raw_text: str | None = Field(None, description="原始文本")
    warnings: list[str] = Field(default_factory=list, description="警告信息")


class ParameterParseRequest(BaseModel):
    """工艺参数解析请求"""

    content: str = Field(..., description="文本内容")
    parse_type: str = Field(
        ..., description="解析类型: lab_confirmation 或 scale_up"
    )


class ParameterParseResponse(BaseModel):
    """工艺参数解析响应"""

    parameters: dict[str, Any] = Field(..., description="解析出的参数")
    confidence: float = Field(..., description="置信度(0-1)")
    warnings: list[str] = Field(default_factory=list, description="警告信息")
