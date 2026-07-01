"""AI 分析服务 - 原料药企业法规影响评估 V6。"""

import asyncio
import logging
import re
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import LLMError, llm_client
from app.modules.regulatory_tracker import repository as repo
from app.modules.regulatory_tracker.knowledge import (
    build_prompt_summary,
)
from app.modules.regulatory_tracker.models.regulatory_document import RegulatoryDocument
from app.modules.regulatory_tracker.services.classification_service import (
    compute_document_category,
)

# 导入 identity model 以解决外键引用问题
from app.platform.identity.models import User  # noqa: F401

logger = logging.getLogger(__name__)


# 影响等级阈值定义
IMPACT_THRESHOLDS = {
    "high": (0.80, 1.00),
    "medium": (0.50, 0.79),
    "low": (0.20, 0.49),
    "none": (0.00, 0.19),
}

# 有效的企业相关性等级
VALID_RELEVANCE_LEVELS = {"related", "weak_related", "unrelated"}

# 有效的生命周期环节（固定 10 个）
VALID_LIFECYCLE_AREAS = [
    "药品研发",
    "工艺开发",
    "分析方法",
    "质量标准",
    "稳定性研究",
    "生产管理",
    "GMP管理",
    "注册申报",
    "变更管理",
    "上市后维护",
]

# 有效的影响部门（固定候选 7 个）
VALID_DEPARTMENTS = ["注册", "QA", "QC", "研发", "生产", "验证", "供应链"]

# 有效的 CTD 章节（固定候选 7 个）
VALID_CTD_SECTIONS = [
    "3.2.S.1",
    "3.2.S.2",
    "3.2.S.3",
    "3.2.S.4",
    "3.2.S.5",
    "3.2.S.6",
    "3.2.S.7",
]

# 评估型表达动词（建议行动必须包含其中之一）
ASSESSMENT_VERBS = [
    "评估",
    "核查",
    "组织",
    "关注",
    "审视",
    "审查",
    "梳理",
    "排查",
    "确认",
    "研判",
]

# 禁止的命令式表达
FORBIDDEN_PATTERNS = [
    r"^立即",
    r"^必须",
    r"^应当立即",
    r"^请.*执行",
    r"^启动",
    r"^落实",
    r"^确保",
    r"^通知.*执行",
    r"^更新(?!是否需要)",
    r"^修改(?!是否)",
    r"^制定(?!是否需要)",
]

# 最大重试次数
MAX_RETRY_ATTEMPTS = 3


def score_to_impact_level(score: float) -> str:
    """将影响评分转换为影响等级。"""
    if score >= 0.80:
        return "high"
    elif score >= 0.50:
        return "medium"
    elif score >= 0.20:
        return "low"
    else:
        return "none"


def impact_level_to_relevance(impact_level: str) -> str:
    """根据影响等级推导企业相关性（旧数据兼容 fallback）。"""
    if impact_level in ("high", "medium"):
        return "related"
    elif impact_level == "low":
        return "weak_related"
    else:
        return "unrelated"


def impact_level_to_focus_required(impact_level: str) -> bool:
    """根据影响等级推导是否建议重点关注（旧数据兼容 fallback）。"""
    return impact_level == "high"


def impact_level_to_archive_recommended(impact_level: str) -> bool:
    """根据影响等级推导是否建议归档（旧数据兼容 fallback）。"""
    return impact_level in ("none", "low")


def _action_is_assessment_style(action: str) -> bool:
    """检查建议行动是否为评估型表达。"""
    if not action or not isinstance(action, str):
        return False
    return any(verb in action for verb in ASSESSMENT_VERBS)


