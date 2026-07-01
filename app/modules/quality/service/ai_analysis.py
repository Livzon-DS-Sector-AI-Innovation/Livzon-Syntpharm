from __future__ import annotations

"""AI analysis service for deviation management."""

import logging
import uuid
from datetime import UTC, datetime

from app.core.llm import llm_client
from app.modules.quality.models.deviations import Deviation

logger = logging.getLogger(__name__)

# AI analysis prompt template
DEVIATION_ANALYSIS_PROMPT = """你是一位专业的制药质量管理专家，具有丰富的GMP偏差管理经验。
请对以下偏差进行专业分析，并以JSON格式返回结果。

偏差信息：
- 标题：{title}
- 部门：{department}
- 发现时间：{discovery_time}
- 发现地点：{discovery_location}
- 偏差描述：{description}
- 立即措施：{immediate_actions}

请分析并返回以下JSON结构（必须严格遵循此格式）：
{{
    "structured_deviation_description": "结构化的偏差描述，包含时间、地点、事件、影响范围等要素，要求清晰完整",
    "preliminary_cause_analysis": "初步原因分析，从人、机、料、法、环、测六个维度进行分析，指出可能的根本原因",
    "risk_assessment": "风险评估，包括对产品质量、患者安全、数据完整性、合规性等方面的影响评估，以及建议的风险等级",
    "capa_suggestions": "纠正和预防措施建议，包括立即纠正措施、长期预防措施、验证要求等"
}}

要求：
1. 使用专业的质量管理术语
2. 分析要具体、有针对性，避免空泛
3. 风险评估要基于实际影响
4. CAPA建议要可执行、可验证
5. 只返回JSON，不要其他内容
"""


async def analyze_deviation_async(deviation_id: uuid.UUID, user_id: str):
    """
    Asynchronously analyze a deviation using AI.
    This function is called in the background after deviation submission.
    """
    from app.core.database import async_session_factory
    from app.modules.quality.models import Deviation

    try:
        async with async_session_factory() as db:
            # Fetch deviation
            deviation = await db.get(Deviation, deviation_id)
            if not deviation or deviation.is_deleted:
                logger.warning(f"Deviation {deviation_id} not found for AI analysis")
                return

            # Build prompt
            prompt = DEVIATION_ANALYSIS_PROMPT.format(
                title=deviation.title or "",
                department=deviation.department or "",
                discovery_time=deviation.discovery_time or "",
                discovery_location=deviation.discovery_location or "",
                description=deviation.description or "",
                immediate_actions=deviation.immediate_actions or "",
            )

            # Call LLM
            # LLM config is global
            result = await llm_client.chat_json([{"role": "user", "content": prompt}])

            # Parse and save result
            if isinstance(result, dict):
                deviation.ai_analysis = result
                deviation.status = "pending_investigation"
                deviation.status_updated_at = datetime.now(UTC)
                deviation.updated_by = (
                    uuid.UUID(user_id) if user_id != "system" else None
                )
                await db.commit()
                logger.info(f"AI analysis completed for deviation {deviation_id}")
            else:
                logger.error(
                    f"AI analysis returned invalid format for deviation {deviation_id}: {type(result)}"
                )

    except Exception as e:
        logger.error(
            f"AI analysis failed for deviation {deviation_id}: {e}", exc_info=True
        )


async def analyze_deviation_sync(deviation: Deviation) -> dict | None:
    """
    Synchronously analyze a deviation using AI.
    Returns the analysis result or None if failed.
    """
    try:
        # Build prompt
        prompt = DEVIATION_ANALYSIS_PROMPT.format(
            title=deviation.title or "",
            department=deviation.department or "",
            discovery_time=deviation.discovery_time or "",
            discovery_location=deviation.discovery_location or "",
            description=deviation.description or "",
            immediate_actions=deviation.immediate_actions or "",
        )

        # Call LLM
        # LLM config is global
        result = await llm_client.chat_json([{"role": "user", "content": prompt}])

        if isinstance(result, dict):
            return result
        else:
            logger.error(f"AI analysis returned invalid format: {type(result)}")
            return None

    except Exception as e:
        logger.error(f"AI analysis failed: {e}", exc_info=True)
        return None
