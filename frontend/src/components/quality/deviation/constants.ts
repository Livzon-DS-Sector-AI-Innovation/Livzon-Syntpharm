/**
 * 偏差台账前端展示常量。
 *
 * 只保留**纯展示**内容：路由、配色、图表色板、超期口径说明。
 * 状态/分级的中文标签一律用后端随行返回的 status_label / level_label，
 * 避免前后端各维护一份 12 态字典而漂移。
 */

/** 台账路由：看盘、表格、表单三处共用同一地址 */
export const DEVIATION_LEDGER_PATH = '/quality/deviation/ledger'

/** 台账详情路由（整页，不再使用抽屉） */
export function deviationDetailPath(id: string): string {
  return `/quality/deviation/${id}`
}

/** 原因分类选项（与后端 REASON_CATEGORIES 对齐） */
export const DEVIATION_REASON_CATEGORIES = ['人员', '设施设备', '产品物料', '文件', '环境', '其它'] as const

/** 偏差分级选项（与后端 DEVIATION_LEVELS 对齐） */
export const DEVIATION_LEVEL_OPTIONS = [
  { value: 'minor', label: '微小' },
  { value: 'moderate', label: '中等' },
  { value: 'major', label: '严重' },
] as const

/** 状态配色：处理中偏蓝、待审核偏橙、终态偏绿/灰、退回红 */
export const DEVIATION_STATUS_COLORS: Record<string, string> = {
  draft: 'default',
  pending_ai_analysis: 'geekblue',
  pending_investigation: 'blue',
  pending_dept_head_review: 'gold',
  pending_cross_dept_head_review: 'gold',
  pending_qa_review: 'gold',
  pending_qa_head_review: 'orange',
  pending_quality_head_review: 'orange',
  pending_final_code: 'cyan',
  returned: 'red',
  closed: 'green',
  cancelled: 'default',
}

/** 分级配色（库内 minor/moderate/major） */
export const DEVIATION_LEVEL_COLORS: Record<string, string> = {
  minor: 'blue',
  moderate: 'orange',
  major: 'red',
}

/** 图表配色：部门分布与状态分布共用，主色优先 */
export const DEVIATION_CHART_COLORS = [
  '#5645d4',
  '#0075de',
  '#1aae39',
  '#dd5b00',
  '#e03131',
  '#7d5bc6',
  '#00a6a6',
  '#c8a200',
  '#b0aea8',
]

/** 超期阈值说明文案（看盘页提示条，与后端 STEP_OVERDUE_DAYS 对齐） */
export const DEVIATION_OVERDUE_HINT =
  '超期口径：待AI分析 1 天、待调查 7 天、待部门/跨部门负责人 3 天、待所属QA 5 天、待QA负责人与质量负责人 3 天、待输入最终编号 3 天，超过阈值即标记为超期。'