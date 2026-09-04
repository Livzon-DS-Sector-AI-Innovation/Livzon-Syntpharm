"""AI Parser Pydantic schemas for request/response models."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class LabConfirmationParsedData(BaseModel):
    """小试工艺确认解析数据结构"""

    temperature: str | None = Field(None, description="反应温度")
    pressure: str | None = Field(None, description="反应压力")
    time: str | None = Field(None, description="反应时间")
    yield_rate: float | None = Field(None, description="收率(%)")
    purity: float | None = Field(None, description="纯度(%)")
    solvent: str | None = Field(None, description="溶剂")
    catalyst: str | None = Field(None, description="催化剂")
    raw_materials: list[str] = Field(default_factory=list, description="原料列表")
    byproducts: list[str] = Field(default_factory=list, description="副产物列表")
    observations: str | None = Field(None, description="实验观察记录")


class ScaleUpParsedData(BaseModel):
    """放大生产解析数据结构"""

    batch_size: str | None = Field(None, description="批次规模")
    equipment: str | None = Field(None, description="使用设备")
    scale_factor: float | None = Field(None, description="放大倍数")
    process_parameters: dict[str, Any] = Field(default_factory=dict, description="工艺参数")
    quality_metrics: dict[str, Any] = Field(default_factory=dict, description="质量指标")
    deviations: list[str] = Field(default_factory=list, description="偏差记录")
    recommendations: list[str] = Field(default_factory=list, description="建议事项列表")


class DOEExperimentParsedData(BaseModel):
    """DOE实验解析数据结构"""

    factors: dict[str, Any] = Field(default_factory=dict, description="实验因子")
    responses: dict[str, Any] = Field(default_factory=dict, description="响应变量")
    design_type: str | None = Field(None, description="设计类型（如全因子、响应面等）")
    runs: int | None = Field(None, description="实验次数")
    optimal_conditions: dict[str, Any] = Field(default_factory=dict, description="最优条件")


class ImpurityParsedData(BaseModel):
    """杂质研究解析数据结构"""

    impurities: list[dict[str, Any]] = Field(default_factory=list, description="杂质列表")
    total_impurity: float | None = Field(None, description="总杂质(%)")
    identification_method: str | None = Field(None, description="鉴定方法")
    control_strategy: str | None = Field(None, description="控制策略")


class CrystalFormParsedData(BaseModel):
    """晶型研究解析数据结构"""

    crystal_forms: list[dict[str, Any]] = Field(default_factory=list, description="晶型列表")
    characterization_methods: list[str] = Field(default_factory=list, description="表征方法")
    stable_form: str | None = Field(None, description="稳定晶型")
    transition_temperature: str | None = Field(None, description="转变温度")


class RouteDesignParsedData(BaseModel):
    """路线设计解析数据结构"""

    steps: list[dict[str, Any]] = Field(default_factory=list, description="反应步骤")
    overall_yield: float | None = Field(None, description="总收率(%)")
    key_intermediates: list[str] = Field(default_factory=list, description="关键中间体")
    advantages: list[str] = Field(default_factory=list, description="路线优势")


class ExperimentParseRequest(BaseModel):
    """实验记录解析请求"""

    content: str = Field(..., min_length=1, max_length=50000, description="实验记录文本内容")
    parse_type: str = Field(..., description="解析类型")
    file_name: str | None = Field(None, description="原始文件名(可选)")

    @field_validator("parse_type")
    @classmethod
    def validate_parse_type(cls, v: str) -> str:
        valid_types = [
            "lab_confirmation",
            "scale_up",
            "doe_experiment",
            "impurity_analysis",
            "crystal_form_analysis",
            "route_design",
        ]
        if v not in valid_types:
            raise ValueError(f"parse_type必须是 {valid_types} 之一，当前值: {v}")
        return v


class ExperimentParseResponse(BaseModel):
    """实验记录解析响应"""

    parse_type: str = Field(..., description="解析类型")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度(0-1)")
    data: (
        LabConfirmationParsedData
        | ScaleUpParsedData
        | DOEExperimentParsedData
        | ImpurityParsedData
        | CrystalFormParsedData
        | RouteDesignParsedData
    ) = Field(..., description="解析出的结构化数据")
    warnings: list[str] = Field(default_factory=list, description="警告信息列表")
    raw_llm_output: dict[str, Any] | None = Field(None, description="LLM原始输出(调试用)")


class ParameterParseRequest(BaseModel):
    """工艺参数解析请求"""

    content: str = Field(..., min_length=1, max_length=30000, description="工艺参数文本内容")
    parse_type: str = Field(..., description="解析类型")

    @field_validator("parse_type")
    @classmethod
    def validate_parse_type(cls, v: str) -> str:
        valid_types = [
            "lab_confirmation",
            "scale_up",
            "doe_experiment",
            "impurity_analysis",
            "crystal_form_analysis",
            "route_design",
        ]
        if v not in valid_types:
            raise ValueError(f"parse_type必须是 {valid_types} 之一，当前值: {v}")
        return v


class ParameterParseResponse(BaseModel):
    """工艺参数解析响应"""

    parameters: dict[str, Any] = Field(default_factory=dict, description="提取的工艺参数")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度(0-1)")
    warnings: list[str] = Field(default_factory=list, description="警告信息列表")
