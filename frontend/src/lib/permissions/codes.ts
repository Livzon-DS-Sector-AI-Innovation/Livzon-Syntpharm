/**
 * 平台权限码常量（与后端 app/platform/permission/registry.py 的 PLATFORM_PERMISSIONS 对齐）。
 *
 * 为什么要用常量：写错权限码在编译期就能发现（`can()` 的参数是联合类型），
 * 而不是运行到点击按钮时才静默失效。
 *
 * 新增权限码时**两边都要改**：后端 registry + 这里。
 */

/**
 * 业务模块访问码（**菜单级**：每个模块 1 个）。
 *
 * 与后端 `BUSINESS_MODULE_PERMISSIONS`（由 `BUSINESS_MODULES` 生成）一一对应：
 * `<module>:module:read`。只控制「模块菜单是否可见 + 模块页面能否进入」；
 * 具体接口权限（`<module>:<resource>:<action>`）后续按需追加，两层正交。
 */
export const MODULE_PERM = {
  productionRead: 'production:module:read',
  equipmentRead: 'equipment:module:read',
  safetyRead: 'safety:module:read',
  environmentRead: 'environment:module:read',
  energyRead: 'energy:module:read',
  warehouseRead: 'warehouse:module:read',
  procurementRead: 'procurement:module:read',
  administrationRead: 'administration:module:read',
  hrRead: 'hr:module:read',
  researchRead: 'research:module:read',
  registrationRead: 'registration:module:read',
  qualityRead: 'quality:module:read',
} as const

/** 研发管理（research）接口级权限码，与后端 RESEARCH_PERMISSIONS 一一对应 */
export const RESEARCH_PERM = {
  researchProjectRead: 'research:project:read',
  researchProjectCreate: 'research:project:create',
  researchProjectUpdate: 'research:project:update',
  researchProjectDelete: 'research:project:delete',
  researchProjectSubmit: 'research:project:submit',
  researchProjectExport: 'research:project:export',
  researchTrackRead: 'research:track:read',
  researchTrackCreate: 'research:track:create',
  researchTrackUpdate: 'research:track:update',
  researchTrackDelete: 'research:track:delete',
  researchTrackExport: 'research:track:export',
  researchInitiationRead: 'research:initiation:read',
  researchInitiationCreate: 'research:initiation:create',
  researchInitiationUpdate: 'research:initiation:update',
  researchInitiationDelete: 'research:initiation:delete',
  researchRouteRead: 'research:route:read',
  researchRouteCreate: 'research:route:create',
  researchRouteUpdate: 'research:route:update',
  researchRouteDelete: 'research:route:delete',
  researchExperimentLogRead: 'research:experiment-log:read',
  researchExperimentLogCreate: 'research:experiment-log:create',
  researchExperimentLogUpdate: 'research:experiment-log:update',
  researchExperimentLogDelete: 'research:experiment-log:delete',
  researchExperimentLogExport: 'research:experiment-log:export',
  researchPilotStudyRead: 'research:pilot-study:read',
  researchPilotStudyCreate: 'research:pilot-study:create',
  researchPilotStudyUpdate: 'research:pilot-study:update',
  researchPilotStudyDelete: 'research:pilot-study:delete',
  researchPilotWorkflowRead: 'research:pilot-workflow:read',
  researchPilotWorkflowCreate: 'research:pilot-workflow:create',
  researchPilotWorkflowDelete: 'research:pilot-workflow:delete',
  researchPilotWorkflowSubmit: 'research:pilot-workflow:submit',
  researchPilotWorkflowApprove: 'research:pilot-workflow:approve',
  researchProcessValidationRead: 'research:process-validation:read',
  researchProcessValidationCreate: 'research:process-validation:create',
  researchProcessValidationUpdate: 'research:process-validation:update',
  researchProcessValidationDelete: 'research:process-validation:delete',
  researchRegistrationFilingRead: 'research:registration-filing:read',
  researchRegistrationFilingCreate: 'research:registration-filing:create',
  researchRegistrationFilingUpdate: 'research:registration-filing:update',
  researchRegistrationFilingDelete: 'research:registration-filing:delete',
  researchDeliverableTemplateRead: 'research:deliverable-template:read',
  researchDeliverableTemplateCreate: 'research:deliverable-template:create',
  researchDeliverableTemplateUpdate: 'research:deliverable-template:update',
  researchDeliverableTemplateDelete: 'research:deliverable-template:delete',
  researchStageDeliverableRead: 'research:stage-deliverable:read',
  researchStageDeliverableCreate: 'research:stage-deliverable:create',
  researchStageDeliverableUpdate: 'research:stage-deliverable:update',
  researchStageDeliverableDelete: 'research:stage-deliverable:delete',
  researchOptimizationRead: 'research:optimization:read',
  researchOptimizationCreate: 'research:optimization:create',
  researchOptimizationUpdate: 'research:optimization:update',
  researchOptimizationDelete: 'research:optimization:delete',
  researchIchRead: 'research:ich:read',
  researchIchCreate: 'research:ich:create',
  researchIchDelete: 'research:ich:delete',
  researchLiteratureCreate: 'research:literature:create',
  researchReportRead: 'research:report:read',
  researchReportCreate: 'research:report:create',
  researchReportUpdate: 'research:report:update',
  researchReportDelete: 'research:report:delete',
} as const

export const PERM = {
  userRead: 'platform:user:read',
  userManage: 'platform:user:manage',
  roleRead: 'platform:role:read',
  roleManage: 'platform:role:manage',
  permissionRead: 'platform:permission:read',
  apiBindingRead: 'platform:api-binding:read',
  grantRead: 'platform:grant:read',
  grantManage: 'platform:grant:manage',
  auditRead: 'platform:audit:read',
  configRead: 'platform:config:read',
  configManage: 'platform:config:manage',
  opsRead: 'platform:ops:read',
  opsManage: 'platform:ops:manage',
  ...MODULE_PERM,
  ...RESEARCH_PERM,
} as const

export type PermissionCode = (typeof PERM)[keyof typeof PERM]

/** 平台全部权限码（供校验脚本比对后端 registry 用） */
export const ALL_PERMISSION_CODES: readonly string[] = Object.values(PERM)

// ── 统一文案 ───────────────────────────────────────────────────────
// 无权限时给"权限不足"的提示，而不是把 403 这种技术状态码抛给用户

export const PERMISSION_DENIED_TITLE = '当前用户权限不足'
export const PERMISSION_DENIED_HINT = '请联系管理员为你的账号分配相应权限'
