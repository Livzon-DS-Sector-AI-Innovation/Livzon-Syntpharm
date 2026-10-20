"""权限代码注册表（唯一权威）。

所有权限码、内置角色、接口绑定的定义都集中在此。应用启动时由
`sync_registry`（见 service.py）把这些声明幂等地同步进 DB 的只读镜像表。

规则（对照《权限体系设计对比报告》第六节）：
- 权限码一经发布不可删除、不可复用；下线只能标记 deprecated（退役）。
- 每个受保护接口必须在此登记 api_bindings（方法 + 路由模板），未登记 → 403。
- 新增权限码请在此追加，不要直接改 DB。
"""

from dataclasses import dataclass

from app.shared.module_registry import BUSINESS_MODULES

# ── 动作集合 ──────────────────────────────────────────────────────

# 业务资源动作（固定集合，业务模块新增权限码必须从此取值）
BUSINESS_ACTIONS: tuple[str, ...] = (
    "read",
    "create",
    "update",
    "delete",
    "submit",
    "approve",
    "reject",
    "export",
    "import",
)

# 平台管理动作
PLATFORM_ACTIONS: tuple[str, ...] = ("read", "manage")


# ── 声明结构 ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class PermissionDef:
    code: str
    name: str
    module: str
    resource: str
    action: str
    description: str = ""


@dataclass(frozen=True)
class RoleDef:
    code: str
    name: str
    category: str
    module_code: str | None
    description: str
    is_superuser: bool = False


@dataclass(frozen=True)
class ApiBindingDef:
    permission_code: str
    method: str
    route_template: str
    scope_required: bool = False


# ── 平台权限码 ────────────────────────────────────────────────────

PLATFORM_PERMISSIONS: tuple[PermissionDef, ...] = (
    PermissionDef("platform:user:read", "查看用户", "platform", "user", "read"),
    PermissionDef("platform:user:manage", "管理用户", "platform", "user", "manage"),
    PermissionDef("platform:role:read", "查看角色", "platform", "role", "read"),
    PermissionDef("platform:role:manage", "管理角色", "platform", "role", "manage"),
    PermissionDef("platform:permission:read", "查看权限目录", "platform", "permission", "read"),
    PermissionDef("platform:grant:read", "查看授权", "platform", "grant", "read"),
    PermissionDef("platform:grant:manage", "管理授权", "platform", "grant", "manage"),
    PermissionDef("platform:config:read", "查看平台配置", "platform", "config", "read"),
    PermissionDef("platform:config:manage", "管理平台配置", "platform", "config", "manage"),
    PermissionDef("platform:audit:read", "查看审计日志", "platform", "audit", "read"),
    PermissionDef("platform:api-binding:read", "查看接口绑定登记簿", "platform", "api-binding", "read"),
    PermissionDef("platform:ops:read", "查看系统运维", "platform", "ops", "read"),
    PermissionDef("platform:ops:manage", "系统运维操作", "platform", "ops", "manage"),
)


# ── 管理界面展示用中文名（仅渲染用，不参与权限判定）──────────────

PLATFORM_DOMAIN_LABEL = "平台管理"

RESOURCE_LABELS: dict[str, str] = {
    "user": "用户管理",
    "role": "角色管理",
    "permission": "权限目录",
    "grant": "授权管理",
    "config": "平台配置",
    "audit": "审计日志",
    "api-binding": "接口绑定",
    "ops": "系统运维",
    # ── research（研发管理）资源 ──
    "project": "研发项目",
    "track": "研究跟踪",
    "initiation": "立项",
    "route": "工艺路线",
    "experiment-log": "实验日志",
    "pilot-study": "中试研究",
    "pilot-workflow": "中试工作流",
    "process-validation": "工艺验证",
    "registration-filing": "注册申报",
    "deliverable-template": "交付物模板",
    "stage-deliverable": "阶段交付物",
    "optimization": "工艺优化",
    "ich": "ICH 分析",
    "literature": "文献分析",
    "report": "研发报告",
    # ── warehouse（仓储管理）资源 ──
    "raw-material": "原辅料库存",
    "packaging-material": "包材库存",
    "product": "成品库存",
    "feishu-config": "仓储飞书配置",
    "feishu-table": "仓储飞书数据表",
    "feishu-record": "仓储飞书记录",
    "feishu-ws": "仓储飞书 WS",
    # ── procurement（采购管理）资源 ──
    "invoice": "采购发票",
    "supplier": "供应商清单",
    "invoice-record": "发票识别记录",
    "purchase-order": "采购订单",
    "purchase-request": "采购申请",
    "contract": "采购合同",
    # ── administration（行政管理）资源 ──
    "vehicle": "车辆信息",
    # ── energy（能耗管理）资源 ──
    "platform": "平台信息",
    "overview": "能耗总览",
    "sync": "数据同步",
    "job": "异步任务",
    "target": "单耗目标",
    "analysis": "AI 分析",
    "device": "设备配置",
    "data": "能耗数据",
    "collect": "采集管理",
    "alert-rule": "预警规则",
    "alert-record": "预警记录",
    "workshop": "车间管理",
    "monthly-record": "月度记录",
    # ── equipment（设备管理）资源 ──
    "equipment": "设备台账",
    "batch-import": "批量导入",
    "spare-part": "备件管理",
    "work-order": "维修工单",
    "calibration": "校准管理",
    "maintenance-plan": "维护计划",
    "inspection-template": "巡检模板",
    "failure-code": "故障代码",
    "personnel": "设备人员",
    "inspection": "巡检管理",
    "maintenance-config": "维护配置",
    "maintenance-staff": "维护人员",
    # ── registration（注册管理）资源 ──
    "project": "注册项目",
    "drug": "药品申报",
    "certificate": "注册证书",
    "authorization-letter": "授权书",
    "reference-standard": "对照物质说明表",
    "reference-substance": "对照品说明表",
    "supplementary-reply": "发补回复",
    "holiday": "节假日管理",
    "validation-audit": "验证文件审核",
    "dossier": "申报资料",
    "regulatory-tracker": "法规追踪",
    "dashboard": "注册看板",
    "approval-record": "审批记录",
    "quality:capa": "CAPA管理",
    "quality:cpv": "持续工艺验证(CPV)",
    "quality:deviation": "偏差管理",
    "quality:deviation-settings": "偏差设置",
    "quality:doc-check": "文件检查",
    "quality:export": "数据导出",
    "quality:fqc": "FQC成品检验",
    "quality:instrument": "仪器校准",
    "quality:ipqc": "IPQC过程检验",
    "quality:iqc": "IQC来料检验",
    "quality:job": "任务管理",
    "quality:label-verification": "标签复核",
    "quality:material-report": "原料报告单",
    "quality:problem": "问题管理",
    "quality:reagent": "试剂管理",
    "quality:reagent-reminder": "试剂提醒",
    "quality:record": "校验记录",
    "quality:sampling": "取样管理",
    "quality:sop-ai": "SOP AI文件校验",
    "quality:stability": "稳定性试验",
    "quality:standard": "检验标准",
    "quality:static-data": "静态数据",
    "hr:ai-exam": "AI出题",
    "hr:annual-training-plans": "年度培训计划",
    "hr:candidates": "候选人管理",
    "hr:departments": "部门管理",
    "hr:departure-records": "离职记录",
    "hr:employees": "员工管理",
    "hr:new-departments": "新部门",
    "hr:new-departure-records": "新离职记录",
    "hr:new-employees": "新员工",
    "hr:new-offboarding-records": "新离岗记录",
    "hr:new-onboarding-records": "新入职记录",
    "hr:offboarding-records": "离岗记录",
    "hr:onboarding-evaluation": "上岗评估",
    "hr:onboarding-records": "入职记录",
    "hr:prejob-training-templates": "岗前培训模板",
    "hr:system-settings": "系统设置",
    "hr:teams": "班组管理",
    "hr:training-evaluation": "培训评估",
    "hr:training-ledgers": "培训台账",
    "hr:training-notification": "培训通知",
    "hr:training-notifications": "培训通知",
    "hr:training-select-tasks": "培训选课",
    "hr:training-sessions": "培训课程",
    "hr:training-sign-in-sheet": "培训签到表",
    "hr:training-specialists": "培训专员",
    "hr:training-teams": "培训班组",
    "hr:turnover-analysis": "流失率分析",
    "hr:webhook": "飞书回调",
    "production:batches": "生产批次",
    "production:materials": "批次物料",
    "production:parameters": "工艺参数",
    "production:plans": "生产计划",
    "production:pressure-audit": "压差审核",
    "production:pressure-dashboard": "压差仪表盘",
    "production:pressure-data-master": "压差数据管理",
    "production:pressure-notifications": "压差通知",
    "production:pressure-ocr-tasks": "压差OCR任务",
    "production:pressure-point-mappings": "压差点位映射",
    "production:pressure-records": "压差记录",
    "production:process-specs": "工艺规程",
    "production:product-output": "产量记录",
    "production:product-sync-config": "同步配置",
    "production:products": "产品定义",
    "production:records": "生产记录",
    "production:steps": "工艺步骤",
    "production:tasks": "生产任务",
}

# ── 业务模块访问权限码（菜单级：每个模块 1 个）─────────────────────
#
# 粒度刻意做粗：只控制「模块菜单是否可见 + 模块页面能否进入」。
# 具体接口/操作权限（`<module>:<resource>:<action>`）后续按需追加 ——
# 两层**正交**：菜单认这里的粗码，接口认细码，细化时无需改菜单配置。
#
# 模块清单一律取自 `BUSINESS_MODULES`（唯一权威），不手抄，避免与前端菜单漂移。
BUSINESS_MODULE_PERMISSIONS: tuple[PermissionDef, ...] = tuple(
    PermissionDef(
        code=f"{module.code}:module:read",
        name=f"访问{module.name}",
        module=module.code,
        resource="module",
        action="read",
        description="模块菜单可见性与页面准入（接口级权限后续追加）",
    )
    for module in BUSINESS_MODULES
)


# ── 业务模块细粒度权限码：research（研发管理）─────────────────

RESEARCH_PERMISSIONS: tuple[PermissionDef, ...] = (
    PermissionDef(
        "research:deliverable-template:create", "创建交付物模板", "research", "deliverable-template", "create"
    ),
    PermissionDef(
        "research:deliverable-template:delete", "删除交付物模板", "research", "deliverable-template", "delete"
    ),
    PermissionDef("research:deliverable-template:read", "查看交付物模板", "research", "deliverable-template", "read"),
    PermissionDef(
        "research:deliverable-template:update", "更新交付物模板", "research", "deliverable-template", "update"
    ),
    PermissionDef("research:experiment-log:create", "创建实验日志", "research", "experiment-log", "create"),
    PermissionDef("research:experiment-log:delete", "删除实验日志", "research", "experiment-log", "delete"),
    PermissionDef("research:experiment-log:export", "导出实验日志", "research", "experiment-log", "export"),
    PermissionDef("research:experiment-log:read", "查看实验日志", "research", "experiment-log", "read"),
    PermissionDef("research:experiment-log:update", "更新实验日志", "research", "experiment-log", "update"),
    PermissionDef("research:ich:create", "创建ICH 分析", "research", "ich", "create"),
    PermissionDef("research:ich:delete", "删除ICH 分析", "research", "ich", "delete"),
    PermissionDef("research:ich:read", "查看ICH 分析", "research", "ich", "read"),
    PermissionDef("research:initiation:create", "创建立项", "research", "initiation", "create"),
    PermissionDef("research:initiation:delete", "删除立项", "research", "initiation", "delete"),
    PermissionDef("research:initiation:read", "查看立项", "research", "initiation", "read"),
    PermissionDef("research:initiation:update", "更新立项", "research", "initiation", "update"),
    PermissionDef("research:literature:create", "创建文献分析", "research", "literature", "create"),
    PermissionDef("research:optimization:create", "创建工艺优化", "research", "optimization", "create"),
    PermissionDef("research:optimization:delete", "删除工艺优化", "research", "optimization", "delete"),
    PermissionDef("research:optimization:read", "查看工艺优化", "research", "optimization", "read"),
    PermissionDef("research:optimization:update", "更新工艺优化", "research", "optimization", "update"),
    PermissionDef("research:pilot-study:create", "创建中试研究", "research", "pilot-study", "create"),
    PermissionDef("research:pilot-study:delete", "删除中试研究", "research", "pilot-study", "delete"),
    PermissionDef("research:pilot-study:read", "查看中试研究", "research", "pilot-study", "read"),
    PermissionDef("research:pilot-study:update", "更新中试研究", "research", "pilot-study", "update"),
    PermissionDef("research:pilot-workflow:approve", "审批中试工作流", "research", "pilot-workflow", "approve"),
    PermissionDef("research:pilot-workflow:create", "创建中试工作流", "research", "pilot-workflow", "create"),
    PermissionDef("research:pilot-workflow:delete", "删除中试工作流", "research", "pilot-workflow", "delete"),
    PermissionDef("research:pilot-workflow:read", "查看中试工作流", "research", "pilot-workflow", "read"),
    PermissionDef("research:pilot-workflow:submit", "提交/流转中试工作流", "research", "pilot-workflow", "submit"),
    PermissionDef("research:process-validation:create", "创建工艺验证", "research", "process-validation", "create"),
    PermissionDef("research:process-validation:delete", "删除工艺验证", "research", "process-validation", "delete"),
    PermissionDef("research:process-validation:read", "查看工艺验证", "research", "process-validation", "read"),
    PermissionDef("research:process-validation:update", "更新工艺验证", "research", "process-validation", "update"),
    PermissionDef("research:project:create", "创建研发项目", "research", "project", "create"),
    PermissionDef("research:project:delete", "删除研发项目", "research", "project", "delete"),
    PermissionDef("research:project:export", "导出研发项目", "research", "project", "export"),
    PermissionDef("research:project:read", "查看研发项目", "research", "project", "read"),
    PermissionDef("research:project:submit", "提交/流转研发项目", "research", "project", "submit"),
    PermissionDef("research:project:update", "更新研发项目", "research", "project", "update"),
    PermissionDef("research:registration-filing:create", "创建注册申报", "research", "registration-filing", "create"),
    PermissionDef("research:registration-filing:delete", "删除注册申报", "research", "registration-filing", "delete"),
    PermissionDef("research:registration-filing:read", "查看注册申报", "research", "registration-filing", "read"),
    PermissionDef("research:registration-filing:update", "更新注册申报", "research", "registration-filing", "update"),
    PermissionDef("research:report:create", "创建研发报告", "research", "report", "create"),
    PermissionDef("research:report:delete", "删除研发报告", "research", "report", "delete"),
    PermissionDef("research:report:read", "查看研发报告", "research", "report", "read"),
    PermissionDef("research:report:update", "更新研发报告", "research", "report", "update"),
    PermissionDef("research:route:create", "创建工艺路线", "research", "route", "create"),
    PermissionDef("research:route:delete", "删除工艺路线", "research", "route", "delete"),
    PermissionDef("research:route:read", "查看工艺路线", "research", "route", "read"),
    PermissionDef("research:route:update", "更新工艺路线", "research", "route", "update"),
    PermissionDef("research:stage-deliverable:create", "创建阶段交付物", "research", "stage-deliverable", "create"),
    PermissionDef("research:stage-deliverable:delete", "删除阶段交付物", "research", "stage-deliverable", "delete"),
    PermissionDef("research:stage-deliverable:read", "查看阶段交付物", "research", "stage-deliverable", "read"),
    PermissionDef("research:stage-deliverable:update", "更新阶段交付物", "research", "stage-deliverable", "update"),
    PermissionDef("research:track:create", "创建研究跟踪", "research", "track", "create"),
    PermissionDef("research:track:delete", "删除研究跟踪", "research", "track", "delete"),
    PermissionDef("research:track:export", "导出研究跟踪", "research", "track", "export"),
    PermissionDef("research:track:read", "查看研究跟踪", "research", "track", "read"),
    PermissionDef("research:track:update", "更新研究跟踪", "research", "track", "update"),
)


# ── 业务模块细粒度权限码：warehouse（仓储管理）─────────────────

WAREHOUSE_PERMISSIONS: tuple[PermissionDef, ...] = (
    PermissionDef("warehouse:raw-material:read", "查看原辅料库存", "warehouse", "raw-material", "read"),
    PermissionDef("warehouse:packaging-material:read", "查看包材库存", "warehouse", "packaging-material", "read"),
    PermissionDef("warehouse:product:read", "查看成品库存", "warehouse", "product", "read"),
    PermissionDef("warehouse:feishu-config:read", "查看仓储飞书配置", "warehouse", "feishu-config", "read"),
    PermissionDef("warehouse:feishu-config:update", "保存仓储飞书配置", "warehouse", "feishu-config", "update"),
    PermissionDef("warehouse:feishu-config:create", "测试仓储飞书连通性", "warehouse", "feishu-config", "create"),
    PermissionDef("warehouse:feishu-table:read", "查看仓储飞书数据表", "warehouse", "feishu-table", "read"),
    PermissionDef("warehouse:feishu-table:create", "刷新仓储飞书数据表目录", "warehouse", "feishu-table", "create"),
    PermissionDef("warehouse:feishu-table:update", "启用/停用仓储飞书数据表", "warehouse", "feishu-table", "update"),
    PermissionDef("warehouse:feishu-table:submit", "同步仓储飞书数据表快照", "warehouse", "feishu-table", "submit"),
    PermissionDef("warehouse:feishu-record:read", "查看仓储飞书记录快照", "warehouse", "feishu-record", "read"),
    PermissionDef("warehouse:feishu-ws:read", "查看仓储飞书 WS 状态", "warehouse", "feishu-ws", "read"),
    PermissionDef("warehouse:feishu-ws:submit", "重启仓储飞书 WS 长连接", "warehouse", "feishu-ws", "submit"),
)

# ── 业务模块细粒度权限码：procurement（采购管理）─────────────────

PROCUREMENT_PERMISSIONS: tuple[PermissionDef, ...] = (
    PermissionDef("procurement:invoice:create", "识别采购发票", "procurement", "invoice", "create"),
    PermissionDef("procurement:supplier:read", "查看供应商清单", "procurement", "supplier", "read"),
    PermissionDef("procurement:supplier:create", "导入供应商清单", "procurement", "supplier", "create"),
    PermissionDef("procurement:invoice-record:read", "查看发票识别记录", "procurement", "invoice-record", "read"),
    PermissionDef("procurement:invoice-record:delete", "删除发票识别记录", "procurement", "invoice-record", "delete"),
    PermissionDef("procurement:purchase-order:read", "查看采购订单", "procurement", "purchase-order", "read"),
    PermissionDef("procurement:purchase-order:export", "导出采购订单", "procurement", "purchase-order", "export"),
    PermissionDef("procurement:purchase-request:read", "查看采购申请", "procurement", "purchase-request", "read"),
    PermissionDef("procurement:purchase-request:create", "创建采购申请", "procurement", "purchase-request", "create"),
    PermissionDef(
        "procurement:purchase-request:update", "更新采购申请", "procurement", "purchase-request", "update"
    ),
    PermissionDef(
        "procurement:purchase-request:submit", "提交/驳回采购申请", "procurement", "purchase-request", "submit"
    ),
    PermissionDef(
        "procurement:purchase-request:approve", "审批采购申请", "procurement", "purchase-request", "approve"
    ),
    PermissionDef("procurement:contract:read", "查看采购合同", "procurement", "contract", "read"),
    PermissionDef("procurement:contract:create", "生成采购合同", "procurement", "contract", "create"),
)

# ── 业务模块细粒度权限码：administration（行政管理）─────────────────

ADMINISTRATION_PERMISSIONS: tuple[PermissionDef, ...] = (
    PermissionDef("administration:vehicle:read", "查看车辆信息", "administration", "vehicle", "read"),
    PermissionDef("administration:vehicle:create", "创建车辆记录", "administration", "vehicle", "create"),
    PermissionDef("administration:vehicle:update", "更新车辆记录", "administration", "vehicle", "update"),
    PermissionDef("administration:vehicle:delete", "删除车辆记录", "administration", "vehicle", "delete"),
)

# ── 业务模块细粒度权限码：energy（能耗管理）─────────────────

ENERGY_PERMISSIONS: tuple[PermissionDef, ...] = (
    # platform（平台信息）
    PermissionDef("energy:platform:read", "查看能耗平台", "energy", "platform", "read"),
    # overview（总览）
    PermissionDef("energy:overview:read", "查看能耗总览", "energy", "overview", "read"),
    # sync（数据同步）
    PermissionDef("energy:sync:create", "执行数据同步", "energy", "sync", "create"),
    # job（异步任务）
    PermissionDef("energy:job:read", "查看异步任务状态", "energy", "job", "read"),
    # target（单耗目标）
    PermissionDef("energy:target:read", "查看单耗目标", "energy", "target", "read"),
    PermissionDef("energy:target:create", "创建单耗目标", "energy", "target", "create"),
    PermissionDef("energy:target:update", "更新单耗目标", "energy", "target", "update"),
    # analysis（AI 分析）
    PermissionDef("energy:analysis:create", "执行 AI 能耗分析", "energy", "analysis", "create"),
    # device（设备配置）
    PermissionDef("energy:device:read", "查看设备配置", "energy", "device", "read"),
    PermissionDef("energy:device:create", "创建设备配置", "energy", "device", "create"),
    PermissionDef("energy:device:update", "更新设备配置", "energy", "device", "update"),
    PermissionDef("energy:device:delete", "删除设备配置", "energy", "device", "delete"),
    # data（能耗数据）
    PermissionDef("energy:data:read", "查看能耗数据", "energy", "data", "read"),
    # collect（采集管理）
    PermissionDef("energy:collect:read", "查看采集日志", "energy", "collect", "read"),
    PermissionDef("energy:collect:create", "手动触发采集", "energy", "collect", "create"),
    # alert-rule（预警规则）
    PermissionDef("energy:alert-rule:read", "查看预警规则", "energy", "alert-rule", "read"),
    PermissionDef("energy:alert-rule:create", "创建预警规则", "energy", "alert-rule", "create"),
    PermissionDef("energy:alert-rule:update", "更新预警规则", "energy", "alert-rule", "update"),
    PermissionDef("energy:alert-rule:delete", "删除预警规则", "energy", "alert-rule", "delete"),
    # alert-record（预警记录）
    PermissionDef("energy:alert-record:read", "查看预警记录", "energy", "alert-record", "read"),
    PermissionDef("energy:alert-record:update", "处理预警记录", "energy", "alert-record", "update"),
    # workshop（车间管理）
    PermissionDef("energy:workshop:read", "查看车间", "energy", "workshop", "read"),
    PermissionDef("energy:workshop:create", "创建车间", "energy", "workshop", "create"),
    PermissionDef("energy:workshop:update", "更新车间", "energy", "workshop", "update"),
    PermissionDef("energy:workshop:delete", "删除车间", "energy", "workshop", "delete"),
    # monthly-record（月度记录）
    PermissionDef("energy:monthly-record:read", "查看月度记录", "energy", "monthly-record", "read"),
    PermissionDef("energy:monthly-record:create", "创建月度记录", "energy", "monthly-record", "create"),
    PermissionDef("energy:monthly-record:delete", "删除月度记录", "energy", "monthly-record", "delete"),
)