def _rewrite_action_to_assessment(action: str) -> str:
    """将命令式表达改写为评估型表达。"""
    if not action or not isinstance(action, str):
        return action

    # 如果已经是评估型，直接返回
    if _action_is_assessment_style(action):
        return action

    # 尝试改写
    rewritten = action

    # "立即更新..." → "评估是否需要更新..."
    rewritten = re.sub(r"^立即\s*", "评估是否需要", rewritten)
    # "必须修改..." → "评估是否需要修改..."
    rewritten = re.sub(r"^必须\s*", "评估是否需要", rewritten)
    # "启动变更控制" → "评估是否需要启动变更控制"
    rewritten = re.sub(r"^启动\s*", "评估是否需要启动", rewritten)
    # "更新..." → "评估是否需要更新..."
    rewritten = re.sub(r"^更新\s*", "评估是否需要更新", rewritten)
    # "修改..." → "评估是否需要修改..."
    rewritten = re.sub(r"^修改\s*", "评估是否需要修改", rewritten)
    # "通知..." → "评估是否需要通知..."
    rewritten = re.sub(r"^通知\s*", "评估是否需要通知", rewritten)
    # "落实..." → "评估如何落实..."
    rewritten = re.sub(r"^落实\s*", "评估如何落实", rewritten)
    # "确保..." → "评估如何确保..."
    rewritten = re.sub(r"^确保\s*", "评估如何确保", rewritten)
    # "制定..." → "评估是否需要制定..."
    rewritten = re.sub(r"^制定\s*", "评估是否需要制定", rewritten)

    # 如果改写后仍然不是评估型，添加前缀
    if not _action_is_assessment_style(rewritten):
        rewritten = f"评估是否需要：{action}"

    return rewritten


