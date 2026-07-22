from fastapi import APIRouter

from app.core.config_api import router as module_settings_router
from app.core.llm.api import router as llm_router
from app.modules.administration import router as administration_router
from app.modules.energy import router as energy_router
from app.modules.environment import router as environment_router
from app.modules.equipment import router as equipment_router
from app.modules.hr import router as hr_router
from app.modules.hr.ai_exam import router as ai_exam_router
from app.modules.procurement import router as procurement_router
from app.modules.production import router as production_router
from app.modules.production.product import output_router as product_output_router
from app.modules.production.product import product_router as workshop_product_router
from app.modules.production.product.sync_config_api import router as product_sync_config_router
from app.modules.quality import (
    cpv_router,
    deviation_router,
    doc_check_router,
    fqc_router,
    instrument_router,
    ipqc_router,
    iqc_router,
    quality_reagent_router,
    quality_router,
    reagent_reminder_router,
    sampling_router,
    stability_router,
    static_data_router,
)
from app.modules.quality.label_verification import router as label_verification_router
from app.modules.quality.sop_ai import router as sop_ai_router
from app.modules.registration import router as registration_router
from app.modules.registration.dossier_writer import router as dossier_writer_router
from app.modules.registration.regulatory_tracker import (
    router as regulatory_tracker_router,
)
from app.modules.research import router as research_router
from app.modules.safety import router as safety_router
from app.modules.warehouse import router as warehouse_router
from app.platform.identity.api import (
    auth_router,
    dept_router,
    login_log_router,
    personnel_router,
    sync_router,
    user_router,
)
from app.platform.system import router as system_router

api_router = APIRouter()

api_router.include_router(user_router, prefix="/identity", tags=["用户信息"])
api_router.include_router(dept_router, prefix="/identity", tags=["组织架构"])
api_router.include_router(personnel_router, prefix="/identity", tags=["人员名单"])
api_router.include_router(auth_router, prefix="/identity", tags=["认证"])
api_router.include_router(sync_router, prefix="/identity", tags=["飞书同步"])
api_router.include_router(login_log_router, prefix="/identity", tags=["登录记录"])
api_router.include_router(system_router, prefix="/system", tags=["系统"])
api_router.include_router(production_router, prefix="/production", tags=["生产管理"])
api_router.include_router(equipment_router, prefix="/equipment", tags=["设备管理"])
api_router.include_router(safety_router, prefix="/safety", tags=["安全管理"])
api_router.include_router(environment_router, prefix="/environment", tags=["环保管理"])
api_router.include_router(energy_router, prefix="/energy", tags=["能源管理"])
api_router.include_router(warehouse_router, prefix="/warehouse", tags=["仓储管理"])
api_router.include_router(procurement_router, prefix="/procurement", tags=["采购管理"])
api_router.include_router(
    administration_router,
    prefix="/administration",
    tags=["行政管理"],
)
api_router.include_router(hr_router, prefix="/hr", tags=["人事管理"])
api_router.include_router(ai_exam_router, prefix="/hr/ai-exam", tags=["AI 出题"])
api_router.include_router(research_router, prefix="/research", tags=["研发管理"])
api_router.include_router(
    registration_router,
    prefix="/registration",
    tags=["注册管理"],
)
# QMS routers
api_router.include_router(quality_router, prefix="/quality", tags=["质量管理"])
api_router.include_router(sampling_router, prefix="/quality", tags=["质量管理 - 取样"])
api_router.include_router(iqc_router, prefix="/quality", tags=["质量管理 - IQC"])
api_router.include_router(ipqc_router, prefix="/quality", tags=["质量管理 - IPQC"])
api_router.include_router(fqc_router, prefix="/quality", tags=["质量管理 - FQC"])
api_router.include_router(stability_router, prefix="/quality", tags=["质量管理 - 稳定性"])
api_router.include_router(deviation_router, prefix="/quality", tags=["质量管理 - 偏差"])
api_router.include_router(quality_reagent_router, prefix="/quality", tags=["质量管理 - 试剂"])
api_router.include_router(doc_check_router, prefix="/quality", tags=["质量管理 - 文件检查"])
api_router.include_router(static_data_router, prefix="/quality", tags=["质量管理 - 静态数据"])
api_router.include_router(reagent_reminder_router, prefix="/quality", tags=["质量管理 - 试剂提醒"])
api_router.include_router(instrument_router, prefix="/quality", tags=["质量管理 - 仪器校准"])
# CPV router
api_router.include_router(cpv_router, prefix="/quality", tags=["质量管理 - CPV"])
api_router.include_router(sop_ai_router, prefix="/quality/sop-ai", tags=["SOP AI"])
api_router.include_router(label_verification_router, prefix="/quality", tags=["质量管理 - 标签复核"])
api_router.include_router(
    workshop_product_router,
    prefix="/production",
    tags=["生产管理 - 产品定义"],
)
api_router.include_router(
    product_output_router,
    prefix="/production",
    tags=["生产管理 - 产量记录"],
)
api_router.include_router(
    product_sync_config_router,
    prefix="/production",
    tags=["生产管理 - 同步配置"],
)
api_router.include_router(regulatory_tracker_router, prefix="/registration", tags=["法规追踪"])
api_router.include_router(
    dossier_writer_router,
    prefix="/registration/dossier-writer",
    tags=["申报资料撰写"],
)

api_router.include_router(llm_router, tags=["LLM配置"])
api_router.include_router(module_settings_router, tags=["模块配置"])