# ── 业务模块细粒度权限码：equipment（设备管理）─────────────────

EQUIPMENT_PERMISSIONS: tuple[PermissionDef, ...] = (
    # equipment（设备台账）
    PermissionDef("equipment:equipment:read", "查看设备台账", "equipment", "equipment", "read"),
    PermissionDef("equipment:equipment:create", "创建设备", "equipment", "equipment", "create"),
    PermissionDef("equipment:equipment:update", "更新设备", "equipment", "equipment", "update"),
    PermissionDef("equipment:equipment:delete", "删除设备", "equipment", "equipment", "delete"),
    # batch-import（批量导入）
    PermissionDef("equipment:batch-import:create", "批量导入设备", "equipment", "batch-import", "create"),
    # spare-part（备件管理）
    PermissionDef("equipment:spare-part:read", "查看备件", "equipment", "spare-part", "read"),
    PermissionDef("equipment:spare-part:create", "创建备件", "equipment", "spare-part", "create"),
    PermissionDef("equipment:spare-part:update", "更新备件", "equipment", "spare-part", "update"),
    PermissionDef("equipment:spare-part:delete", "删除备件", "equipment", "spare-part", "delete"),
    # work-order（维修工单）
    PermissionDef("equipment:work-order:read", "查看维修工单", "equipment", "work-order", "read"),
    PermissionDef("equipment:work-order:create", "创建维修工单", "equipment", "work-order", "create"),
    PermissionDef("equipment:work-order:update", "更新维修工单", "equipment", "work-order", "update"),
    PermissionDef("equipment:work-order:manage", "管理维修工单（分配/开始/完成/验证/关闭）", "equipment", "work-order", "manage"),
    # calibration（校准管理）
    PermissionDef("equipment:calibration:read", "查看校准记录", "equipment", "calibration", "read"),
    PermissionDef("equipment:calibration:create", "创建校准记录", "equipment", "calibration", "create"),
    PermissionDef("equipment:calibration:update", "更新校准记录", "equipment", "calibration", "update"),
    PermissionDef("equipment:calibration:delete", "删除校准记录", "equipment", "calibration", "delete"),
    # maintenance-plan（维护计划）
    PermissionDef("equipment:maintenance-plan:read", "查看维护计划", "equipment", "maintenance-plan", "read"),
    PermissionDef("equipment:maintenance-plan:create", "创建维护计划", "equipment", "maintenance-plan", "create"),
    PermissionDef("equipment:maintenance-plan:update", "更新维护计划", "equipment", "maintenance-plan", "update"),
    PermissionDef("equipment:maintenance-plan:delete", "删除维护计划", "equipment", "maintenance-plan", "delete"),
    # inspection-template（巡检模板）
    PermissionDef("equipment:inspection-template:read", "查看巡检模板", "equipment", "inspection-template", "read"),
    PermissionDef("equipment:inspection-template:create", "创建巡检模板", "equipment", "inspection-template", "create"),
    PermissionDef("equipment:inspection-template:update", "更新巡检模板", "equipment", "inspection-template", "update"),
    PermissionDef("equipment:inspection-template:delete", "删除巡检模板", "equipment", "inspection-template", "delete"),
    # failure-code（故障代码）
    PermissionDef("equipment:failure-code:read", "查看故障代码", "equipment", "failure-code", "read"),
    PermissionDef("equipment:failure-code:create", "创建故障代码", "equipment", "failure-code", "create"),
    PermissionDef("equipment:failure-code:update", "更新故障代码", "equipment", "failure-code", "update"),
    PermissionDef("equipment:failure-code:delete", "删除故障代码", "equipment", "failure-code", "delete"),
    # personnel（人员管理）
    PermissionDef("equipment:personnel:read", "查看设备人员", "equipment", "personnel", "read"),
    PermissionDef("equipment:personnel:create", "创建设备人员", "equipment", "personnel", "create"),
    PermissionDef("equipment:personnel:update", "更新设备人员", "equipment", "personnel", "update"),
    PermissionDef("equipment:personnel:delete", "删除设备人员", "equipment", "personnel", "delete"),
    # inspection（巡检管理）
    PermissionDef("equipment:inspection:read", "查看巡检记录", "equipment", "inspection", "read"),
    PermissionDef("equipment:inspection:create", "创建巡检", "equipment", "inspection", "create"),
    PermissionDef("equipment:inspection:update", "更新巡检", "equipment", "inspection", "update"),
    PermissionDef("equipment:inspection:delete", "删除巡检", "equipment", "inspection", "delete"),
    # maintenance-config / maintenance-staff
    PermissionDef("equipment:maintenance-config:read", "查看维护配置", "equipment", "maintenance-config", "read"),
    PermissionDef("equipment:maintenance-config:update", "更新维护配置", "equipment", "maintenance-config", "update"),
    PermissionDef("equipment:maintenance-staff:read", "查看维护人员", "equipment", "maintenance-staff", "read"),
    PermissionDef("equipment:maintenance-staff:update", "刷新维护人员", "equipment", "maintenance-staff", "update"),
    PermissionDef("equipment:work-order:delete", "删除工单附件图片", "equipment", "work-order", "delete"),
    PermissionDef("equipment:inspection:manage", "管理巡检任务（开始/完成/关闭等）", "equipment", "inspection", "manage"),
    PermissionDef("equipment:batch-import:read", "下载导入模板", "equipment", "batch-import", "read"),
)

# ── 业务模块细粒度权限码：registration（注册管理）─────────────────

REGISTRATION_PERMISSIONS: tuple[PermissionDef, ...] = (
    # project（注册项目）
    PermissionDef("registration:project:read", "查看注册项目", "registration", "project", "read"),
    PermissionDef("registration:project:create", "创建注册项目", "registration", "project", "create"),
    PermissionDef("registration:project:update", "更新注册项目", "registration", "project", "update"),
    PermissionDef("registration:project:delete", "删除注册项目", "registration", "project", "delete"),
    # drug（药品申报进度）
    PermissionDef("registration:drug:read", "查看药品申报", "registration", "drug", "read"),
    PermissionDef("registration:drug:create", "创建药品申报", "registration", "drug", "create"),
    PermissionDef("registration:drug:update", "更新药品申报", "registration", "drug", "update"),
    PermissionDef("registration:drug:delete", "删除药品申报", "registration", "drug", "delete"),
    # certificate（注册证书）
    PermissionDef("registration:certificate:read", "查看注册证书", "registration", "certificate", "read"),
    PermissionDef("registration:certificate:create", "创建注册证书", "registration", "certificate", "create"),
    PermissionDef("registration:certificate:update", "更新注册证书", "registration", "certificate", "update"),
    PermissionDef("registration:certificate:delete", "删除注册证书", "registration", "certificate", "delete"),
    # authorization-letter（授权书）
    PermissionDef("registration:authorization-letter:read", "查看授权书", "registration", "authorization-letter", "read"),
    PermissionDef("registration:authorization-letter:create", "生成授权书", "registration", "authorization-letter", "create"),
    PermissionDef("registration:authorization-letter:delete", "删除授权书", "registration", "authorization-letter", "delete"),
    # reference-standard（对照物质说明表）
    PermissionDef("registration:reference-standard:read", "查看对照物质", "registration", "reference-standard", "read"),
    PermissionDef("registration:reference-standard:create", "创建对照物质", "registration", "reference-standard", "create"),
    PermissionDef("registration:reference-standard:delete", "删除对照物质", "registration", "reference-standard", "delete"),
    # reference-substance（对照品说明表）
    PermissionDef("registration:reference-substance:read", "查看对照品", "registration", "reference-substance", "read"),
    PermissionDef("registration:reference-substance:create", "创建对照品", "registration", "reference-substance", "create"),
    PermissionDef("registration:reference-substance:update", "更新对照品", "registration", "reference-substance", "update"),
    PermissionDef("registration:reference-substance:delete", "删除对照品", "registration", "reference-substance", "delete"),
    # supplementary-reply（发补回复）
    PermissionDef("registration:supplementary-reply:read", "查看发补回复", "registration", "supplementary-reply", "read"),
    PermissionDef("registration:supplementary-reply:create", "生成发补回复", "registration", "supplementary-reply", "create"),
    PermissionDef("registration:supplementary-reply:delete", "删除发补回复", "registration", "supplementary-reply", "delete"),
    # holiday（节假日管理）
    PermissionDef("registration:holiday:read", "查看节假日", "registration", "holiday", "read"),
    PermissionDef("registration:holiday:create", "创建节假日", "registration", "holiday", "create"),
    PermissionDef("registration:holiday:update", "更新节假日", "registration", "holiday", "update"),
    PermissionDef("registration:holiday:delete", "删除节假日", "registration", "holiday", "delete"),
    # validation-audit（验证文件审核）
    PermissionDef("registration:validation-audit:read", "查看验证审核", "registration", "validation-audit", "read"),
    PermissionDef("registration:validation-audit:create", "创建验证审核", "registration", "validation-audit", "create"),
    PermissionDef("registration:validation-audit:update", "更新验证审核", "registration", "validation-audit", "update"),
    PermissionDef("registration:validation-audit:delete", "删除验证审核", "registration", "validation-audit", "delete"),
    # dossier（申报资料）
    PermissionDef("registration:dossier:read", "查看申报资料", "registration", "dossier", "read"),
    PermissionDef("registration:dossier:create", "创建申报资料", "registration", "dossier", "create"),
    PermissionDef("registration:dossier:update", "更新申报资料", "registration", "dossier", "update"),
    PermissionDef("registration:dossier:delete", "删除申报资料", "registration", "dossier", "delete"),
    # regulatory-tracker（法规追踪）
    PermissionDef("registration:regulatory-tracker:read", "查看法规追踪", "registration", "regulatory-tracker", "read"),
    PermissionDef("registration:regulatory-tracker:manage", "管理法规追踪同步", "registration", "regulatory-tracker", "manage"),
    # dashboard（注册看板）
    PermissionDef("registration:dashboard:read", "查看注册看板", "registration", "dashboard", "read"),
    # ledger（注册台账-审批记录）
    PermissionDef("registration:approval-record:read", "查看审批记录", "registration", "approval-record", "read"),
    PermissionDef("registration:approval-record:create", "创建审批记录", "registration", "approval-record", "create"),
    PermissionDef("registration:approval-record:delete", "删除审批记录", "registration", "approval-record", "delete"),
)


QUALITY_PERMISSIONS: tuple[PermissionDef, ...] = (
    PermissionDef("quality:capa:approve", "CAPA管理 - 审批", "quality", "capa", "approve"),
    PermissionDef("quality:capa:create", "CAPA管理 - 新增", "quality", "capa", "create"),
    PermissionDef("quality:capa:delete", "CAPA管理 - 删除", "quality", "capa", "delete"),
    PermissionDef("quality:capa:read", "CAPA管理 - 查看", "quality", "capa", "read"),
    PermissionDef("quality:capa:submit", "CAPA管理 - 提交", "quality", "capa", "submit"),
    PermissionDef("quality:capa:update", "CAPA管理 - 编辑", "quality", "capa", "update"),
    PermissionDef("quality:cpv:create", "持续工艺验证(CPV) - 新增", "quality", "cpv", "create"),
    PermissionDef("quality:cpv:delete", "持续工艺验证(CPV) - 删除", "quality", "cpv", "delete"),
    PermissionDef("quality:cpv:import", "持续工艺验证(CPV) - 导入", "quality", "cpv", "import"),
    PermissionDef("quality:cpv:read", "持续工艺验证(CPV) - 查看", "quality", "cpv", "read"),
    PermissionDef("quality:cpv:update", "持续工艺验证(CPV) - 编辑", "quality", "cpv", "update"),
    PermissionDef("quality:deviation-settings:create", "偏差设置 - 新增", "quality", "deviation-settings", "create"),
    PermissionDef("quality:deviation-settings:delete", "偏差设置 - 删除", "quality", "deviation-settings", "delete"),
    PermissionDef("quality:deviation-settings:read", "偏差设置 - 查看", "quality", "deviation-settings", "read"),
    PermissionDef("quality:deviation-settings:update", "偏差设置 - 编辑", "quality", "deviation-settings", "update"),
    PermissionDef("quality:deviation:approve", "偏差管理 - 审批", "quality", "deviation", "approve"),
    PermissionDef("quality:deviation:create", "偏差管理 - 新增", "quality", "deviation", "create"),
    PermissionDef("quality:deviation:delete", "偏差管理 - 删除", "quality", "deviation", "delete"),
    PermissionDef("quality:deviation:read", "偏差管理 - 查看", "quality", "deviation", "read"),
    PermissionDef("quality:deviation:submit", "偏差管理 - 提交", "quality", "deviation", "submit"),
    PermissionDef("quality:deviation:update", "偏差管理 - 编辑", "quality", "deviation", "update"),
    PermissionDef("quality:doc-check:cancel", "文件检查 - 取消", "quality", "doc-check", "cancel"),
    PermissionDef("quality:doc-check:create", "文件检查 - 新增", "quality", "doc-check", "create"),
    PermissionDef("quality:doc-check:delete", "文件检查 - 删除", "quality", "doc-check", "delete"),
    PermissionDef("quality:doc-check:execute", "文件检查 - 执行", "quality", "doc-check", "execute"),
    PermissionDef("quality:doc-check:read", "文件检查 - 查看", "quality", "doc-check", "read"),
    PermissionDef("quality:doc-check:update", "文件检查 - 编辑", "quality", "doc-check", "update"),
    PermissionDef("quality:export:read", "数据导出 - 查看", "quality", "export", "read"),
    PermissionDef("quality:fqc:approve", "FQC成品检验 - 审批", "quality", "fqc", "approve"),
    PermissionDef("quality:fqc:create", "FQC成品检验 - 新增", "quality", "fqc", "create"),
    PermissionDef("quality:fqc:delete", "FQC成品检验 - 删除", "quality", "fqc", "delete"),
    PermissionDef("quality:fqc:read", "FQC成品检验 - 查看", "quality", "fqc", "read"),
    PermissionDef("quality:fqc:submit", "FQC成品检验 - 提交", "quality", "fqc", "submit"),
    PermissionDef("quality:fqc:update", "FQC成品检验 - 编辑", "quality", "fqc", "update"),
    PermissionDef("quality:instrument:approve", "仪器校准 - 审批", "quality", "instrument", "approve"),
    PermissionDef("quality:instrument:create", "仪器校准 - 新增", "quality", "instrument", "create"),
    PermissionDef("quality:instrument:delete", "仪器校准 - 删除", "quality", "instrument", "delete"),
    PermissionDef("quality:instrument:read", "仪器校准 - 查看", "quality", "instrument", "read"),
    PermissionDef("quality:instrument:submit", "仪器校准 - 提交", "quality", "instrument", "submit"),
    PermissionDef("quality:instrument:update", "仪器校准 - 编辑", "quality", "instrument", "update"),
    PermissionDef("quality:ipqc:approve", "IPQC过程检验 - 审批", "quality", "ipqc", "approve"),
    PermissionDef("quality:ipqc:create", "IPQC过程检验 - 新增", "quality", "ipqc", "create"),
    PermissionDef("quality:ipqc:delete", "IPQC过程检验 - 删除", "quality", "ipqc", "delete"),
    PermissionDef("quality:ipqc:read", "IPQC过程检验 - 查看", "quality", "ipqc", "read"),
    PermissionDef("quality:ipqc:submit", "IPQC过程检验 - 提交", "quality", "ipqc", "submit"),
    PermissionDef("quality:ipqc:update", "IPQC过程检验 - 编辑", "quality", "ipqc", "update"),
    PermissionDef("quality:iqc:approve", "IQC来料检验 - 审批", "quality", "iqc", "approve"),
    PermissionDef("quality:iqc:create", "IQC来料检验 - 新增", "quality", "iqc", "create"),
    PermissionDef("quality:iqc:delete", "IQC来料检验 - 删除", "quality", "iqc", "delete"),
    PermissionDef("quality:iqc:read", "IQC来料检验 - 查看", "quality", "iqc", "read"),
    PermissionDef("quality:iqc:submit", "IQC来料检验 - 提交", "quality", "iqc", "submit"),
    PermissionDef("quality:iqc:update", "IQC来料检验 - 编辑", "quality", "iqc", "update"),
    PermissionDef("quality:label-verification:create", "标签复核 - 新增", "quality", "label-verification", "create"),
    PermissionDef("quality:label-verification:read", "标签复核 - 查看", "quality", "label-verification", "read"),
    PermissionDef("quality:label-verification:update", "标签复核 - 编辑", "quality", "label-verification", "update"),
    PermissionDef("quality:label-verification:delete", "标签复核 - 删除", "quality", "label-verification", "delete"),
    PermissionDef("quality:material-report:create", "原料报告单 - 新增", "quality", "material-report", "create"),
    PermissionDef("quality:material-report:delete", "原料报告单 - 删除", "quality", "material-report", "delete"),
    PermissionDef("quality:material-report:read", "原料报告单 - 查看", "quality", "material-report", "read"),
    PermissionDef("quality:material-report:submit", "原料报告单 - 提交", "quality", "material-report", "submit"),
    PermissionDef("quality:material-report:update", "原料报告单 - 编辑", "quality", "material-report", "update"),
    PermissionDef("quality:problem:create", "问题管理 - 新增", "quality", "problem", "create"),
    PermissionDef("quality:problem:read", "问题管理 - 查看", "quality", "problem", "read"),
    PermissionDef("quality:problem:update", "问题管理 - 编辑", "quality", "problem", "update"),
    PermissionDef("quality:reagent-reminder:create", "试剂提醒 - 新增", "quality", "reagent-reminder", "create"),
    PermissionDef("quality:reagent-reminder:read", "试剂提醒 - 查看", "quality", "reagent-reminder", "read"),
    PermissionDef("quality:reagent:create", "试剂管理 - 新增", "quality", "reagent", "create"),
    PermissionDef("quality:reagent:delete", "试剂管理 - 删除", "quality", "reagent", "delete"),
    PermissionDef("quality:reagent:export", "试剂管理 - 导出", "quality", "reagent", "export"),
    PermissionDef("quality:reagent:read", "试剂管理 - 查看", "quality", "reagent", "read"),
    PermissionDef("quality:reagent:update", "试剂管理 - 编辑", "quality", "reagent", "update"),
    PermissionDef("quality:record:read", "校验记录 - 查看", "quality", "record", "read"),
    PermissionDef("quality:sampling:approve", "取样管理 - 审批", "quality", "sampling", "approve"),
    PermissionDef("quality:sampling:create", "取样管理 - 新增", "quality", "sampling", "create"),
    PermissionDef("quality:sampling:delete", "取样管理 - 删除", "quality", "sampling", "delete"),
    PermissionDef("quality:sampling:read", "取样管理 - 查看", "quality", "sampling", "read"),
    PermissionDef("quality:sampling:submit", "取样管理 - 提交", "quality", "sampling", "submit"),
    PermissionDef("quality:sampling:update", "取样管理 - 编辑", "quality", "sampling", "update"),
    PermissionDef("quality:sop-ai:create", "SOP AI文件校验 - 新增", "quality", "sop-ai", "create"),
    PermissionDef("quality:sop-ai:delete", "SOP AI文件校验 - 删除", "quality", "sop-ai", "delete"),
    PermissionDef("quality:sop-ai:export", "SOP AI文件校验 - 导出", "quality", "sop-ai", "export"),
    PermissionDef("quality:sop-ai:read", "SOP AI文件校验 - 查看", "quality", "sop-ai", "read"),
    PermissionDef("quality:sop-ai:update", "SOP AI文件校验 - 编辑", "quality", "sop-ai", "update"),
    PermissionDef("quality:stability:approve", "稳定性试验 - 审批", "quality", "stability", "approve"),
    PermissionDef("quality:stability:create", "稳定性试验 - 新增", "quality", "stability", "create"),
    PermissionDef("quality:stability:delete", "稳定性试验 - 删除", "quality", "stability", "delete"),
    PermissionDef("quality:stability:read", "稳定性试验 - 查看", "quality", "stability", "read"),
    PermissionDef("quality:stability:submit", "稳定性试验 - 提交", "quality", "stability", "submit"),
    PermissionDef("quality:stability:update", "稳定性试验 - 编辑", "quality", "stability", "update"),
    PermissionDef("quality:standard:create", "检验标准 - 新增", "quality", "standard", "create"),
    PermissionDef("quality:standard:read", "检验标准 - 查看", "quality", "standard", "read"),
    PermissionDef("quality:static-data:create", "静态数据 - 新增", "quality", "static-data", "create"),
    PermissionDef("quality:static-data:delete", "静态数据 - 删除", "quality", "static-data", "delete"),
    PermissionDef("quality:static-data:read", "静态数据 - 查看", "quality", "static-data", "read"),
    PermissionDef("quality:static-data:update", "静态数据 - 编辑", "quality", "static-data", "update"),
)