def build_analysis_prompt(document: RegulatoryDocument) -> list[dict]:
    """构建原料药企业法规影响评估 Prompt。"""
    title = document.title or ""
    classification = document.classification or "未知"
    status_text = document.status_text or "未知"

    # 从 raw_data 提取更多信息
    raw_data = document.raw_data or {}
    content_summary = raw_data.get("contentSummary", "") or raw_data.get("summary", "")
    detail_text = raw_data.get("detail_text", "") or ""

    # 组合正文内容（限制长度）
    content_text = detail_text[:3000] if detail_text else content_summary[:1500]

    # 从知识库获取规则摘要
    rules_summary = build_prompt_summary()

    prompt = f"""你是一名服务于原料药生产企业的法规事务、质量保证、GMP 和注册申报专家。请分析以下法规文档，评估其对原料药企业的影响。

## 文档信息
- 标题: {title}
- 分类: {classification}
- 状态: {status_text}
- 内容: {content_text if content_text else "无详细内容"}

## 判定流程（必须严格按以下步骤执行）

**第一步：识别法规主要对象**
判断法规主要规范的是谁：
- 原料药/API → 进入"直接相关"路径
- 制剂/成品 → 进入"间接相关"路径
- 通用要求 → 进入"通用适用"路径
- 非药品领域（医疗器械、化妆品等）→ 进入"无关"路径

**第二步：匹配默认等级**
根据以下规则查找默认影响等级：

{rules_summary}

**第三步：检查升级条件**
对于默认 low/none 的法规，检查正文是否包含升级条件中的关键词。
如果包含，按升级条件调整影响等级和相关性。

**第四步：检查降级条件**
对于默认 high/medium 的法规，检查是否满足降级条件（如征求意见稿、明确不适用于化学原料药等）。
如果满足，按降级条件调整影响等级。

**第五步：输出最终判断**
根据以上步骤，输出以下字段。

## 影响等级判断规则

**提高影响等级的情况：**
- 涉及原料药（API）
- 涉及药品注册、CTD 资料
- 涉及药学研究、质量研究
- 涉及稳定性研究
- 涉及 GMP、生产管理
- 涉及变更控制
- 指导原则、法规、公告
- ICH 指导原则
- 药典标准

**降低影响等级的情况：**
- 会议新闻、培训通知
- 一般动态、行业资讯
- 与原料药无直接关联
- 仅涉及制剂、临床试验（非原料药相关）

**影响评分标准（0-1）：**
- 0.80-1.00：high，高影响，需要立即评估
- 0.50-0.79：medium，中影响，建议关注并评估
- 0.20-0.49：low，低影响，归档关注
- 0.00-0.19：none，暂无明显影响

## 企业相关性判断

- `related`：与原料药企业直接相关（涉及 API 质量、注册、GMP、杂质、稳定性、工艺等）
- `weak_related`：间接相关或可能相关（涉及制剂但可能影响原料药供应商、涉及通用 GMP 要求等）
- `unrelated`：与原料药企业无关（临床试验、药品广告管理、中药材种植等）

## 分流建议判断

- `focus_required`：是否建议列入重点关注。high 影响通常为 true，medium 视情况，low/none 为 false
- `archive_recommended`：是否建议归入法规档案。low/none 影响通常为 true，high/medium 为 false
- `notification_required`：是否建议通知相关部门。high/medium 影响通常为 true

## 建议行动措辞要求

**极其重要：** 你给出的建议行动必须使用"评估型表达"，因为你是决策支持，不是最终决策者。最终决策由注册经理和相关部门做出。

**必须使用的动词：** 评估、核查、组织评估、关注、审视、审查、梳理、排查、确认、研判

**正确示例：**
- "评估是否需要更新质量标准"
- "核查现有分析方法是否覆盖新要求"
- "组织 RA/QA/QC 评估影响"
- "评估是否影响 CTD 3.2.S 章节"
- "评估是否需要启动变更控制"

**错误示例（禁止使用）：**
- "立即更新质量标准"
- "必须修改 CTD"
- "启动变更控制"
- "通知所有部门执行"
- "更新注册资料"

每条建议行动都必须包含评估型动词。

## 影响环节数量约束

- high/medium 影响：可以详细列出所有受影响的环节
- low 影响：最多列出 2-3 个最相关的受影响环节
- none 影响：所有环节均为 affected=false

## 输出格式

请严格按以下 JSON 格式返回，不要包含其他内容：

{{
  "executive_summary": "一句话结论，100字以内",
  "regulation_type": "法规类型（指导原则/法规/公告/征求意见稿/通知/药典增补/问答函/检查通知/其他）",
  "impact_score": 0.85,
  "impact_level": "high|medium|low|none",
  "relevance_level": "related|weak_related|unrelated",
  "lifecycle_impacts": [
    {{
      "area": "药品研发",
      "affected": true,
      "reason": "具体原因说明"
    }}
  ],
  "departments": ["注册", "QA", "QC", "研发"],
  "ctd_sections": ["3.2.S.3", "3.2.S.4"],
  "recommended_actions": [
    "评估是否需要...",
    "核查现有...是否受影响",
    "组织...评估影响"
  ],
  "focus_required": true,
  "archive_recommended": false,
  "notification_required": true,
  "confidence": 0.85,
  "evidence": ["关键词1", "关键词2", "关键词3"],
  "evidence_excerpts": ["从法规原文中提取的依据片段1"]
}}

**字段说明：**
- `executive_summary`: 一句话结论，100 字以内
- `regulation_type`: 法规类型
- `impact_score`: 影响评分（0-1）
- `impact_level`: 影响等级（high/medium/low/none），与 impact_score 对应
- `relevance_level`: 企业相关性（related/weak_related/unrelated）
- `lifecycle_impacts`: 10 个生命周期环节的影响评估。必须包含全部 10 个环节。low 影响最多 2-3 个 affected=true，none 影响全部 affected=false
- `departments`: 需要关注的部门列表（从：注册、QA、QC、研发、生产、验证、供应链 中选择）。low 影响最多 2-3 个，none 影响为空数组
- `ctd_sections`: 可能影响的 CTD 章节（从：3.2.S.1~3.2.S.7 中选择）。无明确依据时为空数组
- `recommended_actions`: 建议行动（2-5 条），**必须使用评估型表达**
- `focus_required`: 是否建议重点关注（boolean）
- `archive_recommended`: 是否建议归入法规档案（boolean）
- `notification_required`: 是否建议通知相关部门（boolean）
- `confidence`: AI 对该评估的置信度（0-1）
- `evidence`: 判断依据关键词（3-5 个）
- `evidence_excerpts`: 从法规原文中直接提取的依据片段（1-3 条），无法提取则为空数组

**注意事项：**
- 只返回 JSON，不要有其他文字
- lifecycle_impacts 必须包含全部 10 个环节
- recommended_actions 必须使用评估型表达
- none 影响的法规：departments=[]、ctd_sections=[]、lifecycle_impacts 全部 affected=false"""

    return [
        {
            "role": "system",
            "content": "你是专业的药品注册和 GMP 合规专家，专注于化学原料药领域的法规分析。你的分析必须严谨、准确，基于法规原文内容。你提供的是评估建议，不是最终决策。",
        },
        {"role": "user", "content": prompt},
    ]


