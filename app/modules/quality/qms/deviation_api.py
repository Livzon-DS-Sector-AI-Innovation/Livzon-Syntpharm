"""偏差管理 API 路由"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.database import get_db, AsyncSession
from app.core.deps import CurrentUser, get_current_user
from app.modules.quality.qms.deviation_service import (
    DeviationService,
    InvestigationService,
    CorrectionService,
    ClosingService,
)
from app.modules.quality.qms.deviation_schemas import (
    DeviationCreate,
    DeviationUpdate,
    DeviationResponse,
    DeviationListItem,
    DeviationFilter,
    InvestigationCreate,
    InvestigationUpdate,
    InvestigationResponse,
    InvestigationListItem,
    CorrectionCreate,
    CorrectionUpdate,
    CorrectionResponse,
    CorrectionListItem,
    ClosingCreate,
    ClosingUpdate,
    ClosingResponse,
    ClosingListItem,
    DeviationStatistics,
    BatchLockRequest,
    ApprovalResponse,
)
from app.platform.ai.service import log_ai_interaction, AiLogService


class ApiResponse(BaseModel):
    """统一响应格式"""
    code: int = 200
    message: str = "Success"
    data: Optional[dict | list] = None


router = APIRouter(prefix="/deviation", tags=["偏差管理"])


def get_deviation_service(session = Depends(get_db)) -> DeviationService:
    return DeviationService(session)


def get_investigation_service(session = Depends(get_db)) -> InvestigationService:
    return InvestigationService(session)


def get_correction_service(session = Depends(get_db)) -> CorrectionService:
    return CorrectionService(session)


def get_closing_service(session = Depends(get_db)) -> ClosingService:
    return ClosingService(session)


# ========== 偏差主数据 API ==========

@router.get("", response_model=ApiResponse)
async def list_deviations(
    deviation_no: Optional[str] = Query(None, description="偏差编号"),
    deviation_type: Optional[str] = Query(None, description="偏差类型"),
    deviation_level: Optional[str] = Query(None, description="偏差等级"),
    status: Optional[str] = Query(None, description="状态"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    product_batch: Optional[str] = Query(None, description="生产批次"),
    department: Optional[str] = Query(None, description="部门"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: DeviationService = Depends(get_deviation_service),
):
    """获取偏差列表"""
    from datetime import datetime

    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None

    deviations, total = await service.list_deviations(
        deviation_no=deviation_no,
        deviation_type=deviation_type,
        deviation_level=deviation_level,
        status=status,
        start_date=start_dt,
        end_date=end_dt,
        product_batch=product_batch,
        department=department,
        page=page,
        page_size=page_size,
    )

    items = []
    for dev in deviations:
        items.append({
            "id": str(dev.id),
            "deviation_no": dev.deviation_no,
            "occurrence_date": dev.occurrence_date.isoformat() if dev.occurrence_date else None,
            "discovering_department": dev.discovering_department,
            "deviation_type": dev.deviation_type,
            "deviation_level": dev.deviation_level,
            "product_name": dev.product_name,
            "production_batch": dev.production_batch,
            "description": dev.abnormal_description,
            "status": dev.status,
            "batch_locked": dev.batch_locked,
            "has_investigation": dev.investigation is not None,
            "has_correction": dev.correction is not None,
            "has_closing": dev.closing is not None,
            "created_at": dev.created_at.isoformat() if dev.created_at else None,
        })

    return ApiResponse(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


# ========== 统计分析 API ==========

@router.get("/statistics", response_model=ApiResponse)
async def get_statistics(
    service: DeviationService = Depends(get_deviation_service),
):
    """获取统计数据"""
    stats = await service.get_statistics()
    return ApiResponse(data=stats.model_dump())


# ========== AI辅助功能 API ==========

@router.post("/ai/generate-description", response_model=ApiResponse)
async def ai_generate_description(
    deviation_type: Optional[str] = Query(None, description="偏差类型"),
    deviation_level: Optional[str] = Query(None, description="偏差级别"),
    occurrence_date: Optional[str] = Query(None, description="发生日期"),
    discovering_department: Optional[str] = Query(None, description="发现部门"),
    product_name: Optional[str] = Query(None, description="产品名称"),
    production_batch: Optional[str] = Query(None, description="生产批次"),
    keywords: str = Query(..., description="关键词，多个用逗号分隔"),
    current_user: CurrentUser | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI生成偏差描述"""
    try:
        from app.platform.ai.minimax_util import get_ai_util

        user_message = f"""请根据以下用户提供的信息，生成偏差描述。

【重要提醒】：以下信息是用户已填写的真实数据，请基于这些信息生成描述，不要自行想象或编造任何数据（如时间、地点、人员姓名、数量等）。

用户提供的信息：
- 偏差类型: {deviation_type or '未指定'}
- 偏差级别: {deviation_level or '未指定'}
- 发生日期: {occurrence_date or '未指定'}
- 发现部门: {discovering_department or '未指定'}
- 产品/物料名称: {product_name or '未指定'}
- 生产批次: {production_batch or '未指定'}
- 关键词描述: {keywords}

请基于以上真实信息生成偏差描述，描述格式参考：
1. 偏差概述：根据用户输入的关键词描述偏差的基本情况
2. 发现过程：描述偏差是如何被发现的
3. 具体表现：基于关键词描述偏差的具体现象

要求：
1. 只使用用户提供的信息，不要编造任何数据
2. 如信息缺失，该项填写"未提供"
3. 描述要客观、准确、专业
4. 使用规范的GMP用语
5. 格式清晰，分段说明
6. 免责声明："（以上内容由AI辅助生成，仅供参考，最终以人工审核确认。）"
"""

        system_prompt = """你是一位资深的GMP质量管理专家，擅长撰写偏差描述。

【重要原则】：你只能使用用户提供的真实信息来生成偏差描述，绝对不能编造任何数据。

【输出格式】：不要使用任何Markdown格式（如###、####、-、1. 等），只输出纯文本。用自然段落分隔内容即可。

生成规则：
1. 如果用户提供了发生日期，使用该日期；如果没提供，写"未提供"
2. 如果用户提供了发现部门，使用该部门；如果没提供，写"未提供"
3. 如果用户提供了产品/物料名称和批次，使用这些信息；如果没提供，写"未提供"
4. 如果用户提供了关键词，基于关键词描述偏差现象
5. 绝对不要自行编造：具体时间、具体地点、具体人员姓名、具体数量等
6. 只使用用户提供的关键词来描述偏差现象，不要添加额外的假设

请用中文回复，描述要客观、准确、清晰、基于事实。只用普通段落文字输出，不要任何格式符号。"""

        ai_util = get_ai_util()
        result = ai_util.chat(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.7,
            max_tokens=1024,
        )

        return ApiResponse(data={"description": result})
    except ValueError as e:
        error_msg = str(e)
        if "API Key" in error_msg or "AI配置" in error_msg:
            raise HTTPException(status_code=503, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI处理失败: {str(e)}")


@router.post("/ai/analyze-impact", response_model=ApiResponse)
async def ai_analyze_impact(
    deviation_type: Optional[str] = Query(None, description="偏差类型"),
    deviation_level: Optional[str] = Query(None, description="偏差级别"),
    occurrence_date: Optional[str] = Query(None, description="发生日期"),
    discovering_department: Optional[str] = Query(None, description="发现部门"),
    product_name: Optional[str] = Query(None, description="产品名称"),
    production_batch: Optional[str] = Query(None, description="生产批次"),
    description: Optional[str] = Query(None, description="偏差描述"),
    current_user: CurrentUser | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI分析影响范围"""
    try:
        from app.platform.ai.minimax_util import get_ai_util

        user_message = f"""请基于以下用户提供的信息，分析偏差的影响范围。

【重要提醒】：以下信息是用户已填写的真实数据，请基于这些信息进行分析，不要自行想象或编造任何数据。

用户提供的信息：
- 偏差类型: {deviation_type or '未提供'}
- 偏差级别: {deviation_level or '未提供'}
- 发生日期: {occurrence_date or '未提供'}
- 发现部门: {discovering_department or '未提供'}
- 产品/物料名称: {product_name or '未提供'}
- 生产批次: {production_batch or '未提供'}
- 偏差描述: {description or '未提供'}

请从以下维度分析影响范围：
1. 对产品质量的影响（原料、中间体、成品）
2. 对批次的影响（本批次、相关批次）
3. 对验证状态的影响
4. 对患者安全的影响
5. 对法规符合性的影响

【重要】：如信息缺失，该项填写"未提供"。免责声明："（以上内容由AI辅助生成，仅供参考，最终以人工审核确认。）"
"""

        system_prompt = """你是一位资深的GMP质量管理专家，擅长偏差影响分析。

【输出格式】：不要使用任何Markdown格式（如###、####、-、1. 等），只输出纯文本。用自然段落分隔内容即可。

请根据偏差类型和相关信息，系统性地分析偏差可能带来的影响范围。

分析要点：
- 人、机、料、法、环各维度的潜在影响
- 直接影响和间接影响
- 短期影响和长期影响
- 定性描述影响程度

请用中文回复，分析要全面、客观、专业。只用普通段落文字输出，不要任何格式符号。"""

        ai_util = get_ai_util()
        result = ai_util.chat(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.7,
            max_tokens=1024,
        )

        return ApiResponse(data={"impact_analysis": result})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ai/generate-emergency-measures", response_model=ApiResponse)
async def ai_generate_emergency_measures(
    deviation_type: str = Query(..., description="偏差类型"),
    deviation_level: Optional[str] = Query(None, description="偏差等级"),
    description: Optional[str] = Query(None, description="偏差描述"),
    current_user: CurrentUser | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI生成应急措施"""
    try:
        from app.platform.ai.minimax_util import get_ai_util

        user_message = f"""请为以下偏差生成应急措施：

偏差类型: {deviation_type}
偏差等级: {deviation_level or '未指定'}
偏差描述: {description or '未提供'}

要求：
1. 应急措施必须立即执行
2. 措施应能有效控制偏差扩大
3. 包含人员安全、产品安全、物料隔离等
4. 符合GMP规范要求

最后必须附上免责声明："（以上内容由AI辅助生成，仅供参考，最终以人工审核确认。）"
"""

        system_prompt = """你是一位资深的GMP质量管理专家，擅长制定偏差应急措施。

【输出格式】：不要使用任何Markdown格式（如###、####、-、1. 等），只输出纯文本。用自然段落分隔内容即可。

请根据偏差类型和等级，制定立即可行的应急措施。

应急措施应包括：
1. 人员安全措施
2. 产品隔离措施
3. 物料控制措施
4. 生产暂停或调整措施
5. 通知相关人员措施
6. 记录和报告措施

请用中文回复，措施要具体、可操作、及时有效。只用普通段落文字输出，不要任何格式符号。"""

        ai_util = get_ai_util()
        result = ai_util.chat(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.7,
            max_tokens=1024,
        )

        return ApiResponse(data={"emergency_measures": result})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ai/analyze-root-cause", response_model=ApiResponse)
async def ai_analyze_root_cause(
    deviation_type: str = Query(..., description="偏差类型"),
    description: Optional[str] = Query(None, description="偏差描述"),
    direct_cause: Optional[str] = Query(None, description="直接原因"),
    investigation_data: Optional[str] = Query(None, description="调查数据"),
    current_user: CurrentUser | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI使用5M1E方法分析根本原因"""
    try:
        from app.platform.ai.minimax_util import get_ai_util

        user_message = f"""请使用5M1E方法论分析以下偏差的根本原因：

偏差类型: {deviation_type}
偏差描述: {description or '未提供'}
直接原因: {direct_cause or '未提供'}
调查数据: {investigation_data or '未提供'}

5M1E分析维度：
- Man（人）：人员培训、操作失误、责任心等
- Machine（机器）：设备故障、维护不当、仪表校准等
- Material（物料）：原料问题、辅料问题、包材问题等
- Method（方法）：工艺参数、操作规程、SOP等
- Measurement（测量）：检测方法、取样方法、误差等
- Environment（环境）：温湿度、洁净度、光照等

最后必须附上免责声明："（以上内容由AI辅助生成，仅供参考，最终以人工审核确认。）"
"""

        system_prompt = """你是一位资深的GMP质量管理专家，精通5M1E根本原因分析方法。

【输出格式】：不要使用任何Markdown格式（如###、####、-、1. 等），只输出纯文本。用自然段落分隔内容即可。

请使用5M1E（人、机、料、法、测、环）方法论，系统性地分析偏差的根本原因。

分析要求：
1. 对每个M进行深入分析
2. 结合偏差类型和调查数据
3. 识别潜在的根本原因
4. 按可能性排序
5. 给出最可能的根本原因结论

请用中文回复，分析要深入、全面、有逻辑性。只用普通段落文字输出，不要任何格式符号。"""

        ai_util = get_ai_util()
        result = ai_util.chat(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.7,
            max_tokens=1536,
        )

        return ApiResponse(data={"root_cause_analysis": result})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ai/analyze-direct-cause", response_model=ApiResponse)
async def ai_analyze_direct_cause(
    deviation_type: str = Query(..., description="偏差类型"),
    description: Optional[str] = Query(None, description="偏差描述"),
    product_name: Optional[str] = Query(None, description="产品/物料名称"),
    production_batch: Optional[str] = Query(None, description="生产批次"),
    current_user: CurrentUser | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI分析直接原因"""
    try:
        from app.platform.ai.minimax_util import get_ai_util

        user_message = f"""请分析以下偏差的直接原因：

偏差类型: {deviation_type}
偏差描述: {description or '未提供'}
产品/物料名称: {product_name or '未提供'}
生产批次: {production_batch or '未提供'}

直接原因定义：指导致偏差发生的最直接、最表面的原因，通常是偏差发生的当时就能观察到或测量到的现象。

最后必须附上免责声明："（以上内容由AI辅助生成，仅供参考，最终以人工审核确认。）"
"""

        system_prompt = """你是一位资深的GMP质量管理专家，擅长分析偏差的直接原因。

【输出格式】：不要使用任何Markdown格式（如###、####、-、1. 等），只输出纯文本。用自然段落分隔内容即可。

分析要求：
1. 基于偏差描述，准确识别偏差发生的直接表现
2. 分析导致该直接表现的技术或操作层面的原因
3. 直接原因应简洁明了，直指问题的核心
4. 不要深入分析根本原因，那是后续5M1E分析的任务

请用中文回复，表述要清晰、准确。只用普通段落文字输出，不要任何格式符号。"""

        ai_util = get_ai_util()
        result = ai_util.chat(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.7,
            max_tokens=1024,
        )

        return ApiResponse(data={"direct_cause_analysis": result})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ai/generate-capa", response_model=ApiResponse)
async def ai_generate_capa(
    deviation_type: str = Query(..., description="偏差类型"),
    root_cause: Optional[str] = Query(None, description="根本原因"),
    deviation_level: Optional[str] = Query(None, description="偏差等级"),
    department: Optional[str] = Query(None, description="责任部门"),
    current_user: CurrentUser | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI生成CAPA（纠正措施和预防措施）"""
    try:
        from app.platform.ai.minimax_util import get_ai_util

        user_message = f"""请为以下偏差生成CAPA（纠正措施和预防措施）：

偏差类型: {deviation_type}
根本原因: {root_cause or '未提供'}
偏差等级: {deviation_level or '未指定'}
责任部门: {department or '未指定'}

要求：
1. 纠正措施（CA）针对已发生的偏差
2. 预防措施（PA）防止类似偏差再次发生
3. 措施要具体、可操作、有时限
4. 符合GMP规范要求

最后必须附上免责声明："（以上内容由AI辅助生成，仅供参考，最终以人工审核确认。）"
"""

        system_prompt = """你是一位资深的GMP质量管理专家，擅长制定CAPA（纠正预防措施）。

【输出格式】：不要使用任何Markdown格式（如###、####、-、1. 等），只输出纯文本。用自然段落分隔内容即可。

请根据偏差类型和根本原因，制定系统性的CAPA。

CAPA结构：
1. 纠正措施（Corrective Action）- 针对已发生的偏差
   - 立即采取的纠正行动
   - 偏差物料/产品的处理
   - 相关记录的修正

2. 预防措施（Preventive Action）- 防止类似偏差再次发生
   - 工艺/方法的改进
   - 设备的维护升级
   - 人员的培训强化
   - 管理制度的完善
   - 监控机制的建立

每项措施请包含：具体行动、责任人、完成时限、验证方法。

请用中文回复，措施要具体、可操作、有时限、可验证。只用普通段落文字输出，不要任何格式符号。"""

        ai_util = get_ai_util()
        result = ai_util.chat(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.7,
            max_tokens=1536,
        )

        return ApiResponse(data={"capa": result})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ai/generate-prevention", response_model=ApiResponse)
async def ai_generate_prevention(
    deviation_type: str = Query(..., description="偏差类型"),
    root_cause: Optional[str] = Query(None, description="根本原因"),
    deviation_level: Optional[str] = Query(None, description="偏差等级"),
    department: Optional[str] = Query(None, description="责任部门"),
    current_user: CurrentUser | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI生成预防措施（PA）"""
    try:
        from app.platform.ai.minimax_util import get_ai_util

        user_message = f"""请为以下偏差生成预防措施（PA），防止类似偏差再次发生：

偏差类型: {deviation_type}
根本原因: {root_cause or '未提供'}
偏差等级: {deviation_level or '未指定'}
责任部门: {department or '未指定'}

要求：
1. 预防措施要针对根本原因，防止类似问题再次发生
2. 措施要具体、可操作、有时限
3. 符合GMP规范要求

最后必须附上免责声明："（以上内容由AI辅助生成，仅供参考，最终以人工审核确认。）"
"""

        system_prompt = """你是一位资深的GMP质量管理专家，擅长制定预防措施（Preventive Action）。

【输出格式】：不要使用任何Markdown格式（如###、####、-、1. 等），只输出纯文本。用自然段落分隔内容即可。

请根据偏差类型和根本原因，制定系统性的预防措施。

预防措施（Preventive Action）结构：
1. 工艺/方法的改进 - 优化生产流程和操作规程
2. 设备的维护升级 - 改进设备性能和维护计划
3. 人员的培训强化 - 加强技能培训和考核
4. 管理制度的完善 - 健全质量管理体系
5. 监控机制的建立 - 建立预警和监控体系

每项措施请包含：具体行动、责任人、完成时限、验证方法。

请用中文回复，措施要具体、可操作、有时限、可验证。只用普通段落文字输出，不要任何格式符号。"""

        ai_util = get_ai_util()
        result = ai_util.chat(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.7,
            max_tokens=1536,
        )

        return ApiResponse(data={"prevention": result})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{deviation_id}", response_model=ApiResponse)
async def get_deviation(
    deviation_id: UUID,
    service: DeviationService = Depends(get_deviation_service),
):
    """获取偏差详情"""
    try:
        result = await service.get_deviation(deviation_id)
        if not result:
            raise ValueError("偏差不存在")

        data = {
            "deviation": {
                "id": str(result["deviation"].id),
                "deviation_no": result["deviation"].deviation_no,
                "occurrence_date": result["deviation"].occurrence_date.isoformat() if result["deviation"].occurrence_date else None,
                "discovering_department": result["deviation"].discovering_department,
                "discoverer": result["deviation"].discoverer,
                "product_code": result["deviation"].product_code,
                "product_name": result["deviation"].product_name,
                "production_batch": result["deviation"].production_batch,
                "material_code": result["deviation"].material_code,
                "batch_size": result["deviation"].batch_size,
                "deviation_type": result["deviation"].deviation_type,
                "deviation_level": result["deviation"].deviation_level,
                # 添加description字段作为abnormal_description的别名
                "description": result["deviation"].abnormal_description,
                "abnormal_description": result["deviation"].abnormal_description,
                "impact_scope": result["deviation"].impact_scope,
                "emergency_measures": result["deviation"].emergency_measures,
                "attachments": result["deviation"].attachments or [],
                "batch_locked": result["deviation"].batch_locked,
                "batch_lock_reason": result["deviation"].batch_lock_reason,
                "status": result["deviation"].status,
                "created_at": result["deviation"].created_at.isoformat() if result["deviation"].created_at else None,
            },
            "investigation": None,
            "correction": None,
            "closing": None,
            "approvals": [],
        }

        if result["investigation"]:
            data["investigation"] = {
                "id": str(result["investigation"].id),
                "deviation_id": str(result["investigation"].deviation_id),
                "investigation_team": result["investigation"].investigation_team,
                "investigation_start_date": result["investigation"].investigation_start_date.isoformat() if result["investigation"].investigation_start_date else None,
                "investigation_end_date": result["investigation"].investigation_end_date.isoformat() if result["investigation"].investigation_end_date else None,
                "investigation_method": result["investigation"].investigation_method,
                "direct_cause": result["investigation"].direct_cause,
                "indirect_cause": result["investigation"].indirect_cause,
                "root_cause": result["investigation"].root_cause,
                "why_analysis": result["investigation"].why_analysis,
                "impact_assessment": result["investigation"].impact_assessment,
                "investigation_conclusion": result["investigation"].investigation_conclusion,
                "affected_batches": result["investigation"].affected_batches,
                "temporary_measures": result["investigation"].temporary_measures,
                "attachments": result["investigation"].attachments or [],
                "status": result["investigation"].status,
            }

        if result["correction"]:
            data["correction"] = {
                "id": str(result["correction"].id),
                "deviation_id": str(result["correction"].deviation_id),
                "correction_measures": result["correction"].correction_measures,
                "responsible_department": result["correction"].responsible_department,
                "responsible_person": result["correction"].responsible_person,
                "plan_completion_date": result["correction"].plan_completion_date.isoformat() if result["correction"].plan_completion_date else None,
                "temporary_corrective_actions": result["correction"].temporary_corrective_actions or [],
                "long_term_corrective_actions": result["correction"].long_term_corrective_actions or [],
                "progress": result["correction"].progress,
                "status": result["correction"].status,
                "evidence_attachments": result["correction"].evidence_attachments or [],
            }

        if result["closing"]:
            data["closing"] = {
                "id": str(result["closing"].id),
                "deviation_id": str(result["closing"].deviation_id),
                "verification_plan": result["closing"].verification_plan,
                "verification_data": result["closing"].verification_data,
                "verification_result": result["closing"].verification_result,
                "is_resolved": result["closing"].is_resolved,
                "conclusion": result["closing"].conclusion,
                "attachments": result["closing"].attachments or [],
                "batch_unlocked": result["closing"].batch_unlocked,
                "archived": result["closing"].archived,
            }

        return ApiResponse(data=data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("", response_model=ApiResponse)
async def create_deviation(
    data: DeviationCreate,
    service: DeviationService = Depends(get_deviation_service),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """创建偏差"""
    try:
        user_id = current_user.id if current_user else None
        result = await service.create_deviation(data, user_id)
        return ApiResponse(
            message="创建成功",
            data={
                "id": str(result["deviation"].id),
                "deviation_no": result["deviation_no"],
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{deviation_id}", response_model=ApiResponse)
async def update_deviation(
    deviation_id: UUID,
    data: DeviationUpdate,
    service: DeviationService = Depends(get_deviation_service),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """更新偏差"""
    try:
        deviation = await service.update_deviation(deviation_id, data)
        if not deviation:
            raise ValueError("偏差不存在")
        return ApiResponse(
            message="更新成功",
            data={"id": str(deviation.id)}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/{deviation_id}")
async def delete_deviation(
    deviation_id: UUID,
    service: DeviationService = Depends(get_deviation_service),
):
    """删除偏差"""
    try:
        result = await service.delete_deviation(deviation_id)
        if not result:
            raise ValueError("偏差不存在")
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{deviation_id}/submit", response_model=ApiResponse)
async def submit_deviation(
    deviation_id: UUID,
    service: DeviationService = Depends(get_deviation_service),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """提交偏差"""
    try:
        user_id = current_user.id if current_user else None
        await service.submit_deviation(deviation_id, user_id)
        return ApiResponse(message="提交成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{deviation_id}/approve", response_model=ApiResponse)
async def approve_deviation(
    deviation_id: UUID,
    approved: bool = Query(..., description="是否批准"),
    comments: Optional[str] = Query(None, description="审批意见"),
    approval_type: str = Query("admin", description="审批类型"),
    service: DeviationService = Depends(get_deviation_service),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """审批偏差"""
    try:
        user_id = current_user.id if current_user else None
        user_name = current_user.display_name if current_user else None
        await service.approve_deviation(
            deviation_id, approved, comments, approval_type, user_id, user_name
        )
        return ApiResponse(message="审批完成")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{deviation_id}/lock-batch", response_model=ApiResponse)
async def lock_batch(
    deviation_id: UUID,
    data: BatchLockRequest,
    service: DeviationService = Depends(get_deviation_service),
):
    """锁定批次"""
    try:
        await service.lock_batch(deviation_id, data.reason)
        return ApiResponse(message="批次已锁定")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{deviation_id}/unlock-batch", response_model=ApiResponse)
async def unlock_batch(
    deviation_id: UUID,
    service: DeviationService = Depends(get_deviation_service),
):
    """解锁批次"""
    try:
        await service.unlock_batch(deviation_id)
        return ApiResponse(message="批次已解锁")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== 偏差调查 API ==========

@router.get("/investigations/list", response_model=ApiResponse)
async def list_investigations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: InvestigationService = Depends(get_investigation_service),
):
    """待调查列表"""
    investigations, total = await service.list_pending(page, page_size)

    items = []
    for inv in investigations:
        items.append({
            "id": str(inv.id),
            "deviation_id": str(inv.deviation_id),
            "deviation_no": inv.deviation.deviation_no if inv.deviation else None,
            "investigation_team": inv.investigation_team,
            "investigation_start_date": inv.investigation_start_date.isoformat() if inv.investigation_start_date else None,
            "investigation_end_date": inv.investigation_end_date.isoformat() if inv.investigation_end_date else None,
            "status": inv.status,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
        })

    return ApiResponse(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.post("/{deviation_id}/investigation", response_model=ApiResponse)
async def create_investigation(
    deviation_id: UUID,
    data: InvestigationCreate,
    service: InvestigationService = Depends(get_investigation_service),
):
    """创建调查"""
    try:
        investigation = await service.create_investigation(deviation_id, data)
        return ApiResponse(
            message="创建成功",
            data={"id": str(investigation.id)}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{deviation_id}/investigation", response_model=ApiResponse)
async def update_investigation(
    deviation_id: UUID,
    data: InvestigationUpdate,
    service: InvestigationService = Depends(get_investigation_service),
):
    """更新调查"""
    try:
        investigation = await service.update_investigation(deviation_id, data)
        if not investigation:
            raise ValueError("调查记录不存在")
        return ApiResponse(message="更新成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{deviation_id}/investigation/complete", response_model=ApiResponse)
async def complete_investigation(
    deviation_id: UUID,
    service: InvestigationService = Depends(get_investigation_service),
):
    """完成调查"""
    try:
        await service.complete_investigation(deviation_id)
        return ApiResponse(message="调查已完成")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== 偏差整改 API ==========

@router.get("/corrections/list", response_model=ApiResponse)
async def list_corrections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: CorrectionService = Depends(get_correction_service),
):
    """待整改列表"""
    corrections, total = await service.list_pending(page, page_size)

    items = []
    for corr in corrections:
        items.append({
            "id": str(corr.id),
            "deviation_id": str(corr.deviation_id),
            "deviation_no": corr.deviation.deviation_no if corr.deviation else None,
            "responsible_department": corr.responsible_department,
            "responsible_person": corr.responsible_person,
            "plan_completion_date": corr.plan_completion_date.isoformat() if corr.plan_completion_date else None,
            "progress": corr.progress,
            "status": corr.status,
            "created_at": corr.created_at.isoformat() if corr.created_at else None,
        })

    return ApiResponse(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.post("/{deviation_id}/correction", response_model=ApiResponse)
async def create_correction(
    deviation_id: UUID,
    data: CorrectionCreate,
    service: CorrectionService = Depends(get_correction_service),
):
    """创建整改"""
    try:
        correction = await service.create_correction(deviation_id, data)
        return ApiResponse(
            message="创建成功",
            data={"id": str(correction.id)}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{deviation_id}/correction", response_model=ApiResponse)
async def update_correction(
    deviation_id: UUID,
    data: CorrectionUpdate,
    service: CorrectionService = Depends(get_correction_service),
):
    """更新整改"""
    try:
        correction = await service.update_correction(deviation_id, data)
        if not correction:
            raise ValueError("整改记录不存在")
        return ApiResponse(message="更新成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{deviation_id}/correction/progress", response_model=ApiResponse)
async def update_correction_progress(
    deviation_id: UUID,
    progress: int = Query(..., ge=0, le=100),
    service: CorrectionService = Depends(get_correction_service),
):
    """更新整改进度"""
    try:
        await service.update_progress(deviation_id, progress)
        return ApiResponse(message="进度已更新")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== 偏差关闭 API ==========

@router.get("/closings/list", response_model=ApiResponse)
async def list_closings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: ClosingService = Depends(get_closing_service),
):
    """待关闭列表"""
    closings, total = await service.list_pending(page, page_size)

    items = []
    for clo in closings:
        items.append({
            "id": str(clo.id),
            "deviation_id": str(clo.deviation_id),
            "deviation_no": clo.deviation.deviation_no if clo.deviation else None,
            "is_resolved": clo.is_resolved,
            "conclusion": clo.conclusion,
            "archived": clo.archived,
            "created_at": clo.created_at.isoformat() if clo.created_at else None,
        })

    return ApiResponse(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.post("/{deviation_id}/closing", response_model=ApiResponse)
async def create_closing(
    deviation_id: UUID,
    data: ClosingCreate,
    service: ClosingService = Depends(get_closing_service),
):
    """创建关闭申请"""
    try:
        closing = await service.create_closing(deviation_id, data)
        return ApiResponse(
            message="创建成功",
            data={"id": str(closing.id)}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{deviation_id}/closing", response_model=ApiResponse)
async def update_closing(
    deviation_id: UUID,
    data: ClosingUpdate,
    service: ClosingService = Depends(get_closing_service),
):
    """更新关闭记录"""
    try:
        closing = await service.update_closing(deviation_id, data)
        if not closing:
            raise ValueError("关闭记录不存在")
        return ApiResponse(message="更新成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{deviation_id}/closing/complete", response_model=ApiResponse)
async def complete_closing(
    deviation_id: UUID,
    service: ClosingService = Depends(get_closing_service),
):
    """完成关闭"""
    try:
        await service.complete_closing(deviation_id)
        return ApiResponse(message="偏差已关闭")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# 添加 HTTPException 导入
from fastapi import HTTPException