HR_PERMISSIONS: tuple[PermissionDef, ...] = (
    PermissionDef("hr:ai-exam:export", "AI出题 - 导出", "hr", "ai-exam", "export"),
    PermissionDef("hr:ai-exam:generate", "AI出题 - 生成", "hr", "ai-exam", "generate"),
    PermissionDef("hr:annual-training-plans:create", "年度培训计划 - 新增", "hr", "annual-training-plans", "create"),
    PermissionDef("hr:annual-training-plans:delete", "年度培训计划 - 删除", "hr", "annual-training-plans", "delete"),
    PermissionDef("hr:annual-training-plans:export", "年度培训计划 - 导出", "hr", "annual-training-plans", "export"),
    PermissionDef("hr:annual-training-plans:read", "年度培训计划 - 查看", "hr", "annual-training-plans", "read"),
    PermissionDef("hr:annual-training-plans:update", "年度培训计划 - 编辑", "hr", "annual-training-plans", "update"),
    PermissionDef("hr:candidates:create", "候选人管理 - 新增", "hr", "candidates", "create"),
    PermissionDef("hr:candidates:delete", "候选人管理 - 删除", "hr", "candidates", "delete"),
    PermissionDef("hr:candidates:read", "候选人管理 - 查看", "hr", "candidates", "read"),
    PermissionDef("hr:candidates:sync", "候选人管理 - 同步", "hr", "candidates", "sync"),
    PermissionDef("hr:candidates:update", "候选人管理 - 编辑", "hr", "candidates", "update"),
    PermissionDef("hr:departments:create", "部门管理 - 新增", "hr", "departments", "create"),
    PermissionDef("hr:departments:delete", "部门管理 - 删除", "hr", "departments", "delete"),
    PermissionDef("hr:departments:read", "部门管理 - 查看", "hr", "departments", "read"),
    PermissionDef("hr:departments:update", "部门管理 - 编辑", "hr", "departments", "update"),
    PermissionDef("hr:departure-records:create", "离职记录 - 新增", "hr", "departure-records", "create"),
    PermissionDef("hr:departure-records:delete", "离职记录 - 删除", "hr", "departure-records", "delete"),
    PermissionDef("hr:departure-records:read", "离职记录 - 查看", "hr", "departure-records", "read"),
    PermissionDef("hr:departure-records:sync", "离职记录 - 同步", "hr", "departure-records", "sync"),
    PermissionDef("hr:departure-records:update", "离职记录 - 编辑", "hr", "departure-records", "update"),
    PermissionDef("hr:employees:create", "员工管理 - 新增", "hr", "employees", "create"),
    PermissionDef("hr:employees:delete", "员工管理 - 删除", "hr", "employees", "delete"),
    PermissionDef("hr:employees:read", "员工管理 - 查看", "hr", "employees", "read"),
    PermissionDef("hr:employees:sync", "员工管理 - 同步", "hr", "employees", "sync"),
    PermissionDef("hr:employees:update", "员工管理 - 编辑", "hr", "employees", "update"),
    PermissionDef("hr:new-departments:read", "新部门 - 查看", "hr", "new-departments", "read"),
    PermissionDef("hr:new-departure-records:read", "新离职记录 - 查看", "hr", "new-departure-records", "read"),
    PermissionDef("hr:new-employees:read", "新员工 - 查看", "hr", "new-employees", "read"),
    PermissionDef("hr:new-offboarding-records:read", "新离岗记录 - 查看", "hr", "new-offboarding-records", "read"),
    PermissionDef("hr:new-onboarding-records:read", "新入职记录 - 查看", "hr", "new-onboarding-records", "read"),
    PermissionDef("hr:offboarding-records:create", "离岗记录 - 新增", "hr", "offboarding-records", "create"),
    PermissionDef("hr:offboarding-records:delete", "离岗记录 - 删除", "hr", "offboarding-records", "delete"),
    PermissionDef("hr:offboarding-records:read", "离岗记录 - 查看", "hr", "offboarding-records", "read"),
    PermissionDef("hr:offboarding-records:update", "离岗记录 - 编辑", "hr", "offboarding-records", "update"),
    PermissionDef("hr:onboarding-evaluation:create", "上岗评估 - 新增", "hr", "onboarding-evaluation", "create"),
    PermissionDef("hr:onboarding-records:read", "入职记录 - 查看", "hr", "onboarding-records", "read"),
    PermissionDef("hr:onboarding-records:sync", "入职记录 - 同步", "hr", "onboarding-records", "sync"),
    PermissionDef("hr:prejob-training-templates:read", "岗前培训模板 - 查看", "hr", "prejob-training-templates", "read"),
    PermissionDef("hr:prejob-training-templates:update", "岗前培训模板 - 编辑", "hr", "prejob-training-templates", "update"),
    PermissionDef("hr:system-settings:read", "系统设置 - 查看", "hr", "system-settings", "read"),
    PermissionDef("hr:system-settings:update", "系统设置 - 编辑", "hr", "system-settings", "update"),
    PermissionDef("hr:teams:create", "班组管理 - 新增", "hr", "teams", "create"),
    PermissionDef("hr:teams:delete", "班组管理 - 删除", "hr", "teams", "delete"),
    PermissionDef("hr:teams:read", "班组管理 - 查看", "hr", "teams", "read"),
    PermissionDef("hr:teams:update", "班组管理 - 编辑", "hr", "teams", "update"),
    PermissionDef("hr:training-evaluation:create", "培训评估 - 新增", "hr", "training-evaluation", "create"),
    PermissionDef("hr:training-ledgers:create", "培训台账 - 新增", "hr", "training-ledgers", "create"),
    PermissionDef("hr:training-ledgers:delete", "培训台账 - 删除", "hr", "training-ledgers", "delete"),
    PermissionDef("hr:training-ledgers:export", "培训台账 - 导出", "hr", "training-ledgers", "export"),
    PermissionDef("hr:training-ledgers:read", "培训台账 - 查看", "hr", "training-ledgers", "read"),
    PermissionDef("hr:training-ledgers:update", "培训台账 - 编辑", "hr", "training-ledgers", "update"),
    PermissionDef("hr:training-notification:create", "培训通知 - 新增", "hr", "training-notification", "create"),
    PermissionDef("hr:training-notifications:create", "培训通知 - 新增", "hr", "training-notifications", "create"),
    PermissionDef("hr:training-select-tasks:create", "培训选课 - 新增", "hr", "training-select-tasks", "create"),
    PermissionDef("hr:training-select-tasks:read", "培训选课 - 查看", "hr", "training-select-tasks", "read"),
    PermissionDef("hr:training-select-tasks:update", "培训选课 - 编辑", "hr", "training-select-tasks", "update"),
    PermissionDef("hr:training-sessions:create", "培训课程 - 新增", "hr", "training-sessions", "create"),
    PermissionDef("hr:training-sessions:delete", "培训课程 - 删除", "hr", "training-sessions", "delete"),
    PermissionDef("hr:training-sessions:read", "培训课程 - 查看", "hr", "training-sessions", "read"),
    PermissionDef("hr:training-sessions:update", "培训课程 - 编辑", "hr", "training-sessions", "update"),
    PermissionDef("hr:training-sign-in-sheet:create", "培训签到表 - 新增", "hr", "training-sign-in-sheet", "create"),
    PermissionDef("hr:training-specialists:create", "培训专员 - 新增", "hr", "training-specialists", "create"),
    PermissionDef("hr:training-specialists:delete", "培训专员 - 删除", "hr", "training-specialists", "delete"),
    PermissionDef("hr:training-specialists:read", "培训专员 - 查看", "hr", "training-specialists", "read"),
    PermissionDef("hr:training-specialists:sync", "培训专员 - 同步", "hr", "training-specialists", "sync"),
    PermissionDef("hr:training-teams:create", "培训班组 - 新增", "hr", "training-teams", "create"),
    PermissionDef("hr:training-teams:delete", "培训班组 - 删除", "hr", "training-teams", "delete"),
    PermissionDef("hr:training-teams:read", "培训班组 - 查看", "hr", "training-teams", "read"),
    PermissionDef("hr:training-teams:update", "培训班组 - 编辑", "hr", "training-teams", "update"),
    PermissionDef("hr:turnover-analysis:read", "流失率分析 - 查看", "hr", "turnover-analysis", "read"),
    PermissionDef("hr:webhook:create", "飞书回调 - 新增", "hr", "webhook", "create"),
)

PRODUCTION_PERMISSIONS: tuple[PermissionDef, ...] = (
    PermissionDef("production:batches:create", "生产批次 - 新增", "production", "batches", "create"),
    PermissionDef("production:batches:delete", "生产批次 - 删除", "production", "batches", "delete"),
    PermissionDef("production:batches:read", "生产批次 - 查看", "production", "batches", "read"),
    PermissionDef("production:batches:update", "生产批次 - 编辑", "production", "batches", "update"),
    PermissionDef("production:materials:delete", "批次物料 - 删除", "production", "materials", "delete"),
    PermissionDef("production:materials:update", "批次物料 - 编辑", "production", "materials", "update"),
    PermissionDef("production:parameters:create", "工艺参数 - 新增", "production", "parameters", "create"),
    PermissionDef("production:parameters:delete", "工艺参数 - 删除", "production", "parameters", "delete"),
    PermissionDef("production:plans:create", "生产计划 - 新增", "production", "plans", "create"),
    PermissionDef("production:plans:delete", "生产计划 - 删除", "production", "plans", "delete"),
    PermissionDef("production:plans:read", "生产计划 - 查看", "production", "plans", "read"),
    PermissionDef("production:plans:update", "生产计划 - 编辑", "production", "plans", "update"),
    PermissionDef("production:pressure-audit:read", "压差审核 - 查看", "production", "pressure-audit", "read"),
    PermissionDef("production:pressure-dashboard:read", "压差仪表盘 - 查看", "production", "pressure-dashboard", "read"),
    PermissionDef("production:pressure-data-master:create", "压差数据管理 - 新增", "production", "pressure-data-master", "create"),
    PermissionDef("production:pressure-data-master:delete", "压差数据管理 - 删除", "production", "pressure-data-master", "delete"),
    PermissionDef("production:pressure-data-master:read", "压差数据管理 - 查看", "production", "pressure-data-master", "read"),
    PermissionDef("production:pressure-data-master:update", "压差数据管理 - 编辑", "production", "pressure-data-master", "update"),
    PermissionDef("production:pressure-notifications:read", "压差通知 - 查看", "production", "pressure-notifications", "read"),
    PermissionDef("production:pressure-notifications:update", "压差通知 - 编辑", "production", "pressure-notifications", "update"),
    PermissionDef("production:pressure-ocr-tasks:create", "压差OCR任务 - 新增", "production", "pressure-ocr-tasks", "create"),
    PermissionDef("production:pressure-ocr-tasks:read", "压差OCR任务 - 查看", "production", "pressure-ocr-tasks", "read"),
    PermissionDef("production:pressure-ocr-tasks:update", "压差OCR任务 - 编辑", "production", "pressure-ocr-tasks", "update"),
    PermissionDef("production:pressure-point-mappings:create", "压差点位映射 - 新增", "production", "pressure-point-mappings", "create"),
    PermissionDef("production:pressure-point-mappings:delete", "压差点位映射 - 删除", "production", "pressure-point-mappings", "delete"),
    PermissionDef("production:pressure-point-mappings:read", "压差点位映射 - 查看", "production", "pressure-point-mappings", "read"),
    PermissionDef("production:pressure-point-mappings:update", "压差点位映射 - 编辑", "production", "pressure-point-mappings", "update"),
    PermissionDef("production:pressure-records:create", "压差记录 - 新增", "production", "pressure-records", "create"),
    PermissionDef("production:pressure-records:delete", "压差记录 - 删除", "production", "pressure-records", "delete"),
    PermissionDef("production:pressure-records:export", "压差记录 - 导出", "production", "pressure-records", "export"),
    PermissionDef("production:pressure-records:read", "压差记录 - 查看", "production", "pressure-records", "read"),
    PermissionDef("production:pressure-records:update", "压差记录 - 编辑", "production", "pressure-records", "update"),
    PermissionDef("production:process-specs:create", "工艺规程 - 新增", "production", "process-specs", "create"),
    PermissionDef("production:process-specs:delete", "工艺规程 - 删除", "production", "process-specs", "delete"),
    PermissionDef("production:process-specs:read", "工艺规程 - 查看", "production", "process-specs", "read"),
    PermissionDef("production:process-specs:update", "工艺规程 - 编辑", "production", "process-specs", "update"),
    PermissionDef("production:product-output:create", "产量记录 - 新增", "production", "product-output", "create"),
    PermissionDef("production:product-output:delete", "产量记录 - 删除", "production", "product-output", "delete"),
    PermissionDef("production:product-output:export", "产量记录 - 导出", "production", "product-output", "export"),
    PermissionDef("production:product-output:import", "产量记录 - 导入", "production", "product-output", "import"),
    PermissionDef("production:product-output:read", "产量记录 - 查看", "production", "product-output", "read"),
    PermissionDef("production:product-output:update", "产量记录 - 编辑", "production", "product-output", "update"),
    PermissionDef("production:product-sync-config:create", "同步配置 - 新增", "production", "product-sync-config", "create"),
    PermissionDef("production:product-sync-config:delete", "同步配置 - 删除", "production", "product-sync-config", "delete"),
    PermissionDef("production:product-sync-config:read", "同步配置 - 查看", "production", "product-sync-config", "read"),
    PermissionDef("production:product-sync-config:sync", "同步配置 - 同步", "production", "product-sync-config", "sync"),
    PermissionDef("production:product-sync-config:update", "同步配置 - 编辑", "production", "product-sync-config", "update"),
    PermissionDef("production:products:create", "产品定义 - 新增", "production", "products", "create"),
    PermissionDef("production:products:delete", "产品定义 - 删除", "production", "products", "delete"),
    PermissionDef("production:products:read", "产品定义 - 查看", "production", "products", "read"),
    PermissionDef("production:products:update", "产品定义 - 编辑", "production", "products", "update"),
    PermissionDef("production:records:create", "生产记录 - 新增", "production", "records", "create"),
    PermissionDef("production:records:delete", "生产记录 - 删除", "production", "records", "delete"),
    PermissionDef("production:records:update", "生产记录 - 编辑", "production", "records", "update"),
    PermissionDef("production:steps:create", "工艺步骤 - 新增", "production", "steps", "create"),
    PermissionDef("production:steps:delete", "工艺步骤 - 删除", "production", "steps", "delete"),
    PermissionDef("production:steps:read", "工艺步骤 - 查看", "production", "steps", "read"),
    PermissionDef("production:steps:update", "工艺步骤 - 编辑", "production", "steps", "update"),
    PermissionDef("production:tasks:create", "生产任务 - 新增", "production", "tasks", "create"),
    PermissionDef("production:tasks:delete", "生产任务 - 删除", "production", "tasks", "delete"),
    PermissionDef("production:tasks:update", "生产任务 - 编辑", "production", "tasks", "update"),
)



# 全部权限码（业务模块接入存量接口时，把业务权限码合并进来即可，权限树会自动生长）
ALL_PERMISSIONS: tuple[PermissionDef, ...] = (
    PLATFORM_PERMISSIONS + BUSINESS_MODULE_PERMISSIONS + RESEARCH_PERMISSIONS + WAREHOUSE_PERMISSIONS + PROCUREMENT_PERMISSIONS + ADMINISTRATION_PERMISSIONS + ENERGY_PERMISSIONS + EQUIPMENT_PERMISSIONS + REGISTRATION_PERMISSIONS + QUALITY_PERMISSIONS + HR_PERMISSIONS + PRODUCTION_PERMISSIONS
)


# ── 内置角色 ──────────────────────────────────────────────────────
# 内置角色**只保留超级管理员**（2026-10-13 按需求精简）：
# 原先的 48 个模块角色（{module}:{admin|operator|approver|viewer}）与
# permission_admin / config_admin 已下线，不再由注册表声明。
#
# 需要其他角色时，由管理员在「权限管理 → 角色管理」里**自建**（可勾选权限码）。

PLATFORM_ROLES: tuple[RoleDef, ...] = (
    RoleDef(
        code="super_admin",
        name="超级管理员",
        category="platform",
        module_code=None,
        description="拥有全部权限，判定时直接放行",
        is_superuser=True,
    ),
)

ALL_BUILTIN_ROLES: tuple[RoleDef, ...] = PLATFORM_ROLES


# ── 内置角色 → 权限码映射 ──────────────────────────────────────────
# super_admin 通过 is_superuser 直接放行，不在此绑定权限码。
# 其余内置角色已下线（2026-10-13），故此处为空：其他角色的权限由管理员
# 自建角色时在权限树上勾选，写入 permission.role_permissions。

BUILTIN_ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {}


# ── 接口绑定登记簿（首批：平台管理接口）────────────────────────────
# route_template 不含参数值，路径参数用 {name} 占位，与 FastAPI 路由模板对齐。