def validate_impact_result(result: dict) -> dict:
    """验证和规范化影响评估结果，包含规则兜底逻辑。"""

    # ===== 基础字段验证 =====

    # 验证 impact_level
    valid_levels = {"high", "medium", "low", "none"}
    if result.get("impact_level") not in valid_levels:
        result["impact_level"] = "low"

    # 验证 impact_score
    try:
        score = float(result.get("impact_score", 0.5))
        result["impact_score"] = max(0.0, min(1.0, score))
    except (ValueError, TypeError):
        result["impact_score"] = 0.5

    # 确保 impact_level 与 impact_score 一致
    expected_level = score_to_impact_level(result["impact_score"])
    if result["impact_level"] != expected_level:
        logger.warning(
            f"Impact level mismatch: score={result['impact_score']}, level={result['impact_level']}, expected={expected_level}"
        )
        result["impact_level"] = expected_level

    # 验证 relevance_level（带 fallback）
    relevance = result.get("relevance_level")
    if relevance not in VALID_RELEVANCE_LEVELS:
        result["relevance_level"] = impact_level_to_relevance(result["impact_level"])

    # 验证 lifecycle_impacts
    if not isinstance(result.get("lifecycle_impacts"), list):
        result["lifecycle_impacts"] = []
    else:
        for item in result["lifecycle_impacts"]:
            if not isinstance(item, dict):
                continue
            if "area" not in item:
                item["area"] = ""
            if "affected" not in item:
                item["affected"] = False
            if "reason" not in item:
                item["reason"] = ""

    # 过滤数组字段
    array_fields = [
        "departments",
        "ctd_sections",
        "recommended_actions",
        "evidence",
        "evidence_excerpts",
    ]
    for field in array_fields:
        if not isinstance(result.get(field), list):
            result[field] = []

    # 过滤 departments 为有效值
    result["departments"] = [d for d in result["departments"] if d in VALID_DEPARTMENTS]

    # 过滤 ctd_sections 为有效值
    result["ctd_sections"] = [
        c for c in result["ctd_sections"] if c in VALID_CTD_SECTIONS
    ]

    # 验证 confidence
    try:
        confidence = float(result.get("confidence", 0.5))
        result["confidence"] = max(0.0, min(1.0, confidence))
    except (ValueError, TypeError):
        result["confidence"] = 0.5

    # 确保字符串字段
    for field in ["executive_summary", "regulation_type"]:
        if not isinstance(result.get(field), str):
            result[field] = ""

    # 确保 evidence_excerpts 是字符串数组
    result["evidence_excerpts"] = [
        e for e in result["evidence_excerpts"] if isinstance(e, str)
    ]

    # ===== 规则兜底逻辑 =====

    impact_level = result["impact_level"]

    # --- none / unrelated 法规兜底 ---
    if impact_level == "none":
        result["relevance_level"] = "unrelated"
        result["focus_required"] = False
        result["archive_recommended"] = True
        result["notification_required"] = False
        result["departments"] = []
        result["ctd_sections"] = []
        # 所有 lifecycle_impacts 设为 false
        for item in result["lifecycle_impacts"]:
            if isinstance(item, dict):
                item["affected"] = False
                item["reason"] = ""
        # 只保留 1 条归档建议
        if not result["recommended_actions"] or not _action_is_assessment_style(
            result["recommended_actions"][0]
        ):
            result["recommended_actions"] = ["与原料药企业无关，归档留存"]
        else:
            result["recommended_actions"] = result["recommended_actions"][:1]

    # --- low / weak_related 法规兜底 ---
    elif impact_level == "low":
        if result["relevance_level"] == "unrelated":
            result["relevance_level"] = "weak_related"
        result["focus_required"] = False
        result["archive_recommended"] = True
        result["notification_required"] = False
        # 限制影响环节数量：最多 3 个 affected=true
        affected_count = 0
        for item in result["lifecycle_impacts"]:
            if isinstance(item, dict) and item.get("affected"):
                affected_count += 1
                if affected_count > 3:
                    item["affected"] = False
                    item["reason"] = ""
        # 限制部门数量：最多 3 个
        result["departments"] = result["departments"][:3]
        # 无明确依据时清空 CTD 章节
        if not result.get("evidence") or len(result["evidence"]) < 2:
            result["ctd_sections"] = []

    # --- high 法规兜底 ---
    elif impact_level == "high":
        result["relevance_level"] = "related"
        result["focus_required"] = True
        result["archive_recommended"] = False

    # --- medium 法规兜底 ---
    elif impact_level == "medium":
        if result["relevance_level"] == "unrelated":
            result["relevance_level"] = "related"
        result["focus_required"] = False
        result["archive_recommended"] = False

    # ===== 建议行动措辞校验 =====
    actions = result.get("recommended_actions", [])
    cleaned_actions = []
    for action in actions:
        if isinstance(action, str) and action.strip():
            if not _action_is_assessment_style(action):
                action = _rewrite_action_to_assessment(action)
            cleaned_actions.append(action)
    result["recommended_actions"] = cleaned_actions

    # ===== 最终 focus_required / archive_recommended 兜底 =====
    if not isinstance(result.get("focus_required"), bool):
        result["focus_required"] = impact_level_to_focus_required(impact_level)
    if not isinstance(result.get("archive_recommended"), bool):
        result["archive_recommended"] = impact_level_to_archive_recommended(
            impact_level
        )
    if not isinstance(result.get("notification_required"), bool):
        result["notification_required"] = impact_level in ("high", "medium")

    return result


