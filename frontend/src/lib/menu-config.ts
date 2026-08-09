export interface SubMenuItem {
  key: string
  label: string
  path: string
  children?: SubMenuItem[]   // 嵌套子菜单 → Ant Design SubMenu
  disabled?: boolean         // 灰显占位，功能未开发
}

export interface ModuleMenu {
  key: string
  label: string
  icon: string
  path: string
  children: SubMenuItem[]
}

export const moduleMenus: ModuleMenu[] = [
  {
    key: "production",
    label: "生产管理",
    icon: "factory",
    path: "/production",
    children: [
      { key: "batches", label: "批次管理", path: "/production/batches" },
      { key: "plan", label: "生产计划（开发中）", path: "/production/plan" },
      { key: "process", label: "工艺规程（开发中）", path: "/production/process" },
      { key: "records", label: "生产记录（开发中）", path: "/production/records" },
      { key: "balance", label: "物料平衡（开发中）", path: "/production/balance" },
      { key: "product-output", label: "产品管理", path: "/production/product-output" },
      { key: "label-verification", label: "标签复核", path: "/production/label-verification" },
      { 
        key: "pressure", 
        label: "压差统计", 
        path: "/production/pressure",
        children: [
          { key: "pressure-audit", label: "压差审计", path: "/production/pressure/audit" },
          { key: "pressure-manual", label: "手动录入", path: "/production/pressure/manual-input" },
          { key: "pressure-ocr", label: "OCR录入", path: "/production/pressure/ocr-input" },
          { key: "pressure-points", label: "测点管理", path: "/production/pressure/point-management" },
          { key: "pressure-records", label: "压差记录", path: "/production/pressure/records" },
        ]
      },
    ],
  },
  {
    key: "equipment",
    label: "设备管理",
    icon: "cog",
    path: "/equipment",
    children: [
      { key: "stats", label: "设备仪表盘", path: "/equipment/stats" },
      { key: "assets", label: "设备台账", path: "/equipment/assets" },
      { key: "maintenance", label: "维护保养", path: "/equipment/maintenance" },
      { key: "inspection", label: "设备巡检", path: "/equipment/inspection" },
      { key: "spare-parts", label: "备件管理", path: "/equipment/spare-parts" },
      { key: "personnel", label: "人员配置", path: "/equipment/personnel" },
      { key: "settings", label: "模块配置", path: "/equipment/settings" },
    ],
  },
  {
    key: "energy",
    label: "能源管理",
    icon: "bolt",
    path: "/energy",
    children: [
      { key: "overview", label: "能源总览", path: "/energy" },
      { key: "monthly", label: "月度记录", path: "/energy/monthly" },
      { key: "devices", label: "数据源配置", path: "/energy/devices" },
      { key: "alerts", label: "预警管理", path: "/energy/alerts" },
      { key: "collect-logs", label: "采集日志", path: "/energy/collect-logs" },
    ],
  },

  // ═══════════════════════════════════════════════════════
  // 安全管理模块 — 按化工安全生产管理体系分级
  // ═══════════════════════════════════════════════════════
  {
    key: "safety",
    label: "安全管理",
    icon: "shield",
    path: "/safety",
    children: [
      // ── 系统配置 ──
      {
        key: "system-config",
        label: "系统配置",
        path: "",
        children: [
          { key: "module-settings", label: "模块配置", path: "/safety/settings" },
        ],
      },
      // ── 作业安全 ──
      {
        key: "ops-safety",
        label: "作业安全",
        path: "",
        children: [
          { key: "special-ops-mgmt", label: "特殊作业管理", path: "/safety/special-ops" },
          { key: "special-ops-personnel", label: "特殊作业人员", path: "/safety/special-ops/personnel" },
          { key: "daily-risk-report", label: "关键风险作业报备", path: "/safety/risk-reporting" },
        ],
      },
      // ── 风险与隐患 ──
      {
        key: "risk-hazard",
        label: "风险与隐患",
        path: "",
        children: [
          {
            key: "risk-grading",
            label: "风险分级管控",
            path: "",
            children: [
              { key: "hazard-identification", label: "危险源辨识工作流", path: "/safety/hazard-identification" },
              { key: "hazard-identification-new", label: "新建危险源辨识", path: "/safety/hazard-identification/new" },
              { key: "hazard-ledger", label: "危险源辨识台账", path: "/safety/hazard-identification/ledger" },
            ],
          },
          {
            key: "hazard-inspection",
            label: "隐患排查治理",
            path: "",
            children: [
              { key: "hazard-inspection-ledger", label: "隐患台账", path: "/safety/hazard-ledger" },
              { key: "hazard", label: "隐患管理", path: "/safety/hazard" },
            ],
          },
          {
            key: "regulation",
            label: "安全操规管理",
            path: "",
            children: [
              { key: "regulation-list", label: "安全操规台账", path: "/safety/regulation" },
              { key: "regulation-generator", label: "标准化生成", path: "/safety/regulation/generator" },
            ],
          },
          {
            key: "ehs-change",
            label: "EHS变更管理",
            path: "",
            children: [
              { key: "ehs-change-apply", label: "EHS变更申请", path: "/safety/ehs-change" },
            ],
          },
        ],
      },
      // ── 应急与事故 ──
      {
        key: "emergency-accident",
        label: "应急与事故",
        path: "",
        children: [
          { key: "accident-ledger", label: "事故台账", path: "/safety/accident" },
          { key: "emergency-plan", label: "应急预案", path: "", disabled: true },
        ],
      },
      // ── 安全培训与检查 ──
      {
        key: "training-check",
        label: "安全培训与检查",
        path: "",
        children: [
          { key: "safety-check", label: "安全检查", path: "/safety/check" },
          { key: "safety-training", label: "安全培训", path: "/safety/training" },
          { key: "contractor", label: "相关方管理", path: "/safety/contractor" },
        ],
      },
      // ── 职业健康 ──
      {
        key: "occupational-health-group",
        label: "职业健康",
        path: "",
        children: [
          { key: "oh-monitor", label: "职业危害因素监测", path: "/safety/occupational-health" },
        ],
      },
      // ── 法规与安全信息 ──
      {
        key: "regulation-info",
        label: "法规与安全信息",
        path: "",
        children: [
          { key: "knowledge-base", label: "安全知识库", path: "/safety/knowledge-base" },
          { key: "knowledge-graph", label: "知识图谱", path: "/safety/knowledge-base/graph" },
        ],
      },
    ],
  },

  // ═══════════════════════════════════════════════════════
  // 质量管理模块
  // ═══════════════════════════════════════════════════════
  {
    key: "quality",
    label: "质量管理",
    icon: "check-circle",
    path: "/quality",
    children: [
      // ── AI工具 ──
      {
        key: "ai-tools",
        label: "AI工具",
        path: "",
        children: [
          { key: "ai-config", label: "AI配置", path: "/quality/ai-config" },
          { key: "ai-log", label: "AI日志", path: "/quality/ai-log" },
        ],
      },
      // ── 偏差管理 ──
      {
        key: "deviation-mgmt",
        label: "偏差管理",
        path: "",
        children: [
          { key: "deviation", label: "偏差管理", path: "/quality/deviation" },
          { key: "deviation-report", label: "偏差报告", path: "/quality/deviation/report" },
          { 
            key: "deviation-automation",
            label: "偏差自动化",
            path: "",
            children: [
              { key: "deviation-automation-create", label: "创建偏差自动化", path: "/quality/deviation-automation/create" },
              { key: "deviation-automation-history", label: "偏差自动化历史", path: "/quality/deviation-automation/history" },
              { key: "deviation-automation-sop", label: "偏差自动化SOP", path: "/quality/deviation-automation/sop" },
              { key: "deviation-automation-templates", label: "偏差自动化模板", path: "/quality/deviation-automation/templates" },
            ]
          },
          {
            key: "deviation-flow",
            label: "偏差流程",
            path: "",
            children: [
              { key: "deviation-flow-create", label: "创建偏差流程", path: "/quality/deviation-flow/create" },
              { key: "deviation-flow-progress", label: "偏差流程进度", path: "/quality/deviation-flow/progress" },
              { key: "deviation-flow-query", label: "偏差流程查询", path: "/quality/deviation-flow/query" },
              { key: "deviation-flow-settings", label: "偏差流程设置", path: "/quality/deviation-flow/settings" },
            ]
          },
        ],
      },
      // ── 文档检查 ──
      {
        key: "doc-check",
        label: "文档检查",
        path: "",
        children: [
          { key: "doc-check-list", label: "文档检查", path: "/quality/doc-check" },
          { key: "doc-check-new", label: "新建文档检查", path: "/quality/doc-check/new" },
          { key: "fqc", label: "FQC管理", path: "/quality/fqc" },
        ],
      },
      // ── 检验管理 ──
      {
        key: "inspection-mgmt",
        label: "检验管理",
        path: "",
        children: [
          { key: "inspection", label: "质量检验", path: "/quality/inspection" },
          { key: "inspection-standards", label: "检验标准", path: "/quality/inspection/standards" },
          { key: "inspection-table", label: "检验表格", path: "/quality/inspection-table" },
          { key: "ipqc", label: "IPQC管理", path: "/quality/ipqc" },
          { key: "iqc", label: "IQC管理", path: "/quality/iqc" },
        ],
      },
      // ── 仪器校准 ──
      {
        key: "instrument-calibration",
        label: "仪器校准",
        path: "",
        children: [
          { key: "instrument", label: "仪器校准管理", path: "/quality/instrument" },
          { key: "instrument-list", label: "仪器设备台账", path: "/quality/instrument/list" },
          { key: "instrument-records", label: "校准记录", path: "/quality/instrument/records" },
          { key: "instrument-settings", label: "提醒设置", path: "/quality/instrument/settings" },
        ],
      },
      // ── 物料管理 ──
      {
        key: "material-mgmt",
        label: "物料管理",
        path: "",
        children: [
          { key: "material-report", label: "物料报告", path: "/quality/material-report" },
          { key: "material-report-template", label: "物料报告模板", path: "/quality/material-report/template" },
          { key: "reagent", label: "试剂管理", path: "/quality/reagent" },
          { key: "reagent-reminder", label: "试剂库存提醒", path: "/quality/reagent/reminder" },
          { key: "retention", label: "留样管理", path: "/quality/retention" },
          { key: "sampling", label: "取样管理", path: "/quality/sampling" },
        ],
      },
      // ── SOP管理 ──
      {
        key: "sop-mgmt",
        label: "SOP管理",
        path: "",
        children: [
          { key: "sop-ai-batch", label: "批量巡检", path: "/quality/sop-ai/batch" },
          { key: "sop-ai-preview", label: "单文件预审", path: "/quality/sop-ai/preview" },
          { key: "sop-ai-records", label: "校验记录台账", path: "/quality/sop-ai/records" },
        ],
      },
      // ── 稳定性研究 ──
      {
        key: "stability",
        label: "稳定性研究",
        path: "",
        children: [
          { key: "stability-overview", label: "稳定性研究", path: "/quality/stability" },
          { key: "stability-plan", label: "方案录入", path: "/quality/stability/plan" },
          { key: "stability-report", label: "总结报告", path: "/quality/stability/report" },
          { key: "stability-result", label: "检测结果", path: "/quality/stability/result" },
          { key: "stability-settings", label: "提醒设置", path: "/quality/stability/settings" },
        ],
      },
      // ── 静态数据 ──
      {
        key: "static-data",
        label: "静态数据",
        path: "",
        children: [
          { key: "static-data-overview", label: "业务静态数据", path: "/quality/static-data" },
          { key: "static-data-audit", label: "审计数据", path: "/quality/static-data/audit" },
          { key: "static-data-chrom-column", label: "色谱柱管理", path: "/quality/static-data/chrom-column" },
          { key: "static-data-hplc-reference", label: "液相对照品", path: "/quality/static-data/hplc-reference" },
          { key: "static-data-medium", label: "培养基管理", path: "/quality/static-data/medium" },
          { key: "static-data-standard", label: "标准品管理", path: "/quality/static-data/standard" },
          { key: "static-data-storage-condition", label: "贮存条件管理", path: "/quality/static-data/storage-condition" },
        ],
      },
      // ── 其他 ──
      { key: "calculator", label: "计算器", path: "/quality/calculator" },
      { key: "cpv", label: "持续工艺验证", path: "/quality/cpv" },
      { key: "department-contacts", label: "部门联系人配置", path: "/quality/department-contacts" },
    ],
  },

  // ═══════════════════════════════════════════════════════
  // 研发管理模块
  // ═══════════════════════════════════════════════════════
  {
    key: "research",
    label: "研发管理",
    icon: "experiment",
    path: "/research",
    children: [
      { key: "research-overview", label: "研发概览", path: "/research" },
      { key: "projects", label: "研发项目", path: "/research/projects" },
      { key: "initiations", label: "立项管理", path: "/research/initiations" },
      { key: "route-development", label: "打通路线", path: "/research/route-development" },
      { key: "process-optimization", label: "工艺优化", path: "/research/process-optimization" },
      { key: "pilot-study", label: "中试研究", path: "/research/pilot-workflow" },
      { key: "process-validation", label: "工艺验证", path: "/research/process-validation" },
      { key: "registration-filing", label: "申报资料", path: "/research/registration-filing" },
      { key: "research-tracks", label: "研究项", path: "/research/research-tracks" },
      { key: "deliverable-templates", label: "交付物模板", path: "/research/deliverable-templates" },
      { key: "bayesian", label: "贝叶斯优化", path: "/research/bayesian" },
      { key: "ich-analysis", label: "ICH分析", path: "/research/ich-analysis" },
      { key: "reports", label: "研发报告", path: "/research/reports" },
    ],
  },

  // ═══════════════════════════════════════════════════════
  // 注册管理模块
  // ═══════════════════════════════════════════════════════
  {
    key: "registration",
    label: "注册管理",
    icon: "file-text",
    path: "/registration",
    children: [
      { key: "registration-overview", label: "注册概览", path: "/registration" },
      { key: "projects", label: "注册项目", path: "/registration/projects" },
      {
        key: "regulation",
        label: "法规跟踪",
        path: "",
        children: [
          { key: "regulation-dashboard", label: "法规看板", path: "/registration/regulation" },
          { key: "regulation-list", label: "法规列表", path: "/registration/regulation/list" },
        ],
      },
      { key: "authorization-letter", label: "授权书管理", path: "/registration/authorization-letter" },
      { key: "dossier-writer", label: "申报资料撰写", path: "/registration/dossier-writer" },
      { key: "reference-standard", label: "参考标准", path: "/registration/reference-standard" },
      { key: "review", label: "申报进度查询", path: "/registration/review" },
      { key: "supplementary-reply", label: "补充回复", path: "/registration/supplementary-reply" },
      { key: "validation-audit", label: "验证审计", path: "/registration/validation-audit" },
      { key: "ledger", label: "注册台账", path: "/registration/ledger" },
    ],
  },

  // ═══════════════════════════════════════════════════════
  // 人事管理模块
  // ═══════════════════════════════════════════════════════
  {
    key: "hr",
    label: "人事管理",
    icon: "team",
    path: "/hr",
    children: [
      { key: "hr-overview", label: "人事概览", path: "/hr" },
      { key: "departments", label: "部门管理", path: "/hr/departments" },
      { key: "profile", label: "员工档案", path: "/hr/profile" },
      { key: "recruitment", label: "招聘管理", path: "/hr/recruitment" },
      { key: "onboarding", label: "入职管理", path: "/hr/onboarding" },
      { key: "offboarding", label: "离职管理", path: "/hr/offboarding" },
      { key: "attendance", label: "考勤管理", path: "/hr/attendance" },
      { key: "roster", label: "排班管理", path: "/hr/roster" },
      { key: "system-settings", label: "系统设置", path: "/hr/system/settings" },
      {
        key: "training",
        label: "培训管理",
        path: "/hr/training",
        children: [
          { key: "training-overview", label: "培训概览", path: "/hr/training" },
          { key: "onboarding-training", label: "新员工入职培训", path: "/hr/training/onboarding" },
          { key: "training-notification", label: "培训通知", path: "/hr/training/notification" },
          { key: "training-ai-exam", label: "AI 出题", path: "/hr/training/ai-exam" },
          { key: "training-annual-plan", label: "年度培训计划", path: "/hr/training/annual-plan" },
          { key: "training-annual-plan-new", label: "新建年度培训计划", path: "/hr/training/annual-plan/new" },
          { key: "training-ledger", label: "培训台账", path: "/hr/training/ledger" },
          { key: "training-ledger-new", label: "新建培训台账", path: "/hr/training/ledger/new" },
          { key: "trainers", label: "内训师台账", path: "/hr/training/trainers" },
          { key: "evaluation-form", label: "培训效果评估表", path: "/hr/training/evaluation-form" },
          { key: "sop-catalog", label: "SOP 目录", path: "/hr/training/sop-catalog" },
          { key: "training-records", label: "培训列表", path: "/hr/training/records" },
          { key: "training-select-tasks", label: "培训选择任务", path: "/hr/training/select-tasks" },
          { key: "training-specialists", label: "培训专员管理", path: "/hr/training/specialists" },
        ],
      },
    ],
  },

  // ═══════════════════════════════════════════════════════
  // 行政管理模块
  // ═══════════════════════════════════════════════════════
  {
    key: "administration",
    label: "行政管理",
    icon: "setting",
    path: "/administration",
    children: [
      { key: "administration-overview", label: "行政概览", path: "/administration" },
      { key: "notice", label: "公告通知", path: "/administration/notice" },
      { key: "meeting", label: "会议管理", path: "/administration/meeting" },
      { key: "meeting-ledger", label: "物品台账", path: "/administration/meeting/ledger" },
      { key: "meeting-requests", label: "领用记录", path: "/administration/meeting/requests" },
      { key: "meeting-requisitions", label: "领用申请", path: "/administration/meeting/requisitions" },
      { key: "approval", label: "文件审批", path: "/administration/approval" },
      { key: "it-tickets", label: "IT工单", path: "/administration/it-tickets" },
      { key: "vehicle-requests", label: "用车数据", path: "/administration/vehicle-requests" },
      { key: "vehicles", label: "车辆管理", path: "/administration/vehicles" },
      { key: "login-logs", label: "登录记录", path: "/administration/login-logs" },
    ],
  },

  // ═══════════════════════════════════════════════════════
  // 采购管理模块
  // ═══════════════════════════════════════════════════════
  {
    key: "procurement",
    label: "采购管理",
    icon: "shopping-cart",
    path: "/procurement",
    children: [
      { key: "procurement-overview", label: "采购概览", path: "/procurement" },
      { key: "request", label: "采购申请", path: "/procurement/request" },
      { key: "supplier", label: "供应商管理", path: "/procurement/supplier" },
      { key: "order", label: "采购订单", path: "/procurement/order" },
      { key: "invoice-recognition", label: "发票识别", path: "/procurement/invoice-recognition" },
      { key: "contract-summary", label: "合同汇总", path: "/procurement/contract-summary" },
      { key: "contract-generation", label: "合同生成", path: "/procurement/contract-generation" },
      { key: "approval", label: "审批流程", path: "/procurement/approval" },
    ],
  },

  // ═══════════════════════════════════════════════════════
  // 仓储管理模块
  // ═══════════════════════════════════════════════════════
  {
    key: "warehouse",
    label: "仓储管理",
    icon: "database",
    path: "/warehouse",
    children: [
      { key: "warehouse-overview", label: "仓储概览", path: "/warehouse" },
      { key: "inventory", label: "库存管理", path: "/warehouse/inventory" },
      { key: "inout", label: "出入库记录", path: "/warehouse/inout" },
      { key: "stocktake", label: "库存盘点", path: "/warehouse/stocktake" },
      { key: "feishu-config", label: "飞书配置", path: "/warehouse/feishu-config" },
      { key: "packaging", label: "包装管理", path: "/warehouse/packaging" },
      { key: "product", label: "成品管理", path: "/warehouse/product" },
      { key: "raw-material", label: "原料管理", path: "/warehouse/raw-material" },
    ],
  },

  // ═══════════════════════════════════════════════════════
  // 环保管理模块
  // ═══════════════════════════════════════════════════════
  {
    key: "environment",
    label: "环保管理",
    icon: "global",
    path: "/environment",
    children: [
      { key: "environment-overview", label: "环保概览", path: "/environment" },
    ],
  },

  // ═══════════════════════════════════════════════════════
  // 系统设置模块
  // ═══════════════════════════════════════════════════════
  {
    key: "settings",
    label: "系统设置",
    icon: "setting",
    path: "/settings",
    children: [
      { key: "settings-overview", label: "系统设置", path: "/settings" },
    ],
  },
]

export function getModuleByKey(key: string): ModuleMenu | undefined {
  return moduleMenus.find((m) => m.key === key)
}


