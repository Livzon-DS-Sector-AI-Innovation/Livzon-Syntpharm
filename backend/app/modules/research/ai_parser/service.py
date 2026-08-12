"""AI Parser service for experiment record parsing."""

import logging

from app.core.llm import llm_client
from app.modules.research.ai_parser.schemas import (
    ExperimentParseResponse,
    LabConfirmationParsedData,
    ParameterParseResponse,
    ScaleUpParsedData,
)

logger = logging.getLogger(__name__)


# LLM Prompt for experiment record parsing
EXPERIMENT_PARSE_PROMPT = """你是一个专业的制药工艺数据分析助手。请从实验记录中提取关键信息。

解析类型: {parse_type}

请从以下实验记录文本中提取结构化数据:

{content}

要求:
1. 只提取明确提到的信息,不要推测
2. 对于数值,保留原始精度
3. 如果某项信息不存在,返回 null
4. 给出置信度评分(0-1),基于信息的完整性和清晰度

返回JSON格式,包含以下字段:
- confidence: 置信度(0-1)
- data: 解析出的数据对象
- warnings: 警告信息列表(如信息不完整、矛盾等)

对于 lab_confirmation 类型,data 包含:
- batch_no: 批号
- scale_kg: 规模(kg)
- date: 日期
- operator: 操作人
- process_parameters: 工艺参数对象
- yield_rate: 收率(%)
- purity: 纯度(%)
- impurities: 杂质数据数组
- appearance: 外观
- conclusion: 结论

对于 scale_up 类型,data 包含:
- batch_no: 批号
- target_scale_kg: 目标规模(kg)
- actual_scale_kg: 实际规模(kg)
- date: 日期
- operator: 操作人
- equipment: 设备信息对象
- material_balance: 物料衡算
- yield_rate: 收率(%)
- purity: 纯度(%)
- key_indicators: 关键指标对象
- comparison_with_lab: 与小试对比
- conclusion: 结论
"""

PARAMETER_PARSE_PROMPT = """你是一个专业的制药工艺参数分析助手。请从文本中提取工艺参数。

请从以下文本中提取所有工艺参数:

{content}

要求:
1. 提取所有明确的工艺参数(温度、压力、时间、转速、pH等)
2. 保持参数的单位和精度
3. 如果参数有范围,保留范围信息
4. 给出置信度评分(0-1)

返回JSON格式:
{{
  "parameters": {{
    "parameter_name": {{
      "value": "值",
      "unit": "单位",
      "range": "范围(如果有)"
    }}
  }},
  "confidence": 0.95,
  "warnings": []
}}
"""


async def parse_experiment_record(content: str, parse_type: str) -> ExperimentParseResponse:
    """解析实验记录文件内容

    Args:
        content: 实验记录文本内容
        parse_type: 解析类型 (lab_confirmation 或 scale_up)

    Returns:
        ExperimentParseResponse: 解析结果

    Raises:
        ValueError: 解析类型无效
        Exception: LLM调用失败
    """
    if parse_type not in ["lab_confirmation", "scale_up"]:
        raise ValueError(f"无效的解析类型: {parse_type}")

    prompt = EXPERIMENT_PARSE_PROMPT.format(
        parse_type=parse_type,
        content=content[:5000],  # 限制长度
    )

    try:
        messages = [
            {"role": "system", "content": "你是专业的制药工艺数据分析助手。"},
            {"role": "user", "content": prompt},
        ]

        result = await llm_client.chat_json(messages)

        # 验证和构建响应
        confidence = result.get("confidence", 0.5)
        data = result.get("data", {})
        warnings = result.get("warnings", [])

        parsed_data: LabConfirmationParsedData | ScaleUpParsedData
        if parse_type == "lab_confirmation":
            parsed_data = LabConfirmationParsedData(**data)
        else:
            parsed_data = ScaleUpParsedData(**data)

        return ExperimentParseResponse(
            parse_type=parse_type,
            confidence=confidence,
            data=parsed_data,
            raw_text=content[:500],  # 保留部分原始文本
            warnings=warnings,
        )

    except Exception as e:
        logger.error(f"实验记录解析失败: {e}")
        raise


async def parse_process_parameters(content: str, parse_type: str) -> ParameterParseResponse:
    """解析工艺参数文本

    Args:
        content: 包含工艺参数的文本
        parse_type: 解析类型 (lab_confirmation 或 scale_up)

    Returns:
        ParameterParseResponse: 解析结果

    Raises:
        Exception: LLM调用失败
    """
    prompt = PARAMETER_PARSE_PROMPT.format(content=content[:3000])

    try:
        messages = [
            {"role": "system", "content": "你是专业的制药工艺参数分析助手。"},
            {"role": "user", "content": prompt},
        ]

        result = await llm_client.chat_json(messages)

        parameters = result.get("parameters", {})
        confidence = result.get("confidence", 0.5)
        warnings = result.get("warnings", [])

        return ParameterParseResponse(
            parameters=parameters,
            confidence=confidence,
            warnings=warnings,
        )

    except Exception as e:
        logger.error(f"工艺参数解析失败: {e}")
        raise