async def analyze_document(document: RegulatoryDocument) -> dict[str, Any]:
    """使用 AI 分析单个文档的原料药企业影响。"""
    messages = build_analysis_prompt(document)

    try:
        result = await llm_client.chat_json(
            messages,
            expected_keys=["executive_summary", "impact_score", "impact_level"],
        )

        # 验证和规范化结果
        result = validate_impact_result(result)

        return {
            "executive_summary": result.get("executive_summary", ""),
            "regulation_type": result.get("regulation_type", ""),
            "impact_score": result.get("impact_score", 0.5),
            "impact_level": result.get("impact_level", "low"),
            "relevance_level": result.get("relevance_level", "weak_related"),
            "lifecycle_impacts": result.get("lifecycle_impacts", []),
            "departments": result.get("departments", []),
            "ctd_sections": result.get("ctd_sections", []),
            "recommended_actions": result.get("recommended_actions", []),
            "focus_required": result.get("focus_required", False),
            "archive_recommended": result.get("archive_recommended", False),
            "notification_required": result.get("notification_required", False),
            "confidence": result.get("confidence", 0.5),
            "evidence": result.get("evidence", []),
            "evidence_excerpts": result.get("evidence_excerpts", []),
            "status": "completed",
        }

    except LLMError as e:
        logger.error(f"AI 分析文档失败 [{document.document_id}]: {e}")
        return {
            "executive_summary": None,
            "regulation_type": None,
            "impact_score": None,
            "impact_level": None,
            "relevance_level": None,
            "lifecycle_impacts": None,
            "departments": None,
            "ctd_sections": None,
            "recommended_actions": None,
            "focus_required": None,
            "archive_recommended": None,
            "notification_required": None,
            "confidence": None,
            "evidence": None,
            "evidence_excerpts": None,
            "status": "failed",
            "error": str(e),
        }
    except Exception as e:
        logger.error(f"AI 分析文档异常 [{document.document_id}]: {e}")
        return {
            "executive_summary": None,
            "regulation_type": None,
            "impact_score": None,
            "impact_level": None,
            "relevance_level": None,
            "lifecycle_impacts": None,
            "departments": None,
            "ctd_sections": None,
            "recommended_actions": None,
            "focus_required": None,
            "archive_recommended": None,
            "notification_required": None,
            "confidence": None,
            "evidence": None,
            "evidence_excerpts": None,
            "status": "failed",
            "error": str(e),
        }


