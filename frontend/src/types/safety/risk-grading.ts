/**
 * 风险分级管控台账共享常量与契约类型派生。
 *
 * 常量与后端 app/modules/safety/risk_grading.py 保持一致：
 * - 管控层级：需求文档给定的 28 个部门（不改动隐患/检查表单的 DEPARTMENT_OPTIONS）
 * - 控制措施：作业活动台账五项原文，逐字对齐需求文档
 * - 残余风险：仅三个选项（无 4 级）
 * - 执行层级：仅车间 / 班组长
 */

import type { components, operations } from '@/types/generated/schema'

export type WorkActivityHazard = components['schemas']['WorkActivityHazardResponse']
export type WorkActivityHazardCreate = components['schemas']['WorkActivityHazardCreate']
export type WorkActivityHazardUpdate = components['schemas']['WorkActivityHazardUpdate']
export type WorkActivityHazardListApiResponse = components['schemas']['WorkActivityHazardListApiResponse']
export type WorkActivityHazardApiResponse = components['schemas']['WorkActivityHazardApiResponse']

type WorkActivityHazardListOperation =
  operations['list_work_activity_hazards_api_v1_safety_work_activity_hazards_get']
type WorkActivityHazardExportOperation =
  operations['export_work_activity_hazards_api_v1_safety_work_activity_hazards_export_get']

export type WorkActivityHazardListParams = NonNullable<
  WorkActivityHazardListOperation['parameters']['query']
>
export type WorkActivityHazardExportParams = NonNullable<
  WorkActivityHazardExportOperation['parameters']['query']
>

export type EquipmentFacilityHazard = components['schemas']['EquipmentFacilityHazardResponse']
export type EquipmentFacilityHazardCreate = components['schemas']['EquipmentFacilityHazardCreate']
export type EquipmentFacilityHazardUpdate = components['schemas']['EquipmentFacilityHazardUpdate']
export type EquipmentFacilityHazardListApiResponse =
  components['schemas']['EquipmentFacilityHazardListApiResponse']
export type EquipmentFacilityHazardApiResponse = components['schemas']['EquipmentFacilityHazardApiResponse']

type EquipmentFacilityHazardListOperation =
  operations['list_equipment_facility_hazards_api_v1_safety_equipment_facility_hazards_get']
type EquipmentFacilityHazardExportOperation =
  operations['export_equipment_facility_hazards_api_v1_safety_equipment_facility_hazards_export_get']

export type EquipmentFacilityHazardListParams = NonNullable<
  EquipmentFacilityHazardListOperation['parameters']['query']
>
export type EquipmentFacilityHazardExportParams = NonNullable<
  EquipmentFacilityHazardExportOperation['parameters']['query']
>

export interface OptionItem {
  value: string
  label: string
}

export const RISK_GRADING_DEPARTMENT_OPTIONS: OptionItem[] = [
  '106车间',
  'AI创新部',
  '人事行政部',
  '动力部',
  '201车间',
  '202车间',
  '头孢合成制造部公共岗',
  '溶剂回收车间',
  '301车间',
  '302车间',
  '303车间',
  '头孢无菌制造部公共岗',
  '安全中心',
  '环保中心',
  '技术研发部',
  '注册部',
  '仓库',
  '生产部办公室',
  '设备工程部',
  '财务部',
  '质量保证部',
  '质量控制部',
  '采购部',
  '101车间',
  '102车间',
  '103车间',
  '105车间',
  '非头孢制造部公共岗',
].map((value) => ({ value, label: value }))

export const CONTROL_MEASURE_OPTIONS: OptionItem[] = [
  { value: 'engineering', label: '1、工程控制措施，实现本质安全' },
  { value: 'management', label: '2、管理措施，规范安全管理' },
  { value: 'education', label: '3、教育措施，提高从业人员的操作技能和安全意识' },
  { value: 'ppe', label: '4、个体防护设施，减少职业伤害' },
  { value: 'emergency', label: '5、应急处置措施，降低事故伤害' },
]

export const CONTROL_MEASURE_LABELS: Record<string, string> = Object.fromEntries(
  CONTROL_MEASURE_OPTIONS.map((item) => [item.value, item.label]),
)

export const RESIDUAL_RISK_OPTIONS: OptionItem[] = [
  { value: 'level_1', label: '1级低风险' },
  { value: 'level_2', label: '2级一般风险' },
  { value: 'level_3', label: '3级较大风险' },
]

export const RESIDUAL_RISK_LABELS: Record<string, string> = Object.fromEntries(
  RESIDUAL_RISK_OPTIONS.map((item) => [item.value, item.label]),
)

export const EXECUTION_LEVEL_OPTIONS: OptionItem[] = [
  { value: 'workshop', label: '车间' },
  { value: 'team_leader', label: '班组长' },
]

export const EXECUTION_LEVEL_LABELS: Record<string, string> = Object.fromEntries(
  EXECUTION_LEVEL_OPTIONS.map((item) => [item.value, item.label]),
)

export const STANDARD_LINKS = {
  possibleHarm: {
    label: 'GB 6441-2025',
    href: 'https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=39334B61DAD4CC7F9E412A868C567717',
  },
  hazardType: {
    label: 'GB/T 13861-2022',
    href: 'https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=BCBA1F97621C11B4B5A6C10783C93DB1',
  },
} as const

/** 仅用于表单即时预览；最终 D 与级别以后端计算为准。 */
export function computeRiskValue(l: number, e: number, c: number): number {
  return Math.round((l * e * c + Number.EPSILON) * 1e6) / 1e6
}

export function deriveEvaluationGrade(d: number): number {
  if (d > 320) return 4
  if (d > 160) return 3
  if (d > 70) return 2
  return 1
}

/** 设备设施台账措施：与作业活动台账共用稳定 key，展示短标签。 */
export const EQUIPMENT_MEASURE_OPTIONS: OptionItem[] = [
  { value: 'engineering', label: '工程技术' },
  { value: 'management', label: '管理措施' },
  { value: 'education', label: '培训教育' },
  { value: 'ppe', label: '个体防护' },
  { value: 'emergency', label: '应急处置' },
]

export const EQUIPMENT_MEASURE_LABELS: Record<string, string> = Object.fromEntries(
  EQUIPMENT_MEASURE_OPTIONS.map((item) => [item.value, item.label]),
)

export const LIKELIHOOD_LEVEL_OPTIONS: { value: number; label: string }[] = [1, 2, 3, 4, 5].map(
  (value) => ({
    value,
    label: String(value),
  }),
)

export const SEVERITY_LEVEL_OPTIONS: OptionItem[] = ['A', 'B', 'C', 'D', 'E'].map((value) => ({
  value,
  label: value,
}))

/**
 * 安全风险矩阵（S 纵轴 A–E，L 横轴 1–5），与后端 risk_grading.py 一致。
 * R 取交叉格，不是 L×S。
 */
export const SAFETY_RISK_MATRIX: Record<string, readonly number[]> = {
  A: [3, 5, 7, 10, 15],
  B: [5, 7, 10, 15, 23],
  C: [7, 11, 16, 23, 35],
  D: [17, 25, 37, 55, 81],
  E: [22, 32, 46, 68, 100],
}

/** 仅用于表单即时预览；最终 R 以后端查表结果为准。 */
export function lookupRiskEvaluation(likelihood: number, severity: string): number | null {
  const row = SAFETY_RISK_MATRIX[severity]
  if (!row || !Number.isInteger(likelihood) || likelihood < 1 || likelihood > 5) return null
  return row[likelihood - 1] ?? null
}