API_BINDINGS: tuple[ApiBindingDef, ...] = (
    # 用户管理
    ApiBindingDef("platform:user:read", "GET", "/api/v1/identity/users"),
    ApiBindingDef("platform:user:manage", "POST", "/api/v1/identity/users"),
    ApiBindingDef("platform:user:manage", "PUT", "/api/v1/identity/users/{id}"),
    ApiBindingDef("platform:user:manage", "POST", "/api/v1/identity/users/{id}/reset-password"),
    ApiBindingDef("platform:user:manage", "POST", "/api/v1/identity/users/{id}/bind-feishu"),
    ApiBindingDef("platform:user:manage", "DELETE", "/api/v1/identity/users/{id}/bind-feishu"),
    # 会话管理（在线会话 / 踢下线）
    ApiBindingDef("platform:user:read", "GET", "/api/v1/identity/sessions"),
    ApiBindingDef("platform:user:manage", "DELETE", "/api/v1/identity/sessions/{jti}"),
    ApiBindingDef("platform:user:manage", "DELETE", "/api/v1/identity/users/{id}/sessions"),
    # 组织架构 / 人员名单（平台用户读权限即可）
    ApiBindingDef("platform:user:read", "GET", "/api/v1/identity/departments"),
    ApiBindingDef("platform:user:read", "GET", "/api/v1/identity/departments/{dept_id}"),
    ApiBindingDef("platform:user:read", "GET", "/api/v1/identity/personnel"),
    # 登录记录（审计类）
    ApiBindingDef("platform:audit:read", "GET", "/api/v1/identity/login-logs"),
    # 操作审计
    ApiBindingDef("platform:audit:read", "GET", "/api/v1/audit/logs"),
    # Livzon 助手飞书配置与通讯录同步
    ApiBindingDef("platform:config:read", "GET", "/api/v1/identity/feishu-config"),
    ApiBindingDef("platform:config:manage", "PUT", "/api/v1/identity/feishu-config"),
    ApiBindingDef("platform:config:manage", "POST", "/api/v1/identity/feishu-config/test"),
    ApiBindingDef("platform:config:manage", "POST", "/api/v1/identity/sync/departments"),
    ApiBindingDef("platform:config:manage", "POST", "/api/v1/identity/sync/members"),
    ApiBindingDef("platform:config:manage", "POST", "/api/v1/identity/sync/all"),
    # 角色管理
    ApiBindingDef("platform:role:read", "GET", "/api/v1/permission/roles"),
    ApiBindingDef("platform:role:manage", "POST", "/api/v1/permission/roles"),
    ApiBindingDef("platform:role:manage", "PUT", "/api/v1/permission/roles/{id}"),
    ApiBindingDef("platform:role:manage", "DELETE", "/api/v1/permission/roles/{id}"),
    # 权限目录
    ApiBindingDef("platform:permission:read", "GET", "/api/v1/permission/permissions"),
    # 权限树只服务于「角色管理」勾选权限，跟随 role:read（与端点 require_permission 对齐）
    ApiBindingDef("platform:role:read", "GET", "/api/v1/permission/tree"),
    ApiBindingDef("platform:api-binding:read", "GET", "/api/v1/permission/api-bindings"),
    # 授权管理
    ApiBindingDef("platform:grant:read", "GET", "/api/v1/permission/departments"),
    ApiBindingDef("platform:grant:read", "GET", "/api/v1/permission/grants"),
    ApiBindingDef("platform:grant:read", "GET", "/api/v1/permission/preview/{user_id}"),
    ApiBindingDef("platform:grant:manage", "POST", "/api/v1/permission/grants"),
    ApiBindingDef("platform:grant:manage", "PUT", "/api/v1/permission/grants/{id}"),
    ApiBindingDef("platform:grant:manage", "DELETE", "/api/v1/permission/grants/{id}"),
    # 当前用户权限（登录用户自取）
    ApiBindingDef("platform:permission:read", "GET", "/api/v1/permission/my-permissions"),
    # 系统运维
    ApiBindingDef("platform:ops:read", "GET", "/api/v1/system/health"),
    ApiBindingDef("platform:ops:read", "GET", "/api/v1/system/info"),
    ApiBindingDef("platform:ops:read", "GET", "/api/v1/system/resources"),
    ApiBindingDef("platform:ops:read", "GET", "/api/v1/system/redis"),
    ApiBindingDef("platform:ops:read", "GET", "/api/v1/system/redis/keys"),
    ApiBindingDef("platform:ops:manage", "DELETE", "/api/v1/system/redis/keys"),
    ApiBindingDef("platform:ops:read", "GET", "/api/v1/system/scheduled-tasks"),
    ApiBindingDef("platform:ops:manage", "PUT", "/api/v1/system/scheduled-tasks/{name}/toggle"),
    ApiBindingDef("platform:ops:read", "GET", "/api/v1/system/modules"),
    # API 启停开关
    ApiBindingDef("platform:ops:read", "GET", "/api/v1/system/api-routes"),
    ApiBindingDef("platform:ops:manage", "PUT", "/api/v1/system/api-routes/switch"),
    # 日志管理
    ApiBindingDef("platform:ops:read", "GET", "/api/v1/system/logs"),
    ApiBindingDef("platform:ops:manage", "DELETE", "/api/v1/system/logs"),
    # 数据库信息（只读：概览 + 表清单 + 表字段结构）
    ApiBindingDef("platform:ops:read", "GET", "/api/v1/system/db/tables"),
    ApiBindingDef(
        "platform:ops:read",
        "GET",
        "/api/v1/system/db/tables/{schema}/{table}/columns",
    ),
    # 菜单栏管理（显隐 / 权重 / 权限绑定 / 自定义菜单项）
    ApiBindingDef("platform:ops:manage", "PUT", "/api/v1/system/menus/config"),
    # create_module_router 注册的是 GET "/" → 实际路径带尾斜杠；中间件在路由重定向前执行，两种写法都要登记
    ApiBindingDef("research:module:read", "GET", "/api/v1/research"),
    ApiBindingDef("research:module:read", "GET", "/api/v1/research/"),
    ApiBindingDef(
        "research:deliverable-template:delete", "DELETE", "/api/v1/research/deliverable-templates/{template_id}"
    ),
    ApiBindingDef("research:experiment-log:delete", "DELETE", "/api/v1/research/experiment-logs/{log_id}"),
    ApiBindingDef("research:route:delete", "DELETE", "/api/v1/research/experiments/{exp_id}"),
    ApiBindingDef("research:track:delete", "DELETE", "/api/v1/research/findings/{finding_id}"),
    ApiBindingDef("research:ich:delete", "DELETE", "/api/v1/research/ich/records/{record_id}"),
    ApiBindingDef("research:initiation:delete", "DELETE", "/api/v1/research/initiations/{initiation_id}"),
    ApiBindingDef("research:optimization:delete", "DELETE", "/api/v1/research/optimizations/{optimization_id}"),
    ApiBindingDef("research:pilot-workflow:delete", "DELETE", "/api/v1/research/pilot/workflow/{workflow_id}"),
    ApiBindingDef("research:track:delete", "DELETE", "/api/v1/research/projects/tracks/{track_id}"),
    ApiBindingDef("research:project:delete", "DELETE", "/api/v1/research/projects/{project_id}"),
    ApiBindingDef("research:pilot-study:delete", "DELETE", "/api/v1/research/rd-pilot-studies/{study_id}"),
    ApiBindingDef(
        "research:process-validation:delete", "DELETE", "/api/v1/research/rd-process-validations/{validation_id}"
    ),
    ApiBindingDef("research:project:delete", "DELETE", "/api/v1/research/rd-projects/{project_id}"),
    ApiBindingDef(
        "research:registration-filing:delete", "DELETE", "/api/v1/research/rd-registration-filings/{filing_id}"
    ),
    ApiBindingDef(
        "research:stage-deliverable:delete", "DELETE", "/api/v1/research/rd-stage-deliverables/{deliverable_id}"
    ),
    ApiBindingDef("research:report:delete", "DELETE", "/api/v1/research/reports/{report_id}"),
    ApiBindingDef("research:route:delete", "DELETE", "/api/v1/research/routes/{route_id}"),
    ApiBindingDef("research:deliverable-template:read", "GET", "/api/v1/research/deliverable-templates"),
    ApiBindingDef("research:experiment-log:read", "GET", "/api/v1/research/experiment-logs"),
    ApiBindingDef("research:experiment-log:export", "GET", "/api/v1/research/export/experiment-logs"),
    ApiBindingDef("research:project:export", "GET", "/api/v1/research/export/projects"),
    ApiBindingDef("research:track:export", "GET", "/api/v1/research/export/tracks"),
    ApiBindingDef("research:ich:read", "GET", "/api/v1/research/ich/records"),
    ApiBindingDef("research:ich:read", "GET", "/api/v1/research/ich/records/{record_id}"),
    ApiBindingDef("research:initiation:read", "GET", "/api/v1/research/initiations"),
    ApiBindingDef("research:optimization:read", "GET", "/api/v1/research/optimizations"),
    ApiBindingDef("research:optimization:read", "GET", "/api/v1/research/optimizations/{optimization_id}"),
    ApiBindingDef("research:pilot-study:read", "GET", "/api/v1/research/pilot-studies"),
    ApiBindingDef("research:pilot-workflow:read", "GET", "/api/v1/research/pilot/workflow"),
    ApiBindingDef("research:pilot-workflow:read", "GET", "/api/v1/research/pilot/workflow/{workflow_id}"),
    ApiBindingDef(
        "research:pilot-workflow:read", "GET", "/api/v1/research/pilot/workflow/{workflow_id}/steps/{step_id}"
    ),
    ApiBindingDef("research:process-validation:read", "GET", "/api/v1/research/process-validations"),
    ApiBindingDef("research:project:read", "GET", "/api/v1/research/projects"),
    ApiBindingDef("research:project:read", "GET", "/api/v1/research/projects/{project_id}"),
    ApiBindingDef("research:project:read", "GET", "/api/v1/research/projects/{project_id}/milestones"),
    ApiBindingDef("research:project:read", "GET", "/api/v1/research/projects/{project_id}/stages"),
    ApiBindingDef("research:project:read", "GET", "/api/v1/research/projects/{project_id}/tracks"),
    ApiBindingDef("research:pilot-study:read", "GET", "/api/v1/research/rd-pilot-studies"),
    ApiBindingDef("research:process-validation:read", "GET", "/api/v1/research/rd-process-validations"),
    ApiBindingDef("research:project:read", "GET", "/api/v1/research/rd-projects"),
    ApiBindingDef("research:project:read", "GET", "/api/v1/research/rd-projects/{project_id}"),
    ApiBindingDef("research:project:read", "GET", "/api/v1/research/rd-projects/{project_id}/transition-check"),
    ApiBindingDef("research:registration-filing:read", "GET", "/api/v1/research/rd-registration-filings"),
    ApiBindingDef("research:stage-deliverable:read", "GET", "/api/v1/research/rd-stage-deliverables"),
    ApiBindingDef("research:stage-deliverable:read", "GET", "/api/v1/research/rd-stage-deliverables/{deliverable_id}"),
    ApiBindingDef(
        "research:stage-deliverable:read", "GET", "/api/v1/research/rd-stage-deliverables/{deliverable_id}/download"
    ),
    ApiBindingDef("research:registration-filing:read", "GET", "/api/v1/research/registration-filings"),
    ApiBindingDef("research:report:read", "GET", "/api/v1/research/reports"),
    ApiBindingDef("research:route:read", "GET", "/api/v1/research/routes"),
    ApiBindingDef("research:route:read", "GET", "/api/v1/research/routes/{route_id}"),
    ApiBindingDef("research:project:read", "GET", "/api/v1/research/stats/overview"),
    ApiBindingDef("research:project:read", "GET", "/api/v1/research/stats/project-progress"),
    ApiBindingDef("research:track:read", "GET", "/api/v1/research/tracks"),
    ApiBindingDef("research:track:read", "GET", "/api/v1/research/tracks/{track_id}"),
    ApiBindingDef("research:track:read", "GET", "/api/v1/research/tracks/{track_id}/conclusion-versions"),
    ApiBindingDef("research:track:read", "GET", "/api/v1/research/tracks/{track_id}/conclusions"),
    ApiBindingDef("research:track:read", "GET", "/api/v1/research/tracks/{track_id}/findings"),
    ApiBindingDef("research:deliverable-template:create", "POST", "/api/v1/research/deliverable-templates"),
    ApiBindingDef("research:optimization:create", "POST", "/api/v1/research/edbo/generate-scope"),
    ApiBindingDef("research:optimization:create", "POST", "/api/v1/research/edbo/optimize"),
    ApiBindingDef("research:experiment-log:create", "POST", "/api/v1/research/experiment-logs"),
    ApiBindingDef("research:report:create", "POST", "/api/v1/research/generate-report"),
    ApiBindingDef("research:ich:create", "POST", "/api/v1/research/ich/analyze"),
    ApiBindingDef("research:ich:create", "POST", "/api/v1/research/ich/q3c/analyze"),
    ApiBindingDef("research:initiation:create", "POST", "/api/v1/research/initiations"),
    ApiBindingDef("research:literature:create", "POST", "/api/v1/research/literature/analyze"),
    ApiBindingDef("research:optimization:create", "POST", "/api/v1/research/optimizations"),
    ApiBindingDef("research:pilot-study:create", "POST", "/api/v1/research/pilot-studies"),
    ApiBindingDef("research:pilot-workflow:create", "POST", "/api/v1/research/pilot/workflow"),
    ApiBindingDef("research:pilot-workflow:approve", "POST", "/api/v1/research/pilot/workflow/{workflow_id}/approve"),
    ApiBindingDef("research:pilot-workflow:submit", "POST", "/api/v1/research/pilot/workflow/{workflow_id}/start"),
    ApiBindingDef("research:pilot-workflow:create", "POST", "/api/v1/research/pilot/workflow/{workflow_id}/upload"),
    ApiBindingDef("research:process-validation:create", "POST", "/api/v1/research/process-validations"),
    ApiBindingDef("research:project:create", "POST", "/api/v1/research/projects"),
    ApiBindingDef("research:project:create", "POST", "/api/v1/research/projects/{project_id}/milestones"),
    ApiBindingDef("research:project:create", "POST", "/api/v1/research/projects/{project_id}/stages"),
    ApiBindingDef("research:project:create", "POST", "/api/v1/research/projects/{project_id}/tracks"),
    ApiBindingDef("research:pilot-study:create", "POST", "/api/v1/research/rd-pilot-studies"),
    ApiBindingDef("research:process-validation:create", "POST", "/api/v1/research/rd-process-validations"),
    ApiBindingDef("research:project:create", "POST", "/api/v1/research/rd-projects"),
    ApiBindingDef("research:project:submit", "POST", "/api/v1/research/rd-projects/{project_id}/transition"),
    ApiBindingDef("research:registration-filing:create", "POST", "/api/v1/research/rd-registration-filings"),
    ApiBindingDef("research:stage-deliverable:create", "POST", "/api/v1/research/rd-stage-deliverables"),
    ApiBindingDef(
        "research:stage-deliverable:create", "POST", "/api/v1/research/rd-stage-deliverables/{deliverable_id}/upload"
    ),
    ApiBindingDef("research:registration-filing:create", "POST", "/api/v1/research/registration-filings"),
    ApiBindingDef("research:report:create", "POST", "/api/v1/research/reports"),
    ApiBindingDef("research:route:create", "POST", "/api/v1/research/routes"),
    ApiBindingDef("research:route:create", "POST", "/api/v1/research/routes/{route_id}/experiments"),
    ApiBindingDef("research:track:create", "POST", "/api/v1/research/tracks/{track_id}/conclusion-versions"),
    ApiBindingDef("research:track:create", "POST", "/api/v1/research/tracks/{track_id}/conclusions"),
    ApiBindingDef("research:track:create", "POST", "/api/v1/research/tracks/{track_id}/findings"),
    ApiBindingDef(
        "research:deliverable-template:update", "PUT", "/api/v1/research/deliverable-templates/{template_id}"
    ),
    ApiBindingDef("research:experiment-log:update", "PUT", "/api/v1/research/experiment-logs/{log_id}"),
    ApiBindingDef("research:route:update", "PUT", "/api/v1/research/experiments/{exp_id}"),
    ApiBindingDef("research:track:update", "PUT", "/api/v1/research/findings/{finding_id}"),
    ApiBindingDef("research:initiation:update", "PUT", "/api/v1/research/initiations/{initiation_id}"),
    ApiBindingDef("research:optimization:update", "PUT", "/api/v1/research/optimizations/{optimization_id}"),
    ApiBindingDef("research:pilot-study:update", "PUT", "/api/v1/research/pilot-studies/{study_id}"),
    ApiBindingDef("research:process-validation:update", "PUT", "/api/v1/research/process-validations/{validation_id}"),
    ApiBindingDef("research:project:update", "PUT", "/api/v1/research/projects/milestones/{milestone_id}"),
    ApiBindingDef("research:project:update", "PUT", "/api/v1/research/projects/stages/{record_id}"),
    ApiBindingDef("research:track:update", "PUT", "/api/v1/research/projects/tracks/{track_id}"),
    ApiBindingDef("research:project:update", "PUT", "/api/v1/research/projects/{project_id}"),
    ApiBindingDef("research:pilot-study:update", "PUT", "/api/v1/research/rd-pilot-studies/{study_id}"),
    ApiBindingDef(
        "research:process-validation:update", "PUT", "/api/v1/research/rd-process-validations/{validation_id}"
    ),
    ApiBindingDef("research:project:update", "PUT", "/api/v1/research/rd-projects/{project_id}"),
    ApiBindingDef("research:registration-filing:update", "PUT", "/api/v1/research/rd-registration-filings/{filing_id}"),
    ApiBindingDef(
        "research:stage-deliverable:update", "PUT", "/api/v1/research/rd-stage-deliverables/{deliverable_id}"
    ),
    ApiBindingDef("research:registration-filing:update", "PUT", "/api/v1/research/registration-filings/{filing_id}"),
    ApiBindingDef("research:report:update", "PUT", "/api/v1/research/reports/{report_id}"),
    ApiBindingDef("research:route:update", "PUT", "/api/v1/research/routes/{route_id}"),
    # ── environment / administration / warehouse / procurement 模板端点 ──
    ApiBindingDef("environment:module:read", "GET", "/api/v1/environment"),
    ApiBindingDef("environment:module:read", "GET", "/api/v1/environment/"),
    ApiBindingDef("administration:module:read", "GET", "/api/v1/administration"),
    ApiBindingDef("administration:module:read", "GET", "/api/v1/administration/"),
    # ── administration 业务接口 ──
    ApiBindingDef("administration:vehicle:read", "GET", "/api/v1/administration/vehicles"),
    ApiBindingDef("administration:vehicle:create", "POST", "/api/v1/administration/vehicles"),
    ApiBindingDef(
        "administration:vehicle:read", "GET", "/api/v1/administration/vehicles/{vehicle_id}"
    ),
    ApiBindingDef(
        "administration:vehicle:update", "PUT", "/api/v1/administration/vehicles/{vehicle_id}"
    ),
    ApiBindingDef(
        "administration:vehicle:delete", "DELETE", "/api/v1/administration/vehicles/{vehicle_id}"
    ),
    ApiBindingDef(
        "administration:vehicle:read", "GET", "/api/v1/administration/vehicles/template/download"
    ),
    ApiBindingDef("warehouse:module:read", "GET", "/api/v1/warehouse"),
    ApiBindingDef("warehouse:module:read", "GET", "/api/v1/warehouse/"),
    ApiBindingDef("procurement:module:read", "GET", "/api/v1/procurement"),
    ApiBindingDef("procurement:module:read", "GET", "/api/v1/procurement/"),
    ApiBindingDef("safety:module:read", "GET", "/api/v1/safety"),
    ApiBindingDef("safety:module:read", "GET", "/api/v1/safety/"),
    ApiBindingDef("energy:module:read", "GET", "/api/v1/energy"),
    ApiBindingDef("energy:module:read", "GET", "/api/v1/energy/"),
    # ── warehouse 业务接口 ──
    ApiBindingDef("warehouse:raw-material:read", "GET", "/api/v1/warehouse/raw-materials"),
    ApiBindingDef("warehouse:packaging-material:read", "GET", "/api/v1/warehouse/packaging-materials"),
    ApiBindingDef("warehouse:product:read", "GET", "/api/v1/warehouse/products"),
    ApiBindingDef("warehouse:feishu-config:read", "GET", "/api/v1/warehouse/feishu-config"),
    ApiBindingDef("warehouse:feishu-config:update", "PUT", "/api/v1/warehouse/feishu-config"),
    ApiBindingDef("warehouse:feishu-config:create", "POST", "/api/v1/warehouse/feishu-config/test"),
    ApiBindingDef("warehouse:feishu-table:read", "GET", "/api/v1/warehouse/feishu/tables"),
    ApiBindingDef("warehouse:feishu-table:create", "POST", "/api/v1/warehouse/feishu/tables/refresh"),
    ApiBindingDef("warehouse:feishu-table:update", "POST", "/api/v1/warehouse/feishu/tables/enabled/batch"),
    ApiBindingDef("warehouse:feishu-table:update", "PATCH", "/api/v1/warehouse/feishu/tables/{table_id}/enabled"),
    ApiBindingDef(
        "warehouse:feishu-table:submit", "POST", "/api/v1/warehouse/feishu/tables/{table_id}/sync"
    ),
    ApiBindingDef(
        "warehouse:feishu-record:read", "GET", "/api/v1/warehouse/feishu/tables/{table_id}/records"
    ),
    ApiBindingDef(
        "warehouse:feishu-record:read", "GET", "/api/v1/warehouse/feishu/domains/{business_domain}/records"
    ),
    ApiBindingDef("warehouse:feishu-ws:read", "GET", "/api/v1/warehouse/feishu/ws/status"),
    ApiBindingDef("warehouse:feishu-ws:submit", "POST", "/api/v1/warehouse/feishu/ws/restart"),
    # ── procurement 业务接口 ──
    ApiBindingDef("procurement:invoice:create", "POST", "/api/v1/procurement/invoices/recognize"),
    ApiBindingDef("procurement:supplier:read", "GET", "/api/v1/procurement/suppliers"),
    ApiBindingDef("procurement:supplier:create", "POST", "/api/v1/procurement/suppliers/import"),
    ApiBindingDef("procurement:invoice-record:read", "GET", "/api/v1/procurement/invoices/recognition-records"),
    ApiBindingDef(
        "procurement:invoice-record:delete", "DELETE", "/api/v1/procurement/invoices/recognition-records/{record_id}"
    ),
    ApiBindingDef(
        "procurement:invoice-record:delete", "POST", "/api/v1/procurement/invoices/recognition-records/batch-delete"
    ),
    ApiBindingDef("procurement:purchase-order:read", "GET", "/api/v1/procurement/purchase-orders"),
    ApiBindingDef("procurement:purchase-order:export", "GET", "/api/v1/procurement/purchase-orders/export"),
    ApiBindingDef("procurement:purchase-request:read", "GET", "/api/v1/procurement/purchase-requests"),
    ApiBindingDef("procurement:purchase-request:create", "POST", "/api/v1/procurement/purchase-requests"),
    ApiBindingDef(
        "procurement:purchase-request:read", "GET", "/api/v1/procurement/purchase-requests/{request_id}"
    ),
    ApiBindingDef(
        "procurement:purchase-request:update", "PUT", "/api/v1/procurement/purchase-requests/{request_id}"
    ),
    ApiBindingDef(
        "procurement:purchase-request:submit", "POST", "/api/v1/procurement/purchase-requests/{request_id}/submit"
    ),
    ApiBindingDef(
        "procurement:purchase-request:approve", "POST", "/api/v1/procurement/purchase-requests/{request_id}/approve"
    ),
    ApiBindingDef(
        "procurement:purchase-request:submit", "POST", "/api/v1/procurement/purchase-requests/{request_id}/reject"
    ),
    ApiBindingDef("procurement:contract:read", "GET", "/api/v1/procurement/contracts"),
    ApiBindingDef(
        "procurement:contract:read", "GET", "/api/v1/procurement/contracts/templates/{category}"
    ),
    ApiBindingDef("procurement:contract:create", "POST", "/api/v1/procurement/contracts/generate"),
    ApiBindingDef("procurement:contract:read", "GET", "/api/v1/procurement/contracts/{contract_id}"),
    ApiBindingDef(
        "procurement:contract:read", "GET", "/api/v1/procurement/contracts/{contract_id}/file"
    ),
    # ── energy 业务接口 ──
    ApiBindingDef("energy:platform:read", "GET", "/api/v1/energy/platforms"),
    ApiBindingDef("energy:overview:read", "GET", "/api/v1/energy/overview"),
    ApiBindingDef("energy:sync:create", "POST", "/api/v1/energy/sync/bitable"),
    ApiBindingDef("energy:sync:create", "POST", "/api/v1/energy/sync/bitable/workshops"),
    ApiBindingDef("energy:sync:create", "POST", "/api/v1/energy/sync/bitable/monthly"),
    ApiBindingDef("energy:sync:create", "POST", "/api/v1/energy/sync/bitable/cross-import"),
    ApiBindingDef("energy:sync:create", "POST", "/api/v1/energy/sync/bitable/daily-import"),
    ApiBindingDef("energy:job:read", "GET", "/api/v1/energy/jobs/{job_id}"),
    ApiBindingDef("energy:target:create", "POST", "/api/v1/energy/targets"),
    ApiBindingDef(
        "energy:target:read", "GET", "/api/v1/energy/targets/{workshop_id}/{target_month}"
    ),
    ApiBindingDef("energy:target:update", "PUT", "/api/v1/energy/targets/{target_id}"),
    ApiBindingDef("energy:analysis:create", "POST", "/api/v1/energy/ai-analysis-v2"),
    # devices
    ApiBindingDef("energy:device:read", "GET", "/api/v1/energy/devices"),
    ApiBindingDef("energy:device:create", "POST", "/api/v1/energy/devices"),
    ApiBindingDef("energy:device:read", "GET", "/api/v1/energy/devices/{config_id}"),
    ApiBindingDef("energy:device:update", "PUT", "/api/v1/energy/devices/{config_id}"),
    ApiBindingDef("energy:device:delete", "DELETE", "/api/v1/energy/devices/{config_id}"),
    # data
    ApiBindingDef("energy:data:read", "GET", "/api/v1/energy/data"),
    ApiBindingDef("energy:data:read", "GET", "/api/v1/energy/data/statistics"),
    # collect
    ApiBindingDef("energy:collect:read", "GET", "/api/v1/energy/collect/logs"),
    ApiBindingDef(
        "energy:collect:read", "GET", "/api/v1/energy/collect/logs/{log_id}/detail"
    ),
    ApiBindingDef("energy:collect:create", "POST", "/api/v1/energy/collect/trigger"),
    # alert rules
    ApiBindingDef("energy:alert-rule:read", "GET", "/api/v1/energy/alerts/rules"),
    ApiBindingDef("energy:alert-rule:create", "POST", "/api/v1/energy/alerts/rules"),
    ApiBindingDef("energy:alert-rule:read", "GET", "/api/v1/energy/alerts/rules/{rule_id}"),
    ApiBindingDef("energy:alert-rule:update", "PUT", "/api/v1/energy/alerts/rules/{rule_id}"),
    ApiBindingDef("energy:alert-rule:delete", "DELETE", "/api/v1/energy/alerts/rules/{rule_id}"),
    # alert records
    ApiBindingDef("energy:alert-record:read", "GET", "/api/v1/energy/alerts/records"),
    ApiBindingDef(
        "energy:alert-record:update", "PUT", "/api/v1/energy/alerts/records/{record_id}/process"
    ),
    # workshops
    ApiBindingDef("energy:workshop:read", "GET", "/api/v1/energy/workshops"),
    ApiBindingDef("energy:workshop:create", "POST", "/api/v1/energy/workshops"),
    ApiBindingDef("energy:workshop:read", "GET", "/api/v1/energy/workshops/{workshop_id}"),
    ApiBindingDef("energy:workshop:update", "PUT", "/api/v1/energy/workshops/{workshop_id}"),
    ApiBindingDef("energy:workshop:delete", "DELETE", "/api/v1/energy/workshops/{workshop_id}"),
    # monthly
    ApiBindingDef("energy:monthly-record:read", "GET", "/api/v1/energy/monthly"),
    ApiBindingDef("energy:monthly-record:create", "POST", "/api/v1/energy/monthly"),
    ApiBindingDef("energy:monthly-record:create", "POST", "/api/v1/energy/monthly/batch"),
    ApiBindingDef("energy:monthly-record:read", "GET", "/api/v1/energy/monthly/summary"),
    ApiBindingDef("energy:monthly-record:read", "GET", "/api/v1/energy/monthly/{record_id}"),
    ApiBindingDef("energy:monthly-record:delete", "DELETE", "/api/v1/energy/monthly/{record_id}"),
    ApiBindingDef("energy:monthly-record:create", "POST", "/api/v1/energy/monthly/import/feishu"),
    # ── equipment ──
    ApiBindingDef("equipment:equipment:read", "GET", "/api/v1/equipment/categories"),
    ApiBindingDef(
        "equipment:equipment:read", "GET", "/api/v1/equipment/categories/{category_id}"
    ),
    ApiBindingDef(
        "equipment:equipment:update", "PUT", "/api/v1/equipment/categories/{category_id}"
    ),
    ApiBindingDef(
        "equipment:equipment:delete", "DELETE", "/api/v1/equipment/categories/{category_id}"
    ),
    ApiBindingDef("equipment:equipment:read", "GET", "/api/v1/equipment/departments"),
    ApiBindingDef("equipment:equipment:create", "POST", "/api/v1/equipment/equipments"),
    ApiBindingDef("equipment:equipment:read", "GET", "/api/v1/equipment/equipments"),
    ApiBindingDef("equipment:equipment:delete", "POST", "/api/v1/equipment/equipments/batch-delete"),
    ApiBindingDef("equipment:batch-import:create", "POST", "/api/v1/equipment/equipments/import"),
    ApiBindingDef("equipment:batch-import:create", "POST", "/api/v1/equipment/equipments/import/batch"),
    ApiBindingDef("equipment:batch-import:create", "POST", "/api/v1/equipment/equipments/import/preview"),
    ApiBindingDef("equipment:batch-import:read", "GET", "/api/v1/equipment/equipments/import/template"),
    ApiBindingDef("equipment:batch-import:create", "POST", "/api/v1/equipment/equipments/import/test-validation"),
    ApiBindingDef("equipment:equipment:read", "GET", "/api/v1/equipment/equipments/statistics"),
    ApiBindingDef(
        "equipment:equipment:read", "GET", "/api/v1/equipment/equipments/{equipment_id}"
    ),
    ApiBindingDef(
        "equipment:equipment:update", "PUT", "/api/v1/equipment/equipments/{equipment_id}"
    ),
    ApiBindingDef(
        "equipment:equipment:delete", "DELETE", "/api/v1/equipment/equipments/{equipment_id}"
    ),
    ApiBindingDef("equipment:inspection:read", "GET", "/api/v1/equipment/inspection/history"),
    ApiBindingDef(
        "equipment:inspection:read", "GET", "/api/v1/equipment/inspection/history/{task_id}"
    ),
    ApiBindingDef(
        "equipment:inspection:read", "GET", "/api/v1/equipment/inspection/photos/{photo_id}/file"
    ),
    ApiBindingDef("equipment:inspection:create", "POST", "/api/v1/equipment/inspection/routes"),
    ApiBindingDef("equipment:inspection:read", "GET", "/api/v1/equipment/inspection/routes"),
    ApiBindingDef(
        "equipment:inspection:read", "GET", "/api/v1/equipment/inspection/routes/{route_id}"
    ),
    ApiBindingDef(
        "equipment:inspection:update", "PUT", "/api/v1/equipment/inspection/routes/{route_id}"
    ),
    ApiBindingDef(
        "equipment:inspection:delete", "DELETE", "/api/v1/equipment/inspection/routes/{route_id}"
    ),
    ApiBindingDef(
        "equipment:inspection:create", "POST", "/api/v1/equipment/inspection/routes/{route_id}/locations"
    ),
    ApiBindingDef(
        "equipment:inspection:read", "GET", "/api/v1/equipment/inspection/routes/{route_id}/schedules"
    ),
    ApiBindingDef(
        "equipment:inspection:create", "POST", "/api/v1/equipment/inspection/routes/{route_id}/schedules"
    ),
    ApiBindingDef(
        "equipment:inspection:update", "PUT", "/api/v1/equipment/inspection/routes/{route_id}/schedules/{schedule_id}"
    ),
    ApiBindingDef(
        "equipment:inspection:delete", "DELETE", "/api/v1/equipment/inspection/routes/{route_id}/schedules/{schedule_id}"
    ),
    ApiBindingDef("equipment:inspection:create", "POST", "/api/v1/equipment/inspection/tasks"),
    ApiBindingDef("equipment:inspection:read", "GET", "/api/v1/equipment/inspection/tasks"),
    ApiBindingDef(
        "equipment:inspection:read", "GET", "/api/v1/equipment/inspection/tasks/{task_id}"
    ),
    ApiBindingDef(
        "equipment:inspection:manage", "PUT", "/api/v1/equipment/inspection/tasks/{task_id}/close"
    ),
    ApiBindingDef(
        "equipment:inspection:manage", "PUT", "/api/v1/equipment/inspection/tasks/{task_id}/complete"
    ),
    ApiBindingDef(
        "equipment:inspection:create", "POST", "/api/v1/equipment/inspection/tasks/{task_id}/equipments/{equipment_id}/ai-analyze"
    ),
    ApiBindingDef(
        "equipment:inspection:create", "POST", "/api/v1/equipment/inspection/tasks/{task_id}/equipments/{equipment_id}/check"
    ),
    ApiBindingDef(
        "equipment:inspection:create", "POST", "/api/v1/equipment/inspection/tasks/{task_id}/equipments/{equipment_id}/photos"
    ),
    ApiBindingDef(
        "equipment:inspection:create", "POST", "/api/v1/equipment/inspection/tasks/{task_id}/photos"
    ),
    ApiBindingDef(
        "equipment:inspection:read", "GET", "/api/v1/equipment/inspection/tasks/{task_id}/photos"
    ),
    ApiBindingDef(
        "equipment:inspection:delete", "DELETE", "/api/v1/equipment/inspection/tasks/{task_id}/photos/{photo_id}"
    ),
    ApiBindingDef(
        "equipment:inspection:manage", "POST", "/api/v1/equipment/inspection/tasks/{task_id}/route-check"
    ),
    ApiBindingDef(
        "equipment:inspection:manage", "PUT", "/api/v1/equipment/inspection/tasks/{task_id}/start"
    ),
    ApiBindingDef("equipment:equipment:create", "POST", "/api/v1/equipment/locations"),
    ApiBindingDef("equipment:equipment:read", "GET", "/api/v1/equipment/locations"),
    ApiBindingDef(
        "equipment:equipment:read", "GET", "/api/v1/equipment/locations/{location_id}"
    ),
    ApiBindingDef(
        "equipment:equipment:update", "PUT", "/api/v1/equipment/locations/{location_id}"
    ),
    ApiBindingDef(
        "equipment:equipment:delete", "DELETE", "/api/v1/equipment/locations/{location_id}"
    ),
    ApiBindingDef("equipment:calibration:create", "POST", "/api/v1/equipment/maintenance/calibration/plans"),
    ApiBindingDef("equipment:calibration:read", "GET", "/api/v1/equipment/maintenance/calibration/plans"),
    ApiBindingDef("equipment:calibration:read", "GET", "/api/v1/equipment/maintenance/calibration/plans/overdue"),
    ApiBindingDef(
        "equipment:calibration:read", "GET", "/api/v1/equipment/maintenance/calibration/plans/{plan_id}"
    ),
    ApiBindingDef(
        "equipment:calibration:update", "PUT", "/api/v1/equipment/maintenance/calibration/plans/{plan_id}"
    ),
    ApiBindingDef(
        "equipment:calibration:delete", "DELETE", "/api/v1/equipment/maintenance/calibration/plans/{plan_id}"
    ),
    ApiBindingDef("equipment:calibration:create", "POST", "/api/v1/equipment/maintenance/calibration/records"),
    ApiBindingDef("equipment:calibration:read", "GET", "/api/v1/equipment/maintenance/calibration/records"),
    ApiBindingDef(
        "equipment:calibration:read", "GET", "/api/v1/equipment/maintenance/calibration/records/{record_id}"
    ),
    ApiBindingDef("equipment:maintenance-config:read", "GET", "/api/v1/equipment/maintenance/config/claim-timeout"),
    ApiBindingDef("equipment:maintenance-config:update", "PUT", "/api/v1/equipment/maintenance/config/claim-timeout"),
    ApiBindingDef("equipment:inspection-template:create", "POST", "/api/v1/equipment/maintenance/inspection-templates"),
    ApiBindingDef("equipment:inspection-template:read", "GET", "/api/v1/equipment/maintenance/inspection-templates"),
    ApiBindingDef(
        "equipment:inspection-template:create", "POST", "/api/v1/equipment/maintenance/inspection-templates/complete/{work_order_id}"
    ),
    ApiBindingDef(
        "equipment:inspection-template:update", "PUT", "/api/v1/equipment/maintenance/inspection-templates/items/{item_id}"
    ),
    ApiBindingDef(
        "equipment:inspection-template:delete", "DELETE", "/api/v1/equipment/maintenance/inspection-templates/items/{item_id}"
    ),
    ApiBindingDef(
        "equipment:inspection-template:read", "GET", "/api/v1/equipment/maintenance/inspection-templates/{template_id}"
    ),
    ApiBindingDef(
        "equipment:inspection-template:update", "PUT", "/api/v1/equipment/maintenance/inspection-templates/{template_id}"
    ),
    ApiBindingDef(
        "equipment:inspection-template:delete", "DELETE", "/api/v1/equipment/maintenance/inspection-templates/{template_id}"
    ),
    ApiBindingDef(
        "equipment:inspection-template:create", "POST", "/api/v1/equipment/maintenance/inspection-templates/{template_id}/items"
    ),
    ApiBindingDef("equipment:maintenance-plan:create", "POST", "/api/v1/equipment/maintenance/plans"),
    ApiBindingDef("equipment:maintenance-plan:read", "GET", "/api/v1/equipment/maintenance/plans"),
    ApiBindingDef("equipment:maintenance-plan:read", "GET", "/api/v1/equipment/maintenance/plans/overdue"),
    ApiBindingDef(
        "equipment:maintenance-plan:read", "GET", "/api/v1/equipment/maintenance/plans/{plan_id}"
    ),
    ApiBindingDef(
        "equipment:maintenance-plan:update", "PUT", "/api/v1/equipment/maintenance/plans/{plan_id}"
    ),
    ApiBindingDef(
        "equipment:maintenance-plan:delete", "DELETE", "/api/v1/equipment/maintenance/plans/{plan_id}"
    ),
    ApiBindingDef("equipment:maintenance-staff:read", "GET", "/api/v1/equipment/maintenance/staff/all-users"),
    ApiBindingDef("equipment:maintenance-staff:read", "GET", "/api/v1/equipment/maintenance/staff/maintainers"),
    ApiBindingDef("equipment:work-order:create", "POST", "/api/v1/equipment/maintenance/work-orders"),
    ApiBindingDef("equipment:work-order:read", "GET", "/api/v1/equipment/maintenance/work-orders"),
    ApiBindingDef("equipment:work-order:read", "GET", "/api/v1/equipment/maintenance/work-orders/statistics"),
    ApiBindingDef(
        "equipment:work-order:update", "PUT", "/api/v1/equipment/maintenance/work-orders/{work_order_id}"
    ),
    ApiBindingDef(
        "equipment:work-order:read", "GET", "/api/v1/equipment/maintenance/work-orders/{work_order_id}"
    ),
    ApiBindingDef(
        "equipment:work-order:manage", "PUT", "/api/v1/equipment/maintenance/work-orders/{work_order_id}/assign"
    ),
    ApiBindingDef(
        "equipment:work-order:update", "PUT", "/api/v1/equipment/maintenance/work-orders/{work_order_id}/claim"
    ),
    ApiBindingDef(
        "equipment:work-order:manage", "PUT", "/api/v1/equipment/maintenance/work-orders/{work_order_id}/close"
    ),
    ApiBindingDef(
        "equipment:work-order:manage", "PUT", "/api/v1/equipment/maintenance/work-orders/{work_order_id}/complete"
    ),
    ApiBindingDef(
        "equipment:work-order:create", "POST", "/api/v1/equipment/maintenance/work-orders/{work_order_id}/images"
    ),
    ApiBindingDef(
        "equipment:work-order:read", "GET", "/api/v1/equipment/maintenance/work-orders/{work_order_id}/images"
    ),
    ApiBindingDef(
        "equipment:work-order:delete", "DELETE", "/api/v1/equipment/maintenance/work-orders/{work_order_id}/images/{image_id}"
    ),
    ApiBindingDef(
        "equipment:work-order:read", "GET", "/api/v1/equipment/maintenance/work-orders/{work_order_id}/images/{image_id}/file"
    ),
    ApiBindingDef(
        "equipment:work-order:create", "POST", "/api/v1/equipment/maintenance/work-orders/{work_order_id}/materials"
    ),
    ApiBindingDef(
        "equipment:work-order:read", "GET", "/api/v1/equipment/maintenance/work-orders/{work_order_id}/materials"
    ),
    ApiBindingDef(
        "equipment:work-order:manage", "PUT", "/api/v1/equipment/maintenance/work-orders/{work_order_id}/start"
    ),
    ApiBindingDef(
        "equipment:work-order:manage", "PUT", "/api/v1/equipment/maintenance/work-orders/{work_order_id}/verify"
    ),
    ApiBindingDef("equipment:personnel:create", "POST", "/api/v1/equipment/personnel"),
    ApiBindingDef("equipment:personnel:read", "GET", "/api/v1/equipment/personnel"),
    ApiBindingDef("equipment:personnel:read", "GET", "/api/v1/equipment/personnel/candidates"),
    ApiBindingDef("equipment:personnel:create", "POST", "/api/v1/equipment/personnel/refresh-feishu"),
    ApiBindingDef("equipment:personnel:create", "POST", "/api/v1/equipment/personnel/roles"),
    ApiBindingDef("equipment:personnel:read", "GET", "/api/v1/equipment/personnel/roles"),
    ApiBindingDef(
        "equipment:personnel:read", "GET", "/api/v1/equipment/personnel/roles/{role_id}"
    ),
    ApiBindingDef(
        "equipment:personnel:update", "PUT", "/api/v1/equipment/personnel/roles/{role_id}"
    ),
    ApiBindingDef(
        "equipment:personnel:delete", "DELETE", "/api/v1/equipment/personnel/roles/{role_id}"
    ),
    ApiBindingDef(
        "equipment:personnel:read", "GET", "/api/v1/equipment/personnel/{personnel_id}"
    ),
    ApiBindingDef(
        "equipment:personnel:update", "PUT", "/api/v1/equipment/personnel/{personnel_id}"
    ),
    ApiBindingDef(
        "equipment:personnel:delete", "DELETE", "/api/v1/equipment/personnel/{personnel_id}"
    ),
    ApiBindingDef(
        "equipment:personnel:create", "POST", "/api/v1/equipment/personnel/{personnel_id}/categories"
    ),
    ApiBindingDef(
        "equipment:personnel:update", "PUT", "/api/v1/equipment/personnel/{personnel_id}/categories"
    ),
    ApiBindingDef(
        "equipment:personnel:create", "POST", "/api/v1/equipment/personnel/{personnel_id}/roles"
    ),
    ApiBindingDef(
        "equipment:personnel:update", "PUT", "/api/v1/equipment/personnel/{personnel_id}/roles"
    ),
    ApiBindingDef("equipment:spare-part:create", "POST", "/api/v1/equipment/spare-parts"),
    ApiBindingDef("equipment:spare-part:read", "GET", "/api/v1/equipment/spare-parts"),
    ApiBindingDef("equipment:spare-part:read", "GET", "/api/v1/equipment/spare-parts/stock/warnings"),
    ApiBindingDef(
        "equipment:spare-part:read", "GET", "/api/v1/equipment/spare-parts/{spare_part_id}"
    ),
    ApiBindingDef(
        "equipment:spare-part:update", "PUT", "/api/v1/equipment/spare-parts/{spare_part_id}"
    ),
    ApiBindingDef(
        "equipment:spare-part:delete", "DELETE", "/api/v1/equipment/spare-parts/{spare_part_id}"
    ),
    ApiBindingDef(
        "equipment:spare-part:read", "GET", "/api/v1/equipment/spare-parts/{spare_part_id}/stock"
    ),
    ApiBindingDef(
        "equipment:spare-part:create", "POST", "/api/v1/equipment/spare-parts/{spare_part_id}/stock/adjust"
    ),
    ApiBindingDef(
        "equipment:spare-part:create", "POST", "/api/v1/equipment/spare-parts/{spare_part_id}/stock/inbound"
    ),
    # failure-codes (dynamic f-string routes, 3 groups × 5 CRUD)
    ApiBindingDef("equipment:failure-code:create", "POST", "/api/v1/equipment/maintenance/failure-codes/symptoms"),
    ApiBindingDef("equipment:failure-code:read", "GET", "/api/v1/equipment/maintenance/failure-codes/symptoms"),
    ApiBindingDef("equipment:failure-code:read", "GET", "/api/v1/equipment/maintenance/failure-codes/symptoms/{code_id}"),
    ApiBindingDef("equipment:failure-code:update", "PUT", "/api/v1/equipment/maintenance/failure-codes/symptoms/{code_id}"),
    ApiBindingDef("equipment:failure-code:delete", "DELETE", "/api/v1/equipment/maintenance/failure-codes/symptoms/{code_id}"),
    ApiBindingDef("equipment:failure-code:create", "POST", "/api/v1/equipment/maintenance/failure-codes/causes"),
    ApiBindingDef("equipment:failure-code:read", "GET", "/api/v1/equipment/maintenance/failure-codes/causes"),
    ApiBindingDef("equipment:failure-code:read", "GET", "/api/v1/equipment/maintenance/failure-codes/causes/{code_id}"),
    ApiBindingDef("equipment:failure-code:update", "PUT", "/api/v1/equipment/maintenance/failure-codes/causes/{code_id}"),
    ApiBindingDef("equipment:failure-code:delete", "DELETE", "/api/v1/equipment/maintenance/failure-codes/causes/{code_id}"),
    ApiBindingDef("equipment:failure-code:create", "POST", "/api/v1/equipment/maintenance/failure-codes/actions"),
    ApiBindingDef("equipment:failure-code:read", "GET", "/api/v1/equipment/maintenance/failure-codes/actions"),
    ApiBindingDef("equipment:failure-code:read", "GET", "/api/v1/equipment/maintenance/failure-codes/actions/{code_id}"),
    ApiBindingDef("equipment:failure-code:update", "PUT", "/api/v1/equipment/maintenance/failure-codes/actions/{code_id}"),
    ApiBindingDef("equipment:failure-code:delete", "DELETE", "/api/v1/equipment/maintenance/failure-codes/actions/{code_id}"),
    # ── registration ──
    ApiBindingDef("registration:authorization-letter:read", "GET", "/api/v1/registration/authorization-letters"),
    ApiBindingDef("registration:authorization-letter:create", "POST", "/api/v1/registration/authorization-letters/generate"),
    ApiBindingDef("registration:authorization-letter:read", "GET", "/api/v1/registration/authorization-letters/products"),
    ApiBindingDef(
        "registration:authorization-letter:read", "GET", "/api/v1/registration/authorization-letters/{letter_id}"
    ),
    ApiBindingDef(
        "registration:authorization-letter:delete", "DELETE", "/api/v1/registration/authorization-letters/{letter_id}"
    ),
    ApiBindingDef(
        "registration:authorization-letter:read", "GET", "/api/v1/registration/authorization-letters/{letter_id}/download"
    ),
    ApiBindingDef(
        "registration:authorization-letter:read", "GET", "/api/v1/registration/authorization-letters/{letter_id}/download-url"
    ),
    ApiBindingDef("registration:certificate:read", "GET", "/api/v1/registration/certificates"),
    ApiBindingDef("registration:certificate:create", "POST", "/api/v1/registration/certificates"),
    ApiBindingDef(
        "registration:certificate:read", "GET", "/api/v1/registration/certificates/{certificate_id}"
    ),
    ApiBindingDef(
        "registration:certificate:update", "PUT", "/api/v1/registration/certificates/{certificate_id}"
    ),
    ApiBindingDef(
        "registration:certificate:delete", "DELETE", "/api/v1/registration/certificates/{certificate_id}"
    ),
    ApiBindingDef("registration:dashboard:read", "GET", "/api/v1/registration/dashboard/summary"),
    ApiBindingDef("registration:drug:read", "GET", "/api/v1/registration/drugs"),
    ApiBindingDef("registration:drug:create", "POST", "/api/v1/registration/drugs"),
    ApiBindingDef("registration:drug:read", "GET", "/api/v1/registration/drugs/nodes"),
    ApiBindingDef(
        "registration:drug:read", "GET", "/api/v1/registration/drugs/{drug_id}"
    ),
    ApiBindingDef(
        "registration:drug:update", "PUT", "/api/v1/registration/drugs/{drug_id}"
    ),
    ApiBindingDef(
        "registration:drug:delete", "DELETE", "/api/v1/registration/drugs/{drug_id}"
    ),
    ApiBindingDef("registration:holiday:read", "GET", "/api/v1/registration/holidays"),
    ApiBindingDef("registration:holiday:create", "POST", "/api/v1/registration/holidays"),
    ApiBindingDef(
        "registration:holiday:update", "PUT", "/api/v1/registration/holidays/{holiday_id}"
    ),
    ApiBindingDef(
        "registration:holiday:delete", "DELETE", "/api/v1/registration/holidays/{holiday_id}"
    ),
    ApiBindingDef("registration:approval-record:read", "GET", "/api/v1/registration/ledger/copp-certificates"),
    ApiBindingDef("registration:approval-record:create", "POST", "/api/v1/registration/ledger/copp-certificates"),
    ApiBindingDef("registration:approval-record:read", "GET", "/api/v1/registration/ledger/copp-certificates/export"),
    ApiBindingDef("registration:approval-record:create", "POST", "/api/v1/registration/ledger/copp-certificates/import"),
    ApiBindingDef("registration:approval-record:read", "GET", "/api/v1/registration/ledger/domestic-approvals"),
    ApiBindingDef("registration:approval-record:create", "POST", "/api/v1/registration/ledger/domestic-approvals"),
    ApiBindingDef("registration:approval-record:read", "GET", "/api/v1/registration/ledger/domestic-approvals/export"),
    ApiBindingDef("registration:approval-record:create", "POST", "/api/v1/registration/ledger/domestic-approvals/import"),
    ApiBindingDef("registration:approval-record:read", "GET", "/api/v1/registration/ledger/international-reviews"),
    ApiBindingDef("registration:approval-record:create", "POST", "/api/v1/registration/ledger/international-reviews"),
    ApiBindingDef("registration:approval-record:read", "GET", "/api/v1/registration/ledger/international-reviews/export"),
    ApiBindingDef("registration:approval-record:create", "POST", "/api/v1/registration/ledger/international-reviews/import"),
    ApiBindingDef("registration:approval-record:read", "GET", "/api/v1/registration/ledger/overseas-approvals"),
    ApiBindingDef("registration:approval-record:create", "POST", "/api/v1/registration/ledger/overseas-approvals"),
    ApiBindingDef("registration:approval-record:read", "GET", "/api/v1/registration/ledger/overseas-approvals/export"),
    ApiBindingDef("registration:approval-record:create", "POST", "/api/v1/registration/ledger/overseas-approvals/import"),
    ApiBindingDef("registration:approval-record:read", "GET", "/api/v1/registration/ledger/reviewing"),
    ApiBindingDef("registration:approval-record:read", "GET", "/api/v1/registration/ledger/summary"),
    ApiBindingDef("registration:approval-record:read", "GET", "/api/v1/registration/ledger/wc-certificates"),
    ApiBindingDef("registration:approval-record:create", "POST", "/api/v1/registration/ledger/wc-certificates"),
    ApiBindingDef("registration:approval-record:read", "GET", "/api/v1/registration/ledger/wc-certificates/export"),
    ApiBindingDef("registration:approval-record:create", "POST", "/api/v1/registration/ledger/wc-certificates/import"),
    ApiBindingDef("registration:project:read", "GET", "/api/v1/registration/projects"),
    ApiBindingDef("registration:project:create", "POST", "/api/v1/registration/projects"),
    ApiBindingDef(
        "registration:project:read", "GET", "/api/v1/registration/projects/{project_id}"
    ),
    ApiBindingDef(
        "registration:project:update", "PUT", "/api/v1/registration/projects/{project_id}"
    ),
    ApiBindingDef(
        "registration:project:delete", "DELETE", "/api/v1/registration/projects/{project_id}"
    ),
    ApiBindingDef("registration:reference-standard:read", "GET", "/api/v1/registration/reference-standards"),
    ApiBindingDef("registration:reference-standard:create", "POST", "/api/v1/registration/reference-standards/generate"),
    ApiBindingDef("registration:reference-standard:create", "POST", "/api/v1/registration/reference-standards/parse-coa"),
    ApiBindingDef(
        "registration:reference-standard:read", "GET", "/api/v1/registration/reference-standards/{record_id}"
    ),
    ApiBindingDef(
        "registration:reference-standard:delete", "DELETE", "/api/v1/registration/reference-standards/{record_id}"
    ),
    ApiBindingDef(
        "registration:reference-standard:read", "GET", "/api/v1/registration/reference-standards/{record_id}/download"
    ),
    ApiBindingDef(
        "registration:reference-standard:read", "GET", "/api/v1/registration/reference-standards/{record_id}/download-url"
    ),
    ApiBindingDef("registration:reference-substance:read", "GET", "/api/v1/registration/reference-substances"),
    ApiBindingDef("registration:reference-substance:create", "POST", "/api/v1/registration/reference-substances"),
    ApiBindingDef(
        "registration:reference-substance:read", "GET", "/api/v1/registration/reference-substances/{substance_id}"
    ),
    ApiBindingDef(
        "registration:reference-substance:update", "PUT", "/api/v1/registration/reference-substances/{substance_id}"
    ),
    ApiBindingDef(
        "registration:reference-substance:delete", "DELETE", "/api/v1/registration/reference-substances/{substance_id}"
    ),
    ApiBindingDef("registration:regulatory-tracker:read", "GET", "/api/v1/registration/regulatory-documents"),
    ApiBindingDef("registration:regulatory-tracker:manage", "POST", "/api/v1/registration/regulatory-documents/batch-read"),
    ApiBindingDef("registration:regulatory-tracker:read", "GET", "/api/v1/registration/regulatory-documents/export"),
    ApiBindingDef(
        "registration:regulatory-tracker:read", "GET", "/api/v1/registration/regulatory-documents/{doc_id}/detail"
    ),
    ApiBindingDef(
        "registration:regulatory-tracker:manage", "PATCH", "/api/v1/registration/regulatory-documents/{doc_id}/read"
    ),
    ApiBindingDef("registration:regulatory-tracker:read", "GET", "/api/v1/registration/regulatory-tracker/dashboard"),
    ApiBindingDef("registration:regulatory-tracker:read", "GET", "/api/v1/registration/regulatory-tracker/summary"),
    ApiBindingDef("registration:supplementary-reply:read", "GET", "/api/v1/registration/supplementary-replies"),
    ApiBindingDef("registration:supplementary-reply:create", "POST", "/api/v1/registration/supplementary-replies/generate"),
    ApiBindingDef(
        "registration:supplementary-reply:read", "GET", "/api/v1/registration/supplementary-replies/{reply_id}"
    ),
    ApiBindingDef(
        "registration:supplementary-reply:delete", "DELETE", "/api/v1/registration/supplementary-replies/{reply_id}"
    ),
    ApiBindingDef(
        "registration:supplementary-reply:read", "GET", "/api/v1/registration/supplementary-replies/{reply_id}/download"
    ),
    ApiBindingDef(
        "registration:supplementary-reply:read", "GET", "/api/v1/registration/supplementary-replies/{reply_id}/download-url"
    ),
    ApiBindingDef("registration:regulatory-tracker:read", "GET", "/api/v1/registration/sync-jobs"),
    ApiBindingDef("registration:regulatory-tracker:manage", "POST", "/api/v1/registration/sync-jobs/trigger"),
    ApiBindingDef("registration:validation-audit:create", "POST", "/api/v1/registration/validation-audit/tasks"),
    ApiBindingDef("registration:validation-audit:read", "GET", "/api/v1/registration/validation-audit/tasks"),
    ApiBindingDef(
        "registration:validation-audit:read", "GET", "/api/v1/registration/validation-audit/tasks/{task_id}"
    ),
    ApiBindingDef(
        "registration:validation-audit:update", "PUT", "/api/v1/registration/validation-audit/tasks/{task_id}"
    ),
    ApiBindingDef(
        "registration:validation-audit:delete", "DELETE", "/api/v1/registration/validation-audit/tasks/{task_id}"
    ),
    ApiBindingDef(
        "registration:validation-audit:create", "POST", "/api/v1/registration/validation-audit/tasks/{task_id}/audit"
    ),
    ApiBindingDef(
        "registration:validation-audit:read", "POST", "/api/v1/registration/validation-audit/tasks/{task_id}/export"
    ),
    ApiBindingDef(
        "registration:validation-audit:create", "POST", "/api/v1/registration/validation-audit/tasks/{task_id}/files"
    ),
    ApiBindingDef(
        "registration:validation-audit:read", "GET", "/api/v1/registration/validation-audit/tasks/{task_id}/files"
    ),
    ApiBindingDef(
        "registration:validation-audit:read", "GET", "/api/v1/registration/validation-audit/tasks/{task_id}/issues"
    ),
    ApiBindingDef(
        "registration:validation-audit:create", "POST", "/api/v1/registration/validation-audit/tasks/{task_id}/parse"
    ),
    ApiBindingDef(
        "registration:validation-audit:read", "GET", "/api/v1/registration/validation-audit/tasks/{task_id}/report"
    ),
    ApiBindingDef("quality:doc-check:create", "POST", "/api/v1/quality/batch"),
    ApiBindingDef("quality:doc-check:create", "POST", "/api/v1/quality/check"),
    ApiBindingDef("quality:doc-check:read", "GET", "/api/v1/quality/check"),
    ApiBindingDef("quality:doc-check:read", "GET", "/api/v1/quality/check/{check_id}"),
    ApiBindingDef("quality:doc-check:update", "PUT", "/api/v1/quality/check/{check_id}"),
    ApiBindingDef("quality:doc-check:delete", "DELETE", "/api/v1/quality/check/{check_id}"),
    ApiBindingDef("quality:doc-check:cancel", "POST", "/api/v1/quality/check/{check_id}/cancel"),
    ApiBindingDef("quality:doc-check:execute", "POST", "/api/v1/quality/check/{check_id}/execute"),
    ApiBindingDef("quality:doc-check:read", "GET", "/api/v1/quality/config"),
    ApiBindingDef("quality:doc-check:create", "POST", "/api/v1/quality/config"),
    ApiBindingDef("quality:doc-check:read", "GET", "/api/v1/quality/config/{config_id}"),
    ApiBindingDef("quality:doc-check:update", "PUT", "/api/v1/quality/config/{config_id}"),
    ApiBindingDef("quality:cpv:update", "POST", "/api/v1/quality/cpv/import/confirm"),
    ApiBindingDef("quality:cpv:create", "POST", "/api/v1/quality/cpv/import/preview"),
    ApiBindingDef("quality:cpv:import", "GET", "/api/v1/quality/cpv/import/tasks"),
    ApiBindingDef("quality:cpv:import", "GET", "/api/v1/quality/cpv/import/tasks/{task_id}"),
    ApiBindingDef("quality:cpv:update", "PUT", "/api/v1/quality/cpv/parameters/{parameter_id}"),
    ApiBindingDef("quality:cpv:delete", "DELETE", "/api/v1/quality/cpv/parameters/{parameter_id}"),
    ApiBindingDef("quality:cpv:create", "POST", "/api/v1/quality/cpv/products"),
    ApiBindingDef("quality:cpv:read", "GET", "/api/v1/quality/cpv/products"),
    ApiBindingDef("quality:cpv:read", "GET", "/api/v1/quality/cpv/products/{product_id}"),
    ApiBindingDef("quality:cpv:update", "PUT", "/api/v1/quality/cpv/products/{product_id}"),
    ApiBindingDef("quality:cpv:delete", "DELETE", "/api/v1/quality/cpv/products/{product_id}"),
    ApiBindingDef("quality:cpv:create", "GET", "/api/v1/quality/cpv/products/{product_id}/batches"),
    ApiBindingDef("quality:cpv:read", "GET", "/api/v1/quality/cpv/products/{product_id}/cpp"),
    ApiBindingDef("quality:cpv:read", "GET", "/api/v1/quality/cpv/products/{product_id}/cqa"),
    ApiBindingDef("quality:cpv:read", "GET", "/api/v1/quality/cpv/products/{product_id}/parameters"),
    ApiBindingDef("quality:cpv:create", "POST", "/api/v1/quality/cpv/products/{product_id}/parameters"),
    ApiBindingDef("quality:cpv:read", "GET", "/api/v1/quality/cpv/products/{product_id}/statistics"),
    ApiBindingDef("quality:cpv:read", "GET", "/api/v1/quality/cpv/products/{product_id}/trend"),
    ApiBindingDef("quality:deviation:read", "GET", "/api/v1/quality/deviation"),
    ApiBindingDef("quality:deviation:create", "POST", "/api/v1/quality/deviation"),
    ApiBindingDef("quality:deviation-settings:read", "GET", "/api/v1/quality/deviation-settings/auto-triggers"),
    ApiBindingDef("quality:deviation-settings:create", "POST", "/api/v1/quality/deviation-settings/auto-triggers"),
    ApiBindingDef("quality:deviation-settings:update", "PUT", "/api/v1/quality/deviation-settings/auto-triggers/{id}"),
    ApiBindingDef("quality:deviation-settings:delete", "DELETE", "/api/v1/quality/deviation-settings/auto-triggers/{id}"),
    ApiBindingDef("quality:deviation-settings:update", "PUT", "/api/v1/quality/deviation-settings/auto-triggers/{id}/toggle"),
    ApiBindingDef("quality:deviation-settings:read", "GET", "/api/v1/quality/deviation-settings/feishu-bot"),
    ApiBindingDef("quality:deviation-settings:create", "POST", "/api/v1/quality/deviation-settings/feishu-bot"),
    ApiBindingDef("quality:deviation-settings:update", "PUT", "/api/v1/quality/deviation-settings/feishu-bot"),
    ApiBindingDef("quality:deviation-settings:delete", "DELETE", "/api/v1/quality/deviation-settings/feishu-bot"),
    ApiBindingDef("quality:deviation-settings:update", "PUT", "/api/v1/quality/deviation-settings/feishu-bot/toggle"),
    ApiBindingDef("quality:deviation-settings:read", "GET", "/api/v1/quality/deviation-settings/feishu-user/by-mobile"),
    ApiBindingDef("quality:deviation-settings:read", "GET", "/api/v1/quality/deviation-settings/leaders"),
    ApiBindingDef("quality:deviation-settings:create", "POST", "/api/v1/quality/deviation-settings/leaders"),
    ApiBindingDef("quality:deviation-settings:update", "PUT", "/api/v1/quality/deviation-settings/leaders/{id}"),
    ApiBindingDef("quality:deviation-settings:delete", "DELETE", "/api/v1/quality/deviation-settings/leaders/{id}"),
    ApiBindingDef("quality:deviation-settings:update", "PUT", "/api/v1/quality/deviation-settings/leaders/{id}/toggle"),
    ApiBindingDef("quality:deviation-settings:read", "GET", "/api/v1/quality/deviation-settings/message-templates"),
    ApiBindingDef("quality:deviation-settings:create", "POST", "/api/v1/quality/deviation-settings/message-templates"),
    ApiBindingDef("quality:deviation-settings:update", "PUT", "/api/v1/quality/deviation-settings/message-templates/{id}"),
    ApiBindingDef("quality:deviation-settings:delete", "DELETE", "/api/v1/quality/deviation-settings/message-templates/{id}"),
    ApiBindingDef("quality:deviation-settings:update", "PUT", "/api/v1/quality/deviation-settings/message-templates/{id}/set-default"),
    ApiBindingDef("quality:deviation-settings:update", "PUT", "/api/v1/quality/deviation-settings/message-templates/{id}/toggle"),
    ApiBindingDef("quality:deviation-settings:read", "GET", "/api/v1/quality/deviation-settings/options"),
    ApiBindingDef("quality:deviation-settings:read", "GET", "/api/v1/quality/deviation-settings/qa-users"),
    ApiBindingDef("quality:deviation-settings:create", "POST", "/api/v1/quality/deviation-settings/qa-users"),
    ApiBindingDef("quality:deviation-settings:update", "PUT", "/api/v1/quality/deviation-settings/qa-users/{id}"),
    ApiBindingDef("quality:deviation-settings:delete", "DELETE", "/api/v1/quality/deviation-settings/qa-users/{id}"),
    ApiBindingDef("quality:deviation-settings:update", "PUT", "/api/v1/quality/deviation-settings/qa-users/{id}/toggle"),
    ApiBindingDef("quality:deviation-settings:create", "POST", "/api/v1/quality/deviation-settings/reminder/trigger"),
    ApiBindingDef("quality:deviation-settings:read", "GET", "/api/v1/quality/deviation-settings/rules"),
    ApiBindingDef("quality:deviation-settings:create", "POST", "/api/v1/quality/deviation-settings/rules"),
    ApiBindingDef("quality:deviation-settings:update", "PUT", "/api/v1/quality/deviation-settings/rules/{id}"),
    ApiBindingDef("quality:deviation-settings:delete", "DELETE", "/api/v1/quality/deviation-settings/rules/{id}"),
    ApiBindingDef("quality:deviation-settings:update", "PUT", "/api/v1/quality/deviation-settings/rules/{id}/toggle"),
    ApiBindingDef("quality:deviation:create", "POST", "/api/v1/quality/deviation/ai/analyze-direct-cause"),
    ApiBindingDef("quality:deviation:create", "POST", "/api/v1/quality/deviation/ai/analyze-impact"),
    ApiBindingDef("quality:deviation:create", "POST", "/api/v1/quality/deviation/ai/analyze-root-cause"),
    ApiBindingDef("quality:deviation:create", "POST", "/api/v1/quality/deviation/ai/generate-capa"),
    ApiBindingDef("quality:deviation:create", "POST", "/api/v1/quality/deviation/ai/generate-description"),
    ApiBindingDef("quality:deviation:create", "POST", "/api/v1/quality/deviation/ai/generate-emergency-measures"),
    ApiBindingDef("quality:deviation:create", "POST", "/api/v1/quality/deviation/ai/generate-prevention"),
    ApiBindingDef("quality:deviation:read", "GET", "/api/v1/quality/deviation/closings/list"),
    ApiBindingDef("quality:deviation:read", "GET", "/api/v1/quality/deviation/corrections/list"),
    ApiBindingDef("quality:deviation:read", "GET", "/api/v1/quality/deviation/investigations/list"),
    ApiBindingDef("quality:deviation:read", "GET", "/api/v1/quality/deviation/statistics"),
    ApiBindingDef("quality:deviation:read", "GET", "/api/v1/quality/deviation/{deviation_id}"),
    ApiBindingDef("quality:deviation:update", "PUT", "/api/v1/quality/deviation/{deviation_id}"),
    ApiBindingDef("quality:deviation:delete", "DELETE", "/api/v1/quality/deviation/{deviation_id}"),
    ApiBindingDef("quality:deviation:approve", "POST", "/api/v1/quality/deviation/{deviation_id}/approve"),
    ApiBindingDef("quality:deviation:create", "POST", "/api/v1/quality/deviation/{deviation_id}/closing"),
    ApiBindingDef("quality:deviation:update", "PUT", "/api/v1/quality/deviation/{deviation_id}/closing"),
    ApiBindingDef("quality:deviation:update", "POST", "/api/v1/quality/deviation/{deviation_id}/closing/complete"),
    ApiBindingDef("quality:deviation:create", "POST", "/api/v1/quality/deviation/{deviation_id}/correction"),
    ApiBindingDef("quality:deviation:update", "PUT", "/api/v1/quality/deviation/{deviation_id}/correction"),
    ApiBindingDef("quality:deviation:update", "POST", "/api/v1/quality/deviation/{deviation_id}/correction/progress"),
    ApiBindingDef("quality:deviation:create", "POST", "/api/v1/quality/deviation/{deviation_id}/investigation"),
    ApiBindingDef("quality:deviation:update", "PUT", "/api/v1/quality/deviation/{deviation_id}/investigation"),
    ApiBindingDef("quality:deviation:update", "POST", "/api/v1/quality/deviation/{deviation_id}/investigation/complete"),
    ApiBindingDef("quality:deviation:update", "POST", "/api/v1/quality/deviation/{deviation_id}/lock-batch"),
    ApiBindingDef("quality:deviation:submit", "POST", "/api/v1/quality/deviation/{deviation_id}/submit"),
    ApiBindingDef("quality:deviation:update", "POST", "/api/v1/quality/deviation/{deviation_id}/unlock-batch"),
    ApiBindingDef("quality:export:read", "GET", "/api/v1/quality/export/{record_id}"),
    ApiBindingDef("quality:fqc:create", "POST", "/api/v1/quality/fqc/inspections"),
    ApiBindingDef("quality:fqc:read", "GET", "/api/v1/quality/fqc/inspections"),
    ApiBindingDef("quality:fqc:read", "GET", "/api/v1/quality/fqc/inspections/{inspection_id}"),
    ApiBindingDef("quality:fqc:update", "PUT", "/api/v1/quality/fqc/inspections/{inspection_id}"),
    ApiBindingDef("quality:fqc:delete", "DELETE", "/api/v1/quality/fqc/inspections/{inspection_id}"),
    ApiBindingDef("quality:fqc:read", "GET", "/api/v1/quality/fqc/inspections/{inspection_id}/approvals"),
    ApiBindingDef("quality:fqc:approve", "POST", "/api/v1/quality/fqc/inspections/{inspection_id}/approve"),
    ApiBindingDef("quality:fqc:update", "POST", "/api/v1/quality/fqc/inspections/{inspection_id}/lock-batch"),
    ApiBindingDef("quality:fqc:create", "POST", "/api/v1/quality/fqc/inspections/{inspection_id}/reinspection"),
    ApiBindingDef("quality:fqc:create", "POST", "/api/v1/quality/fqc/inspections/{inspection_id}/release"),
    ApiBindingDef("quality:fqc:submit", "POST", "/api/v1/quality/fqc/inspections/{inspection_id}/submit"),
    ApiBindingDef("quality:fqc:update", "POST", "/api/v1/quality/fqc/inspections/{inspection_id}/unlock-batch"),
    ApiBindingDef("quality:instrument:read", "GET", "/api/v1/quality/instrument"),
    ApiBindingDef("quality:instrument:create", "POST", "/api/v1/quality/instrument"),
    ApiBindingDef("quality:instrument:create", "POST", "/api/v1/quality/instrument/feishu-contacts/resolve-user"),
    ApiBindingDef("quality:instrument:create", "POST", "/api/v1/quality/instrument/recognize"),
    ApiBindingDef("quality:instrument:read", "GET", "/api/v1/quality/instrument/record/for-reminder"),
    ApiBindingDef("quality:instrument:create", "POST", "/api/v1/quality/instrument/record/remind"),
    ApiBindingDef("quality:instrument:read", "GET", "/api/v1/quality/instrument/record/upcoming"),
    ApiBindingDef("quality:instrument:read", "GET", "/api/v1/quality/instrument/records"),
    ApiBindingDef("quality:instrument:create", "POST", "/api/v1/quality/instrument/records"),
    ApiBindingDef("quality:instrument:read", "GET", "/api/v1/quality/instrument/records/{record_id}"),
    ApiBindingDef("quality:instrument:update", "PUT", "/api/v1/quality/instrument/records/{record_id}"),
    ApiBindingDef("quality:instrument:delete", "DELETE", "/api/v1/quality/instrument/records/{record_id}"),
    ApiBindingDef("quality:instrument:approve", "POST", "/api/v1/quality/instrument/records/{record_id}/approve"),
    ApiBindingDef("quality:instrument:submit", "POST", "/api/v1/quality/instrument/records/{record_id}/submit"),
    ApiBindingDef("quality:instrument:read", "GET", "/api/v1/quality/instrument/reminder-config"),
    ApiBindingDef("quality:instrument:create", "POST", "/api/v1/quality/instrument/reminder-config"),
    ApiBindingDef("quality:instrument:update", "PUT", "/api/v1/quality/instrument/reminder-config/{config_id}"),
    ApiBindingDef("quality:instrument:delete", "DELETE", "/api/v1/quality/instrument/reminder-config/{config_id}"),
    ApiBindingDef("quality:instrument:create", "POST", "/api/v1/quality/instrument/reminder/auto-trigger"),
    ApiBindingDef("quality:instrument:read", "GET", "/api/v1/quality/instrument/rules"),
    ApiBindingDef("quality:instrument:create", "POST", "/api/v1/quality/instrument/rules"),
    ApiBindingDef("quality:instrument:read", "GET", "/api/v1/quality/instrument/rules/{instrument_id}"),
    ApiBindingDef("quality:instrument:update", "PUT", "/api/v1/quality/instrument/rules/{rule_id}"),
    ApiBindingDef("quality:instrument:delete", "DELETE", "/api/v1/quality/instrument/rules/{rule_id}"),
    ApiBindingDef("quality:instrument:read", "GET", "/api/v1/quality/instrument/upcoming"),
    ApiBindingDef("quality:instrument:read", "GET", "/api/v1/quality/instrument/{instrument_id}"),
    ApiBindingDef("quality:instrument:update", "PUT", "/api/v1/quality/instrument/{instrument_id}"),
    ApiBindingDef("quality:instrument:delete", "DELETE", "/api/v1/quality/instrument/{instrument_id}"),
    ApiBindingDef("quality:instrument:create", "POST", "/api/v1/quality/instrument/{instrument_id}/activate"),
    ApiBindingDef("quality:instrument:approve", "POST", "/api/v1/quality/instrument/{instrument_id}/approve"),
    ApiBindingDef("quality:instrument:create", "POST", "/api/v1/quality/instrument/{instrument_id}/deactivate"),
    ApiBindingDef("quality:instrument:submit", "POST", "/api/v1/quality/instrument/{instrument_id}/submit"),
    ApiBindingDef("quality:ipqc:create", "POST", "/api/v1/quality/ipqc/inspections"),
    ApiBindingDef("quality:ipqc:read", "GET", "/api/v1/quality/ipqc/inspections"),
    ApiBindingDef("quality:ipqc:read", "GET", "/api/v1/quality/ipqc/inspections/{inspection_id}"),
    ApiBindingDef("quality:ipqc:update", "PUT", "/api/v1/quality/ipqc/inspections/{inspection_id}"),
    ApiBindingDef("quality:ipqc:delete", "DELETE", "/api/v1/quality/ipqc/inspections/{inspection_id}"),
    ApiBindingDef("quality:ipqc:read", "GET", "/api/v1/quality/ipqc/inspections/{inspection_id}/approvals"),
    ApiBindingDef("quality:ipqc:approve", "POST", "/api/v1/quality/ipqc/inspections/{inspection_id}/approve"),
    ApiBindingDef("quality:ipqc:update", "POST", "/api/v1/quality/ipqc/inspections/{inspection_id}/lock-batch"),
    ApiBindingDef("quality:ipqc:submit", "POST", "/api/v1/quality/ipqc/inspections/{inspection_id}/submit"),
    ApiBindingDef("quality:ipqc:update", "POST", "/api/v1/quality/ipqc/inspections/{inspection_id}/unlock-batch"),
    ApiBindingDef("quality:iqc:create", "POST", "/api/v1/quality/iqc/inspections"),
    ApiBindingDef("quality:iqc:read", "GET", "/api/v1/quality/iqc/inspections"),
    ApiBindingDef("quality:iqc:read", "GET", "/api/v1/quality/iqc/inspections/{inspection_id}"),
    ApiBindingDef("quality:iqc:update", "PUT", "/api/v1/quality/iqc/inspections/{inspection_id}"),
    ApiBindingDef("quality:iqc:delete", "DELETE", "/api/v1/quality/iqc/inspections/{inspection_id}"),
    ApiBindingDef("quality:iqc:read", "GET", "/api/v1/quality/iqc/inspections/{inspection_id}/approvals"),
    ApiBindingDef("quality:iqc:approve", "POST", "/api/v1/quality/iqc/inspections/{inspection_id}/approve"),
    ApiBindingDef("quality:iqc:submit", "POST", "/api/v1/quality/iqc/inspections/{inspection_id}/submit"),
    ApiBindingDef("quality:label-verification:read", "GET", "/api/v1/quality/label-verifications"),
    ApiBindingDef("quality:label-verification:create", "POST", "/api/v1/quality/label-verifications"),
    ApiBindingDef("quality:label-verification:read", "GET", "/api/v1/quality/label-verifications/batch/{batch_number}"),
    ApiBindingDef("quality:label-verification:read", "GET", "/api/v1/quality/label-verifications/statistics"),
    ApiBindingDef("quality:label-verification:read", "GET", "/api/v1/quality/label-verifications/{verification_id}"),
    ApiBindingDef("quality:label-verification:update", "PUT", "/api/v1/quality/label-verifications/{verification_id}"),
    ApiBindingDef("quality:label-verification:delete", "DELETE", "/api/v1/quality/label-verifications/{verification_id}"),
    ApiBindingDef("quality:label-verification:create", "POST", "/api/v1/quality/label-verifications/upload-video"),
    ApiBindingDef("quality:label-verification:create", "POST", "/api/v1/quality/label-verifications/analyze-video"),
    ApiBindingDef("quality:label-verification:create", "POST", "/api/v1/quality/label-verifications/auto-compare"),
    ApiBindingDef("quality:material-report:read", "GET", "/api/v1/quality/material-report/"),
    ApiBindingDef("quality:material-report:create", "POST", "/api/v1/quality/material-report/"),
    ApiBindingDef("quality:material-report:read", "GET", "/api/v1/quality/material-report/statistics"),
    ApiBindingDef("quality:material-report:read", "GET", "/api/v1/quality/material-report/template"),
    ApiBindingDef("quality:material-report:read", "POST", "/api/v1/quality/material-report/template/"),
    ApiBindingDef("quality:material-report:read", "GET", "/api/v1/quality/material-report/template/{template_id}"),
    ApiBindingDef("quality:material-report:read", "PUT", "/api/v1/quality/material-report/template/{template_id}"),
    ApiBindingDef("quality:material-report:read", "DELETE", "/api/v1/quality/material-report/template/{template_id}"),
    ApiBindingDef("quality:material-report:read", "GET", "/api/v1/quality/material-report/template/{template_id}/preview"),
    ApiBindingDef("quality:material-report:read", "GET", "/api/v1/quality/material-report/{report_id}"),
    ApiBindingDef("quality:material-report:update", "PUT", "/api/v1/quality/material-report/{report_id}"),
    ApiBindingDef("quality:material-report:delete", "DELETE", "/api/v1/quality/material-report/{report_id}"),
    ApiBindingDef("quality:material-report:create", "POST", "/api/v1/quality/material-report/{report_id}/generate"),
    ApiBindingDef("quality:material-report:create", "POST", "/api/v1/quality/material-report/{report_id}/images"),
    ApiBindingDef("quality:material-report:read", "GET", "/api/v1/quality/material-report/{report_id}/images"),
    ApiBindingDef("quality:material-report:create", "POST", "/api/v1/quality/material-report/{report_id}/items"),
    ApiBindingDef("quality:material-report:submit", "POST", "/api/v1/quality/material-report/{report_id}/submit"),
    ApiBindingDef("quality:problem:read", "GET", "/api/v1/quality/problems"),
    ApiBindingDef("quality:problem:create", "PUT", "/api/v1/quality/problems/batch"),
    ApiBindingDef("quality:problem:update", "PUT", "/api/v1/quality/problems/{problem_id}"),
    ApiBindingDef("quality:reagent:create", "POST", "/api/v1/quality/reagent"),
    ApiBindingDef("quality:reagent-reminder:create", "POST", "/api/v1/quality/reagent-reminder/check"),
    ApiBindingDef("quality:reagent-reminder:read", "GET", "/api/v1/quality/reagent-reminder/config"),
    ApiBindingDef("quality:reagent-reminder:create", "POST", "/api/v1/quality/reagent-reminder/config"),
    ApiBindingDef("quality:reagent-reminder:create", "POST", "/api/v1/quality/reagent-reminder/item-reminder"),
    ApiBindingDef("quality:reagent-reminder:read", "GET", "/api/v1/quality/reagent-reminder/item-reminder/{reagent_name}"),
    ApiBindingDef("quality:reagent-reminder:read", "GET", "/api/v1/quality/reagent-reminder/low-stock"),
    ApiBindingDef("quality:reagent:export", "GET", "/api/v1/quality/reagent/export"),
    ApiBindingDef("quality:reagent:read", "GET", "/api/v1/quality/reagent/list"),
    ApiBindingDef("quality:reagent:read", "GET", "/api/v1/quality/reagent/next-lot-no"),
    ApiBindingDef("quality:reagent:create", "POST", "/api/v1/quality/reagent/recognize"),
    ApiBindingDef("quality:reagent:read", "GET", "/api/v1/quality/reagent/{reagent_id}"),
    ApiBindingDef("quality:reagent:update", "PUT", "/api/v1/quality/reagent/{reagent_id}"),
    ApiBindingDef("quality:reagent:delete", "DELETE", "/api/v1/quality/reagent/{reagent_id}"),
    ApiBindingDef("quality:record:read", "GET", "/api/v1/quality/records"),
    ApiBindingDef("quality:sampling:create", "POST", "/api/v1/quality/sampling/orders"),
    ApiBindingDef("quality:sampling:read", "GET", "/api/v1/quality/sampling/orders"),
    ApiBindingDef("quality:sampling:read", "GET", "/api/v1/quality/sampling/orders/{order_id}"),
    ApiBindingDef("quality:sampling:update", "PUT", "/api/v1/quality/sampling/orders/{order_id}"),
    ApiBindingDef("quality:sampling:delete", "DELETE", "/api/v1/quality/sampling/orders/{order_id}"),
    ApiBindingDef("quality:sampling:read", "GET", "/api/v1/quality/sampling/orders/{order_id}/approvals"),
    ApiBindingDef("quality:sampling:approve", "POST", "/api/v1/quality/sampling/orders/{order_id}/approve"),
    ApiBindingDef("quality:sampling:submit", "POST", "/api/v1/quality/sampling/orders/{order_id}/submit"),
    ApiBindingDef("quality:sampling:read", "GET", "/api/v1/quality/sampling/retention-ledger"),
    ApiBindingDef("quality:sop-ai:create", "POST", "/api/v1/quality/sop-ai/check/batch"),
    ApiBindingDef("quality:sop-ai:create", "POST", "/api/v1/quality/sop-ai/check/single"),
    ApiBindingDef("quality:sop-ai:read", "GET", "/api/v1/quality/sop-ai/config"),
    ApiBindingDef("quality:sop-ai:read", "GET", "/api/v1/quality/sop-ai/config/{config_key}"),
    ApiBindingDef("quality:sop-ai:update", "PUT", "/api/v1/quality/sop-ai/config/{config_key}"),
    ApiBindingDef("quality:sop-ai:export", "GET", "/api/v1/quality/sop-ai/export/{id}"),
    ApiBindingDef("quality:sop-ai:read", "GET", "/api/v1/quality/sop-ai/jobs"),
    ApiBindingDef("quality:sop-ai:create", "POST", "/api/v1/quality/sop-ai/jobs"),
    ApiBindingDef("quality:sop-ai:delete", "DELETE", "/api/v1/quality/sop-ai/jobs/{job_id}"),
    ApiBindingDef("quality:sop-ai:update", "PUT", "/api/v1/quality/sop-ai/problems/{problem_id}"),
    ApiBindingDef("quality:sop-ai:read", "GET", "/api/v1/quality/sop-ai/records"),
    ApiBindingDef("quality:sop-ai:read", "GET", "/api/v1/quality/sop-ai/records/{id}"),
    ApiBindingDef("quality:stability:create", "POST", "/api/v1/quality/stability/inspections"),
    ApiBindingDef("quality:stability:read", "GET", "/api/v1/quality/stability/inspections"),
    ApiBindingDef("quality:stability:read", "GET", "/api/v1/quality/stability/inspections/{inspection_id}"),
    ApiBindingDef("quality:stability:update", "PUT", "/api/v1/quality/stability/inspections/{inspection_id}"),
    ApiBindingDef("quality:stability:submit", "POST", "/api/v1/quality/stability/inspections/{inspection_id}/submit"),
    ApiBindingDef("quality:stability:update", "PUT", "/api/v1/quality/stability/sample-nodes/{node_id}"),
    ApiBindingDef("quality:stability:create", "POST", "/api/v1/quality/stability/studies"),
    ApiBindingDef("quality:stability:read", "GET", "/api/v1/quality/stability/studies"),
    ApiBindingDef("quality:stability:read", "GET", "/api/v1/quality/stability/studies/{study_id}"),
    ApiBindingDef("quality:stability:update", "PUT", "/api/v1/quality/stability/studies/{study_id}"),
    ApiBindingDef("quality:stability:delete", "DELETE", "/api/v1/quality/stability/studies/{study_id}"),
    ApiBindingDef("quality:stability:approve", "POST", "/api/v1/quality/stability/studies/{study_id}/approve"),
    ApiBindingDef("quality:stability:read", "GET", "/api/v1/quality/stability/studies/{study_id}/sample-nodes"),
    ApiBindingDef("quality:stability:submit", "POST", "/api/v1/quality/stability/studies/{study_id}/submit"),
    ApiBindingDef("quality:stability:read", "GET", "/api/v1/quality/stability/studies/{study_id}/trend"),
    ApiBindingDef("quality:standard:read", "GET", "/api/v1/quality/standards"),
    ApiBindingDef("quality:standard:create", "POST", "/api/v1/quality/standards"),
    ApiBindingDef("quality:standard:create", "POST", "/api/v1/quality/standards/copy"),
    ApiBindingDef("quality:standard:read", "GET", "/api/v1/quality/standards/effective"),
    ApiBindingDef("quality:static-data:read", "GET", "/api/v1/quality/static-data/chrom-column"),
    ApiBindingDef("quality:static-data:create", "POST", "/api/v1/quality/static-data/chrom-column"),
    ApiBindingDef("quality:static-data:read", "GET", "/api/v1/quality/static-data/chrom-column/template"),
    ApiBindingDef("quality:static-data:read", "GET", "/api/v1/quality/static-data/chrom-column/{id}"),
    ApiBindingDef("quality:static-data:update", "PUT", "/api/v1/quality/static-data/chrom-column/{id}"),
    ApiBindingDef("quality:static-data:delete", "DELETE", "/api/v1/quality/static-data/chrom-column/{id}"),
    ApiBindingDef("quality:static-data:read", "GET", "/api/v1/quality/static-data/dict/{dict_type}"),
    ApiBindingDef("quality:static-data:read", "GET", "/api/v1/quality/static-data/hplc-reference"),
    ApiBindingDef("quality:static-data:create", "POST", "/api/v1/quality/static-data/hplc-reference"),
    ApiBindingDef("quality:static-data:create", "POST", "/api/v1/quality/static-data/hplc-reference/batch-import"),
    ApiBindingDef("quality:static-data:read", "GET", "/api/v1/quality/static-data/hplc-reference/need-recal"),
    ApiBindingDef("quality:static-data:read", "GET", "/api/v1/quality/static-data/hplc-reference/template"),
    ApiBindingDef("quality:static-data:read", "GET", "/api/v1/quality/static-data/hplc-reference/{id}"),
    ApiBindingDef("quality:static-data:update", "PUT", "/api/v1/quality/static-data/hplc-reference/{id}"),
    ApiBindingDef("quality:static-data:delete", "DELETE", "/api/v1/quality/static-data/hplc-reference/{id}"),
    ApiBindingDef("quality:static-data:read", "GET", "/api/v1/quality/static-data/hplc-reference/{id}/usage-history"),
    ApiBindingDef("quality:static-data:update", "POST", "/api/v1/quality/static-data/hplc-reference/{id}/use"),
    ApiBindingDef("quality:static-data:read", "GET", "/api/v1/quality/static-data/medium"),
    ApiBindingDef("quality:static-data:create", "POST", "/api/v1/quality/static-data/medium"),
    ApiBindingDef("quality:static-data:read", "GET", "/api/v1/quality/static-data/medium/{id}"),
    ApiBindingDef("quality:static-data:update", "PUT", "/api/v1/quality/static-data/medium/{id}"),
    ApiBindingDef("quality:static-data:delete", "DELETE", "/api/v1/quality/static-data/medium/{id}"),
    ApiBindingDef("quality:static-data:update", "POST", "/api/v1/quality/static-data/medium/{id}/adjust-stock"),
    ApiBindingDef("quality:static-data:read", "GET", "/api/v1/quality/static-data/standard"),
    ApiBindingDef("quality:static-data:create", "POST", "/api/v1/quality/static-data/standard"),
    ApiBindingDef("quality:static-data:read", "GET", "/api/v1/quality/static-data/standard/{id}"),
    ApiBindingDef("quality:static-data:update", "PUT", "/api/v1/quality/static-data/standard/{id}"),
    ApiBindingDef("quality:static-data:delete", "DELETE", "/api/v1/quality/static-data/standard/{id}"),
    ApiBindingDef("quality:static-data:update", "POST", "/api/v1/quality/static-data/standard/{id}/adjust-quantity"),
    ApiBindingDef("quality:static-data:read", "GET", "/api/v1/quality/static-data/storage-condition"),
    ApiBindingDef("quality:static-data:create", "POST", "/api/v1/quality/static-data/storage-condition"),
    ApiBindingDef("quality:static-data:read", "GET", "/api/v1/quality/static-data/storage-condition/options"),
    ApiBindingDef("quality:static-data:read", "GET", "/api/v1/quality/static-data/storage-condition/{id}"),
    ApiBindingDef("quality:static-data:update", "PUT", "/api/v1/quality/static-data/storage-condition/{id}"),
    ApiBindingDef("quality:static-data:delete", "DELETE", "/api/v1/quality/static-data/storage-condition/{id}"),
    ApiBindingDef("quality:static-data:read", "GET", "/api/v1/quality/static-data/unit/options"),
    ApiBindingDef("quality:doc-check:create", "POST", "/api/v1/quality/upload"),
    ApiBindingDef("quality:doc-check:read", "GET", "/api/v1/quality/vector-cache"),


    ApiBindingDef("hr:employees:read", "GET", "/api/v1/hr/employees"),
    ApiBindingDef("hr:employees:create", "POST", "/api/v1/hr/employees"),
    ApiBindingDef("hr:employees:sync", "POST", "/api/v1/hr/employees/sync-from-feishu"),
    ApiBindingDef("hr:employees:sync", "GET", "/api/v1/hr/employees/sync-status"),
    ApiBindingDef("hr:employees:read", "GET", "/api/v1/hr/employees/by-number/{employee_number}"),
    ApiBindingDef("hr:employees:read", "GET", "/api/v1/hr/employees/{employee_id}"),
    ApiBindingDef("hr:employees:update", "PUT", "/api/v1/hr/employees/{employee_id}"),
    ApiBindingDef("hr:employees:delete", "DELETE", "/api/v1/hr/employees/{employee_id}"),
    ApiBindingDef("hr:employees:sync", "POST", "/api/v1/hr/employees/{employee_id}/sync-to-feishu"),
    ApiBindingDef("hr:webhook:create", "POST", "/api/v1/hr/webhook/feishu-approval"),
    ApiBindingDef("hr:employees:read", "GET", "/api/v1/hr/employees/{employee_id}/onboarding-training-record"),
    ApiBindingDef("hr:employees:read", "GET", "/api/v1/hr/employees/{employee_id}/prejob-training-plan"),
    ApiBindingDef("hr:employees:create", "POST", "/api/v1/hr/employees/{employee_id}/prejob-training-plan"),
    ApiBindingDef("hr:employees:read", "GET", "/api/v1/hr/employees/{employee_id}/onboarding-evaluation"),
    ApiBindingDef("hr:training-sign-in-sheet:create", "POST", "/api/v1/hr/training-sign-in-sheet"),
    ApiBindingDef("hr:training-notifications:create", "POST", "/api/v1/hr/training-notifications/send"),
    ApiBindingDef("hr:training-select-tasks:create", "POST", "/api/v1/hr/training-select-tasks/send"),
    ApiBindingDef("hr:training-select-tasks:read", "GET", "/api/v1/hr/training-select-tasks/{token}"),
    ApiBindingDef("hr:training-select-tasks:update", "POST", "/api/v1/hr/training-select-tasks/{token}/submit"),
    ApiBindingDef("hr:training-select-tasks:read", "GET", "/api/v1/hr/training-select-tasks"),
    ApiBindingDef("hr:training-select-tasks:read", "GET", "/api/v1/hr/training-select-tasks/{token}/result"),
    ApiBindingDef("hr:training-notification:create", "POST", "/api/v1/hr/training-notification"),
    ApiBindingDef("hr:training-evaluation:create", "POST", "/api/v1/hr/training-evaluation"),
    ApiBindingDef("hr:onboarding-evaluation:create", "POST", "/api/v1/hr/onboarding-evaluation"),
    ApiBindingDef("hr:departments:read", "GET", "/api/v1/hr/departments"),
    ApiBindingDef("hr:departments:create", "POST", "/api/v1/hr/departments"),
    ApiBindingDef("hr:departments:read", "GET", "/api/v1/hr/departments/{department_id}"),
    ApiBindingDef("hr:departments:update", "PUT", "/api/v1/hr/departments/{department_id}"),
    ApiBindingDef("hr:departments:delete", "DELETE", "/api/v1/hr/departments/{department_id}"),
    ApiBindingDef("hr:teams:read", "GET", "/api/v1/hr/teams"),
    ApiBindingDef("hr:teams:create", "POST", "/api/v1/hr/teams"),
    ApiBindingDef("hr:teams:read", "GET", "/api/v1/hr/teams/{team_id}"),
    ApiBindingDef("hr:teams:update", "PUT", "/api/v1/hr/teams/{team_id}"),
    ApiBindingDef("hr:teams:delete", "DELETE", "/api/v1/hr/teams/{team_id}"),
    ApiBindingDef("hr:offboarding-records:read", "GET", "/api/v1/hr/offboarding-records"),
    ApiBindingDef("hr:offboarding-records:create", "POST", "/api/v1/hr/offboarding-records"),
    ApiBindingDef("hr:offboarding-records:read", "GET", "/api/v1/hr/offboarding-records/{record_id}"),
    ApiBindingDef("hr:offboarding-records:update", "PUT", "/api/v1/hr/offboarding-records/{record_id}"),
    ApiBindingDef("hr:offboarding-records:delete", "DELETE", "/api/v1/hr/offboarding-records/{record_id}"),
    ApiBindingDef("hr:onboarding-records:read", "GET", "/api/v1/hr/onboarding-records"),
    ApiBindingDef("hr:onboarding-records:sync", "POST", "/api/v1/hr/onboarding-records/sync-from-feishu"),
    ApiBindingDef("hr:onboarding-records:sync", "GET", "/api/v1/hr/onboarding-records/sync-status"),
    ApiBindingDef("hr:onboarding-records:read", "GET", "/api/v1/hr/onboarding-records/{record_id}"),
    ApiBindingDef("hr:departure-records:read", "GET", "/api/v1/hr/departure-records"),
    ApiBindingDef("hr:departure-records:create", "POST", "/api/v1/hr/departure-records"),
    ApiBindingDef("hr:departure-records:read", "GET", "/api/v1/hr/departure-records/{record_id}"),
    ApiBindingDef("hr:departure-records:update", "PUT", "/api/v1/hr/departure-records/{record_id}"),
    ApiBindingDef("hr:departure-records:delete", "DELETE", "/api/v1/hr/departure-records/{record_id}"),
    ApiBindingDef("hr:departure-records:sync", "POST", "/api/v1/hr/departure-records/sync-from-feishu"),
    ApiBindingDef("hr:departure-records:sync", "GET", "/api/v1/hr/departure-records/sync-status"),
    ApiBindingDef("hr:training-ledgers:read", "GET", "/api/v1/hr/training-ledgers"),
    ApiBindingDef("hr:training-ledgers:create", "POST", "/api/v1/hr/training-ledgers"),
    ApiBindingDef("hr:training-ledgers:read", "GET", "/api/v1/hr/training-ledgers/pages"),
    ApiBindingDef("hr:training-ledgers:create", "POST", "/api/v1/hr/training-ledgers/pages"),
    ApiBindingDef("hr:training-ledgers:export", "GET", "/api/v1/hr/training-ledgers/export"),
    ApiBindingDef("hr:training-ledgers:read", "GET", "/api/v1/hr/training-ledgers/{record_id}"),
    ApiBindingDef("hr:training-ledgers:update", "PUT", "/api/v1/hr/training-ledgers/{record_id}"),
    ApiBindingDef("hr:training-ledgers:delete", "DELETE", "/api/v1/hr/training-ledgers/{record_id}"),
    ApiBindingDef("hr:annual-training-plans:read", "GET", "/api/v1/hr/annual-training-plans"),
    ApiBindingDef("hr:annual-training-plans:create", "POST", "/api/v1/hr/annual-training-plans"),
    ApiBindingDef("hr:annual-training-plans:read", "GET", "/api/v1/hr/annual-training-plans/{plan_id}"),
    ApiBindingDef("hr:annual-training-plans:update", "PUT", "/api/v1/hr/annual-training-plans/{plan_id}"),
    ApiBindingDef("hr:annual-training-plans:delete", "DELETE", "/api/v1/hr/annual-training-plans/{plan_id}"),
    ApiBindingDef("hr:annual-training-plans:read", "GET", "/api/v1/hr/annual-training-plans/{plan_id}/items"),
    ApiBindingDef("hr:annual-training-plans:update", "PUT", "/api/v1/hr/annual-training-plans/{plan_id}/items/batch"),
    ApiBindingDef("hr:annual-training-plans:export", "GET", "/api/v1/hr/annual-training-plans/{plan_id}/export"),
    ApiBindingDef("hr:new-employees:read", "GET", "/api/v1/hr/new/employees"),
    ApiBindingDef("hr:new-onboarding-records:read", "GET", "/api/v1/hr/new/onboarding-records"),
    ApiBindingDef("hr:new-departure-records:read", "GET", "/api/v1/hr/new/departure-records"),
    ApiBindingDef("hr:new-offboarding-records:read", "GET", "/api/v1/hr/new/offboarding-records"),
    ApiBindingDef("hr:new-departments:read", "GET", "/api/v1/hr/new/departments"),
    ApiBindingDef("hr:candidates:read", "GET", "/api/v1/hr/candidates"),
    ApiBindingDef("hr:candidates:read", "POST", "/api/v1/hr/candidates/parse-preview"),
    ApiBindingDef("hr:candidates:create", "POST", "/api/v1/hr/candidates"),
    ApiBindingDef("hr:candidates:sync", "POST", "/api/v1/hr/candidates/sync-from-feishu"),
    ApiBindingDef("hr:candidates:sync", "GET", "/api/v1/hr/candidates/sync-status"),
    ApiBindingDef("hr:candidates:sync", "POST", "/api/v1/hr/candidates/{candidate_id}/sync-to-feishu"),
    ApiBindingDef("hr:candidates:read", "GET", "/api/v1/hr/candidates/{candidate_id}"),
    ApiBindingDef("hr:candidates:update", "PUT", "/api/v1/hr/candidates/{candidate_id}"),
    ApiBindingDef("hr:candidates:delete", "DELETE", "/api/v1/hr/candidates/{candidate_id}"),
    ApiBindingDef("hr:candidates:update", "PUT", "/api/v1/hr/candidates/{candidate_id}/recommendation-level"),
    ApiBindingDef("hr:candidates:read", "GET", "/api/v1/hr/candidates/{candidate_id}/resume-preview"),
    ApiBindingDef("hr:training-sessions:read", "GET", "/api/v1/hr/training-sessions"),
    ApiBindingDef("hr:training-sessions:create", "POST", "/api/v1/hr/training-sessions"),
    ApiBindingDef("hr:training-sessions:update", "PUT", "/api/v1/hr/training-sessions/{session_id}/status"),
    ApiBindingDef("hr:training-sessions:read", "GET", "/api/v1/hr/training-sessions/{session_id}"),
    ApiBindingDef("hr:training-sessions:update", "PUT", "/api/v1/hr/training-sessions/{session_id}"),
    ApiBindingDef("hr:training-sessions:delete", "DELETE", "/api/v1/hr/training-sessions/{session_id}"),
    ApiBindingDef("hr:training-sessions:create", "POST", "/api/v1/hr/training-sessions/{session_id}/send-select-tasks"),
    ApiBindingDef("hr:training-sessions:read", "GET", "/api/v1/hr/training-sessions/{session_id}/select-tasks"),
    ApiBindingDef("hr:training-specialists:read", "GET", "/api/v1/hr/training-specialists"),
    ApiBindingDef("hr:training-specialists:create", "POST", "/api/v1/hr/training-specialists"),
    ApiBindingDef("hr:training-specialists:delete", "DELETE", "/api/v1/hr/training-specialists/{specialist_id}"),
    ApiBindingDef("hr:training-specialists:sync", "POST", "/api/v1/hr/training-specialists/sync-feishu-openids"),
    ApiBindingDef("hr:training-teams:read", "GET", "/api/v1/hr/training-teams"),
    ApiBindingDef("hr:training-teams:create", "POST", "/api/v1/hr/training-teams"),
    ApiBindingDef("hr:training-teams:update", "PUT", "/api/v1/hr/training-teams/{team_id}"),
    ApiBindingDef("hr:training-teams:delete", "DELETE", "/api/v1/hr/training-teams/{team_id}"),
    ApiBindingDef("hr:prejob-training-templates:read", "GET", "/api/v1/hr/prejob-training-templates"),
    ApiBindingDef("hr:prejob-training-templates:update", "PUT", "/api/v1/hr/prejob-training-templates"),
    ApiBindingDef("hr:system-settings:read", "GET", "/api/v1/hr/system-settings"),
    ApiBindingDef("hr:system-settings:update", "PUT", "/api/v1/hr/system-settings"),
    ApiBindingDef("hr:departments:update", "PUT", "/api/v1/hr/departments/{department_id}/production-settings"),
    ApiBindingDef("hr:turnover-analysis:read", "GET", "/api/v1/hr/turnover-analysis"),
    ApiBindingDef("hr:ai-exam:generate", "POST", "/api/v1/hr/ai-exam/generate"),
    ApiBindingDef("hr:ai-exam:export", "POST", "/api/v1/hr/ai-exam/export"),
    ApiBindingDef("production:batches:read", "GET", "/api/v1/production/batches"),
    ApiBindingDef("production:batches:read", "GET", "/api/v1/production/batches/{batch_id}"),
    ApiBindingDef("production:batches:create", "POST", "/api/v1/production/batches"),
    ApiBindingDef("production:batches:update", "PUT", "/api/v1/production/batches/{batch_id}"),
    ApiBindingDef("production:batches:update", "PUT", "/api/v1/production/batches/{batch_id}/status"),
    ApiBindingDef("production:batches:delete", "DELETE", "/api/v1/production/batches/{batch_id}"),
    ApiBindingDef("production:batches:read", "GET", "/api/v1/production/batches/{batch_id}/materials"),
    ApiBindingDef("production:batches:create", "POST", "/api/v1/production/batches/{batch_id}/materials"),
    ApiBindingDef("production:materials:update", "PUT", "/api/v1/production/materials/{material_id}"),
    ApiBindingDef("production:materials:delete", "DELETE", "/api/v1/production/materials/{material_id}"),
    ApiBindingDef("production:plans:read", "GET", "/api/v1/production/plans"),
    ApiBindingDef("production:plans:read", "GET", "/api/v1/production/plans/{plan_id}"),
    ApiBindingDef("production:plans:create", "POST", "/api/v1/production/plans"),
    ApiBindingDef("production:plans:update", "PUT", "/api/v1/production/plans/{plan_id}"),
    ApiBindingDef("production:plans:delete", "DELETE", "/api/v1/production/plans/{plan_id}"),
    ApiBindingDef("production:plans:read", "GET", "/api/v1/production/plans/{plan_id}/tasks"),
    ApiBindingDef("production:tasks:create", "POST", "/api/v1/production/tasks"),
    ApiBindingDef("production:tasks:update", "PUT", "/api/v1/production/tasks/{task_id}"),
    ApiBindingDef("production:tasks:delete", "DELETE", "/api/v1/production/tasks/{task_id}"),
    ApiBindingDef("production:process-specs:read", "GET", "/api/v1/production/process-specs"),
    ApiBindingDef("production:process-specs:read", "GET", "/api/v1/production/process-specs/{spec_id}"),
    ApiBindingDef("production:process-specs:create", "POST", "/api/v1/production/process-specs"),
    ApiBindingDef("production:process-specs:update", "PUT", "/api/v1/production/process-specs/{spec_id}"),
    ApiBindingDef("production:process-specs:delete", "DELETE", "/api/v1/production/process-specs/{spec_id}"),
    ApiBindingDef("production:process-specs:read", "GET", "/api/v1/production/process-specs/{spec_id}/steps"),
    ApiBindingDef("production:steps:create", "POST", "/api/v1/production/steps"),
    ApiBindingDef("production:steps:update", "PUT", "/api/v1/production/steps/{step_id}"),
    ApiBindingDef("production:steps:delete", "DELETE", "/api/v1/production/steps/{step_id}"),
    ApiBindingDef("production:steps:read", "GET", "/api/v1/production/steps/{step_id}/parameters"),
    ApiBindingDef("production:parameters:create", "POST", "/api/v1/production/parameters"),
    ApiBindingDef("production:parameters:delete", "DELETE", "/api/v1/production/parameters/{param_id}"),
    ApiBindingDef("production:batches:read", "GET", "/api/v1/production/batches/{batch_id}/records"),
    ApiBindingDef("production:records:create", "POST", "/api/v1/production/records"),
    ApiBindingDef("production:records:update", "PUT", "/api/v1/production/records/{record_id}"),
    ApiBindingDef("production:records:delete", "DELETE", "/api/v1/production/records/{record_id}"),
    ApiBindingDef("production:batches:read", "GET", "/api/v1/production/batches/{batch_id}/balance"),
    ApiBindingDef("production:batches:read", "POST", "/api/v1/production/batches/{batch_id}/balance/calculate"),
    ApiBindingDef("production:batches:update", "PUT", "/api/v1/production/batches/{batch_id}/balance"),
    ApiBindingDef("production:products:read", "GET", "/api/v1/production/products"),
    ApiBindingDef("production:products:read", "GET", "/api/v1/production/products/workshop/{workshop}"),
    ApiBindingDef("production:products:read", "GET", "/api/v1/production/products/{product_id}"),
    ApiBindingDef("production:products:create", "POST", "/api/v1/production/products"),
    ApiBindingDef("production:products:update", "PUT", "/api/v1/production/products/{product_id}"),
    ApiBindingDef("production:products:delete", "DELETE", "/api/v1/production/products/{product_id}"),
    ApiBindingDef("production:product-output:read", "GET", "/api/v1/production/product-output/workshops"),
    ApiBindingDef("production:product-output:read", "GET", "/api/v1/production/product-output"),
    ApiBindingDef("production:product-output:read", "GET", "/api/v1/production/product-output/summary"),
    ApiBindingDef("production:product-output:read", "GET", "/api/v1/production/product-output/batch-count"),
    ApiBindingDef("production:product-output:export", "GET", "/api/v1/production/product-output/export"),
    ApiBindingDef("production:product-output:read", "GET", "/api/v1/production/product-output/annual-review"),
    ApiBindingDef("production:product-output:export", "GET", "/api/v1/production/product-output/annual-review/export"),
    ApiBindingDef("production:product-output:read", "GET", "/api/v1/production/product-output/{record_id}"),
    ApiBindingDef("production:product-output:create", "POST", "/api/v1/production/product-output"),
    ApiBindingDef("production:product-output:update", "PUT", "/api/v1/production/product-output/{record_id}"),
    ApiBindingDef("production:product-output:delete", "DELETE", "/api/v1/production/product-output/batch"),
    ApiBindingDef("production:product-output:delete", "DELETE", "/api/v1/production/product-output/{record_id}"),
    ApiBindingDef("production:product-output:import", "POST", "/api/v1/production/product-output/import/preview"),
    ApiBindingDef("production:product-output:import", "POST", "/api/v1/production/product-output/import"),
    ApiBindingDef("production:product-output:import", "DELETE", "/api/v1/production/product-output/import/{batch_id}"),
    ApiBindingDef("production:product-output:import", "POST", "/api/v1/production/product-output/import-from-bitable"),
    ApiBindingDef("production:product-sync-config:read", "GET", "/api/v1/production/product-sync-config/{product_id}"),
    ApiBindingDef("production:product-sync-config:create", "POST", "/api/v1/production/product-sync-config"),
    ApiBindingDef("production:product-sync-config:update", "PUT", "/api/v1/production/product-sync-config/{config_id}"),
    ApiBindingDef("production:product-sync-config:delete", "DELETE", "/api/v1/production/product-sync-config/{config_id}"),
    ApiBindingDef("production:product-sync-config:sync", "POST", "/api/v1/production/product-sync-config/{product_id}/push"),
    ApiBindingDef("production:product-sync-config:sync", "POST", "/api/v1/production/product-sync-config/{product_id}/pull"),
    ApiBindingDef("production:product-sync-config:sync", "POST", "/api/v1/production/product-sync-config/{product_id}/sync"),
    ApiBindingDef("production:product-sync-config:read", "POST", "/api/v1/production/product-sync-config/{product_id}/preview-push"),
    ApiBindingDef("production:product-sync-config:read", "POST", "/api/v1/production/product-sync-config/{product_id}/preview-pull"),
    ApiBindingDef("production:product-sync-config:update", "POST", "/api/v1/production/product-sync-config/{product_id}/undo-last-sync"),
    ApiBindingDef("production:pressure-dashboard:read", "GET", "/api/v1/production/pressure/dashboard"),
    ApiBindingDef("production:pressure-point-mappings:read", "GET", "/api/v1/production/pressure/point-mappings"),
    ApiBindingDef("production:pressure-point-mappings:read", "GET", "/api/v1/production/pressure/point-mappings/check-unique"),
    ApiBindingDef("production:pressure-point-mappings:create", "POST", "/api/v1/production/pressure/point-mappings"),
    ApiBindingDef("production:pressure-point-mappings:read", "GET", "/api/v1/production/pressure/point-mappings/{mapping_id}"),
    ApiBindingDef("production:pressure-point-mappings:update", "PUT", "/api/v1/production/pressure/point-mappings/{mapping_id}"),
    ApiBindingDef("production:pressure-point-mappings:delete", "DELETE", "/api/v1/production/pressure/point-mappings/{mapping_id}"),
    ApiBindingDef("production:pressure-records:read", "GET", "/api/v1/production/pressure/records"),
    ApiBindingDef("production:pressure-records:read", "GET", "/api/v1/production/pressure/records/merged"),
    ApiBindingDef("production:pressure-records:export", "GET", "/api/v1/production/pressure/records/export/by-area"),
    ApiBindingDef("production:pressure-records:create", "POST", "/api/v1/production/pressure/records/manual"),
    ApiBindingDef("production:pressure-records:create", "POST", "/api/v1/production/pressure/records/manual/batch"),
    ApiBindingDef("production:pressure-records:create", "POST", "/api/v1/production/pressure/records/ocr"),
    ApiBindingDef("production:pressure-records:create", "POST", "/api/v1/production/pressure/records/merged/delete"),
    ApiBindingDef("production:pressure-records:delete", "POST", "/api/v1/production/pressure/records/merged/batch-delete"),
    ApiBindingDef("production:pressure-records:create", "POST", "/api/v1/production/pressure/records/merged/update"),
    ApiBindingDef("production:pressure-records:read", "GET", "/api/v1/production/pressure/records/{record_id}"),
    ApiBindingDef("production:pressure-records:update", "PATCH", "/api/v1/production/pressure/records/{record_id}/audit"),
    ApiBindingDef("production:pressure-records:update", "PATCH", "/api/v1/production/pressure/records/batch-audit"),
    ApiBindingDef("production:pressure-records:delete", "DELETE", "/api/v1/production/pressure/records/{record_id}"),
    ApiBindingDef("production:pressure-records:delete", "POST", "/api/v1/production/pressure/records/batch-delete"),
    ApiBindingDef("production:pressure-audit:read", "GET", "/api/v1/production/pressure/audit/stats"),
    ApiBindingDef("production:pressure-ocr-tasks:read", "GET", "/api/v1/production/pressure/ocr-tasks"),
    ApiBindingDef("production:pressure-ocr-tasks:create", "POST", "/api/v1/production/pressure/ocr-tasks"),
    ApiBindingDef("production:pressure-ocr-tasks:read", "GET", "/api/v1/production/pressure/ocr-tasks/{task_id}"),
    ApiBindingDef("production:pressure-ocr-tasks:update", "POST", "/api/v1/production/pressure/ocr-tasks/{task_id}/submit"),
    ApiBindingDef("production:pressure-data-master:read", "GET", "/api/v1/production/pressure/data-master"),
    ApiBindingDef("production:pressure-data-master:create", "POST", "/api/v1/production/pressure/data-master"),
    ApiBindingDef("production:pressure-data-master:create", "POST", "/api/v1/production/pressure/data-master/batch"),
    ApiBindingDef("production:pressure-data-master:read", "GET", "/api/v1/production/pressure/data-master/{item_id}"),
    ApiBindingDef("production:pressure-data-master:update", "PUT", "/api/v1/production/pressure/data-master/{item_id}"),
    ApiBindingDef("production:pressure-data-master:delete", "DELETE", "/api/v1/production/pressure/data-master/{item_id}"),
    ApiBindingDef("production:pressure-data-master:delete", "POST", "/api/v1/production/pressure/data-master/batch-delete"),
    ApiBindingDef("production:pressure-notifications:read", "GET", "/api/v1/production/pressure/notifications"),
    ApiBindingDef("production:pressure-notifications:update", "PATCH", "/api/v1/production/pressure/notifications/{notification_id}/read"),
    ApiBindingDef("production:pressure-notifications:update", "PATCH", "/api/v1/production/pressure/notifications/read-all"),
)