async def analyze_and_update(
    db: AsyncSession,
    document: RegulatoryDocument,
    force: bool = False,
) -> bool:
    """分析文档并更新数据库（自动工作流）。

    Args:
        db: 数据库会话
        document: 待分析的文档
        force: 是否强制重新分析（忽略缓存）

    Returns:
        是否成功
    """
    doc_id = str(document.id)[:8]
    doc_title = document.title[:50]

    start_time = time.time()

    # ===== 防重复调用检查 =====
    if not force and document.ai_analysis_status == "completed":
        logger.info(f"[{doc_id}] 法规已分析，跳过: {doc_title}")
        return True

    if not force and document.ai_analysis_status == "pending":
        logger.info(f"[{doc_id}] 法规正在分析中，跳过: {doc_title}")
        return True

    # ===== 标记为分析中 =====
    logger.info(f"[{doc_id}] AI 分析开始: {doc_title}")
    await repo.update_document(
        db,
        document.id,
        {
            "ai_analysis_status": "pending",
        },
    )
    await db.commit()

    # ===== 执行 AI 分析（带重试） =====
    retry_count = 0
    result = None

    while retry_count < MAX_RETRY_ATTEMPTS:
        try:
            result = await analyze_document(document)
            if result["status"] == "completed":
                break
            else:
                retry_count += 1
                if retry_count < MAX_RETRY_ATTEMPTS:
                    logger.warning(
                        f"[{doc_id}] AI 分析失败，重试 {retry_count}/{MAX_RETRY_ATTEMPTS}: {result.get('error')}"
                    )
                    await asyncio.sleep(2**retry_count)  # 指数退避
        except Exception as e:
            retry_count += 1
            if retry_count < MAX_RETRY_ATTEMPTS:
                logger.warning(
                    f"[{doc_id}] AI 分析异常，重试 {retry_count}/{MAX_RETRY_ATTEMPTS}: {e}"
                )
                await asyncio.sleep(2**retry_count)

    # ===== 更新分析结果 =====
    elapsed_time = time.time() - start_time

    if result and result["status"] == "completed":
        # 计算系统分类（不由 AI 输出）
        document_category = compute_document_category(
            ai_analysis_status="completed",
            impact_level=result["impact_level"],
            focus_required=result["focus_required"],
            archive_recommended=result["archive_recommended"],
        )

        update_data = {
            "ai_analysis_status": "completed",
            "ai_analyzed_at": datetime.now(UTC),
            "ai_summary": result["executive_summary"],
            "ai_key_points": {
                "regulation_type": result["regulation_type"],
                "impact_level": result["impact_level"],
                "relevance_level": result["relevance_level"],
                "lifecycle_impacts": result["lifecycle_impacts"],
                "departments": result["departments"],
                "ctd_sections": result["ctd_sections"],
                "recommended_actions": result["recommended_actions"],
                "focus_required": result["focus_required"],
                "archive_recommended": result["archive_recommended"],
                "notification_required": result["notification_required"],
                "confidence": result["confidence"],
                "evidence": result["evidence"],
                "evidence_excerpts": result["evidence_excerpts"],
            },
            "ai_relevance_score": result["impact_score"],
            "document_category": document_category,  # 系统计算的分类
        }

        await repo.update_document(db, document.id, update_data)
        await db.commit()

        logger.info(
            f"[{doc_id}] AI 分析完成: {doc_title} | "
            f"等级={result['impact_level']} | 评分={result['impact_score']:.2f} | "
            f"相关性={result['relevance_level']} | 分类={document_category} | "
            f"耗时={elapsed_time:.1f}s"
        )
        return True
    else:
        # 分析失败
        error_msg = result.get("error", "未知错误") if result else "未知错误"

        # 计算失败分类
        document_category = compute_document_category(
            ai_analysis_status="failed",
            impact_level=None,
            focus_required=None,
            archive_recommended=None,
        )

        await repo.update_document(
            db,
            document.id,
            {
                "ai_analysis_status": "failed",
                "ai_analyzed_at": datetime.now(UTC),
                "document_category": document_category,
            },
        )
        await db.commit()

        logger.error(
            f"[{doc_id}] AI 分析失败: {doc_title} | "
            f"重试次数={retry_count} | 错误={error_msg} | "
            f"耗时={elapsed_time:.1f}s"
        )
        return False


async def analyze_new_documents(
    db: AsyncSession,
    channel_id: str | None = None,
    limit: int = 10,
) -> dict[str, int]:
    """批量分析新文档。"""
    from sqlalchemy import and_, select

    stmt = select(RegulatoryDocument).where(
        and_(
            not RegulatoryDocument.is_deleted,
            RegulatoryDocument.ai_analysis_status is None,
        )
    )

    if channel_id:
        stmt = stmt.where(RegulatoryDocument.channel_id == channel_id)

    stmt = stmt.order_by(RegulatoryDocument.first_found_at.desc()).limit(limit)

    result = await db.execute(stmt)
    documents = result.scalars().all()

    stats = {"analyzed": 0, "failed": 0, "skipped": 0}

    for doc in documents:
        success = await analyze_and_update(db, doc)
        if success:
            stats["analyzed"] += 1
        else:
            stats["failed"] += 1

    logger.info(f"批量分析完成: {stats}")
    return stats
