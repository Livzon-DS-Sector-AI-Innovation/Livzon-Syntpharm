"""AI Parser service for experiment record parsing."""

import logging

from app.core.llm import llm_client
from app.core.llm.exceptions import LLMOutputError, LLMProviderError
from app.modules.research.ai_parser.schemas import (
    CrystalFormParsedData,
    DOEExperimentParsedData,
    ExperimentParseResponse,
    ImpurityParsedData,
    LabConfirmationParsedData,
    ParameterParseResponse,
    RouteDesignParsedData,
    ScaleUpParsedData,
)

logger = logging.getLogger(__name__)

# 不同解析类型的Prompt模板
PARSE_PROMPTS = {
    "lab_confirmation": """你是一个专业的制药工艺数据分析助手。请从小试工艺确认实验记录中提取关键信息。
请从以下文本中提取结构化数据:
{content}
要求:
1. 只提取明确提到的信息,不要推测
2. 返回 JSON 格式,包含 confidence (0-1), data (对象), warnings (数组)
3. data应包含: temperature, pressure, time, yield_rate, purity, solvent, catalyst等字段""",
    "scale_up": """你是一个专业的制药工艺放大数据分析助手。请从放大生产记录中提取关键信息。
请从以下文本中提取结构化数据:
{content}
要求:
1. 只提取明确提到的信息,不要推测
2. 返回 JSON 格式,包含 confidence (0-1), data (对象), warnings (数组)
3. data应包含: batch_size, equipment, scale_factor, process_parameters, quality_metrics等字段""",
    "doe_experiment": """你是一个专业的DOE实验数据分析助手。请从DOE实验记录中提取实验设计信息。
请从以下文本中提取结构化数据:
{content}
要求:
1. 只提取明确提到的信息,不要推测
2. 返回 JSON 格式,包含 confidence (0-1), data (对象), warnings (数组)
3. data应包含: factors(因子), responses(响应), design_type(设计类型), runs(实验次数), optimal_conditions(最优条件)""",
    "impurity_analysis": """你是一个专业的杂质研究数据分析助手。请从杂质分析报告或实验记录中提取杂质信息。
请从以下文本中提取结构化数据:
{content}
要求:
1. 只提取明确提到的信息,不要推测
2. 返回 JSON 格式,包含 confidence (0-1), data (对象), warnings (数组)
3. data应包含: impurities(杂质列表，每个杂质含name, amount, type等), total_impurity, identification_method, control_strategy""",
    "crystal_form_analysis": """你是一个专业的晶型研究数据分析助手。请从晶型表征报告或实验记录中提取晶型信息。
请从以下文本中提取结构化数据:
{content}
要求:
1. 只提取明确提到的信息,不要推测
2. 返回 JSON 格式,包含 confidence (0-1), data (对象), warnings (数组)
3. data应包含: crystal_forms(晶型列表), characterization_methods(表征方法), stable_form(稳定晶型), transition_temperature(转变温度)""",
    "route_design": """你是一个专业的合成路线设计分析助手。请从文献或实验记录中提取合成路线信息。
请从以下文本中提取结构化数据:
{content}
要求:
1. 只提取明确提到的信息,不要推测
2. 返回 JSON 格式,包含 confidence (0-1), data (对象), warnings (数组)
3. data应包含: steps(反应步骤列表), overall_yield(总收率), key_intermediates(关键中间体), advantages(路线优势)""",
}


async def parse_experiment_record(content: str, parse_type: str) -> ExperimentParseResponse:
    """解析实验记录文件内容"""
    valid_types = [
        "lab_confirmation",
        "scale_up",
        "doe_experiment",
        "impurity_analysis",
        "crystal_form_analysis",
        "route_design",
    ]
    if parse_type not in valid_types:
        raise ValueError(f"无效的解析类型: {parse_type}，必须是 {valid_types} 之一")

    prompt_template = PARSE_PROMPTS.get(parse_type, PARSE_PROMPTS["lab_confirmation"])
    prompt = prompt_template.format(content=content[:5000])

    try:
        messages = [
            {"role": "system", "content": "你是专业的制药工艺数据分析助手。"},
            {"role": "user", "content": prompt},
        ]
        result = await llm_client.chat_json(messages)

        confidence = result.get("confidence", 0.5)
        data = result.get("data", {})
        warnings = result.get("warnings", [])

        # 根据parse_type创建对应的数据模型
        data_models = {
            "lab_confirmation": LabConfirmationParsedData,
            "scale_up": ScaleUpParsedData,
            "doe_experiment": DOEExperimentParsedData,
            "impurity_analysis": ImpurityParsedData,
            "crystal_form_analysis": CrystalFormParsedData,
            "route_design": RouteDesignParsedData,
        }

        model_class = data_models.get(parse_type, LabConfirmationParsedData)
        parsed_data = model_class(**data)

        return ExperimentParseResponse(
            parse_type=parse_type, confidence=confidence, data=parsed_data, warnings=warnings
        )
    except (LLMProviderError, LLMOutputError) as e:
        logger.error(f"LLM 解析失败: {e}")
        raise
    except Exception as e:
        logger.error(f"实验记录解析异常: {e}")
        raise


async def parse_process_parameters(content: str, parse_type: str) -> ParameterParseResponse:
    """解析工艺参数文本"""
    valid_types = [
        "lab_confirmation",
        "scale_up",
        "doe_experiment",
        "impurity_analysis",
        "crystal_form_analysis",
        "route_design",
    ]
    if parse_type not in valid_types:
        raise ValueError(f"无效的解析类型: {parse_type}")

    prompt = f"请从以下文本中提取{parse_type}相关的工艺参数: {content[:3000]}。返回 JSON: {{parameters: {{}}, confidence: 0-1, warnings: []}}"

    try:
        messages = [{"role": "user", "content": prompt}]
        result = await llm_client.chat_json(messages)
        return ParameterParseResponse(
            parameters=result.get("parameters", {}),
            confidence=result.get("confidence", 0.5),
            warnings=result.get("warnings", []),
        )
    except Exception as e:
        logger.error(f"工艺参数解析失败: {e}")
        raise