# ── 登录入口 / 当前用户自取（豁免绑定兜底）─────────────────────────
# 这两类接口无法绑定权限码，若按「未登记即 403」处理，开启
# `PERMISSION_ENFORCE_ENABLED` 后登录会整体挂掉：
# - 登录入口（auth/*）：调用方还没登录，不可能持有权限码；
# - 当前用户自取（me）：只要求「已登录」，权限判定交给路由自身的 require_user。
# 因此它们只做豁免登记，不参与权限绑定。
EXEMPT_ROUTES: tuple[tuple[str, str], ...] = (
    ("GET", "/api/v1/identity/auth/login"),
    ("GET", "/api/v1/identity/auth/callback"),
    ("GET", "/api/v1/identity/auth/logout"),
    ("POST", "/api/v1/identity/auth/local/login"),
    ("POST", "/api/v1/identity/auth/test-login"),
    ("GET", "/api/v1/identity/me"),
    # 自助改密：任何登录用户都可能需要（尤其被标记「首登强制改密」时），
    # 不挂权限码，判定交给路由自身的 require_user
    ("POST", "/api/v1/identity/me/password"),
    # 菜单栏配置读取：每个登录用户的导航渲染都要读，只要求已登录（写操作用 ops:manage）
    ("GET", "/api/v1/system/menus/config"),


)


# ── 便捷索引 ──────────────────────────────────────────────────────

PERMISSIONS_BY_CODE: dict[str, PermissionDef] = {p.code: p for p in ALL_PERMISSIONS}
ROLES_BY_CODE: dict[str, RoleDef] = {r.code: r for r in ALL_BUILTIN_ROLES}
BINDINGS_BY_ROUTE: dict[tuple[str, str], ApiBindingDef] = {(b.method, b.route_template): b for b in API_BINDINGS}

# 受保护路由前缀：这些前缀下的请求必须已登记绑定，否则 403
PROTECTED_ROUTE_PREFIXES: tuple[str, ...] = tuple(
    f"/api/v1/{module.path.lstrip('/')}" for module in BUSINESS_MODULES
) + (
    "/api/v1/permission",
    "/api/v1/identity",
    "/api/v1/system",
    "/api/v1/audit",
)


def is_protected_route(path: str) -> bool:
    """判断路由是否属于受保护前缀。"""
    return any(path == prefix or path.startswith(prefix + "/") for prefix in PROTECTED_ROUTE_PREFIXES)


# ── 按模块灰度强制 ────────────────────────────────────────────────
# `PERMISSION_ENFORCE_MODULES`（config.py）允许只对已完成绑定的模块开强制，
# 未完成的模块暂不受兜底影响（接入一个开一个，避免一刀切 403）。

# 路径前缀 → 模块码（含平台域伪模块码，用于灰度集合取值）
_PREFIX_TO_MODULE: dict[str, str] = {
    **{f"/api/v1/{m.path.lstrip('/')}": m.code for m in BUSINESS_MODULES},
    "/api/v1/permission": "permission",
    "/api/v1/identity": "identity",
    "/api/v1/system": "system",
    "/api/v1/audit": "audit",
}

# 灰度集合可用模块码全集（校验配置拼写用）
ENFORCEABLE_MODULE_CODES: frozenset[str] = frozenset(_PREFIX_TO_MODULE.values())

# ── 已完成接入的模块（CI 完整性门禁范围）─────────────────────────
# 模块的全部接口绑定登记完成后，把模块码加到这里：
# - scripts/ci/check_permissions.py 会对它执行完整性校验
#   （每个路由都有绑定或豁免、每个 require_permission 码都存在）；
# - 此后才允许把该模块码加入部署配置的 PERMISSION_ENFORCE_MODULES 开强制。
ENFORCE_READY_MODULES: tuple[str, ...] = ("research", "environment", "administration", "warehouse", "procurement", "safety", "energy", "equipment", "registration", "quality", "hr", "production")


def module_for_path(path: str) -> str | None:
    """反查请求路径所属模块码；非受保护路径返回 None。"""
    for prefix, code in _PREFIX_TO_MODULE.items():
        if path == prefix or path.startswith(prefix + "/"):
            return code
    return None


def is_enforced_route(path: str, enabled_modules: frozenset[str]) -> bool:
    """该路径是否处于强制兜底范围：受保护 且 （灰度集合为空=全部 / 或所属模块在集合内）。"""
    code = module_for_path(path)
    if code is None:
        return False
    return not enabled_modules or code in enabled_modules
