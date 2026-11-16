/**
 * 风险分级管控台账的契约类型与前端展示映射。
 *
 * 选项、5×5 安全风险矩阵与分级阈值全部来自后端只读接口
 * `GET /api/v1/safety/enums/risk-grading`，前端不再手写这些常量。
 */

import type { components, operations } from '@/types/generated/schema'

export type WorkActivityHazard = components['schemas']['WorkActivityHazardResponse']
export type WorkActivityHazardCreate = components['schemas']['WorkActivityHazardCreate']
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

export type RiskGradingOptions = components['schemas']['RiskGradingOptions']
export type RiskGradingOptionsApiResponse = components['schemas']['RiskGradingOptionsApiResponse']
export type RiskGradingValueLabel = components['schemas']['RiskGradingValueLabel']
export type RiskGradeThreshold = components['schemas']['RiskGradeThreshold']
export type EquipmentGradeBand = components['schemas']['EquipmentGradeBand']
export type LecRange = components['schemas']['LecRange']

/** 设备设施评价级别标签样式：黄底是唯一使用黑字的填充（白字对比度不足）。 */
export const EQUIPMENT_GRADE_TAG_STYLES: Record<
  number,
  { backgroundColor: string; color: string; borderColor: string }
> = {
  1: { backgroundColor: '#1e88e5', color: '#ffffff', borderColor: '#1565c0' },
  2: { backgroundColor: '#ffd400', color: '#000000', borderColor: '#c9a600' },
  3: { backgroundColor: '#f57c00', color: '#ffffff', borderColor: '#c25e00' },
  4: { backgroundColor: '#e53935', color: '#ffffff', borderColor: '#b71c1c' },
}

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

/** 按后端下发的阈值推导预览级别；阈值从高到低排列。 */
export function deriveEvaluationGrade(
  d: number,
  thresholds: RiskGradeThreshold[] | undefined,
): number | null {
  if (!thresholds) return null
  const threshold = thresholds.find((item) => d > Number(item.lower_bound_exclusive))
  return threshold?.grade ?? null
}

/** 按后端下发的矩阵查 R；仅用于表单即时预览。 */
export function lookupRiskEvaluation(
  matrix: Record<string, number[]> | undefined,
  likelihood: number,
  severity: string,
): number | null {
  const row = matrix?.[severity]
  if (!row || !Number.isInteger(likelihood) || likelihood < 1 || likelihood > 5) return null
  return row[likelihood - 1] ?? null
}

/** 按后端下发的分段查设备设施评价级别；仅用于表单即时预览。 */
export function deriveEquipmentEvaluationGrade(
  r: number | null,
  bands: EquipmentGradeBand[] | undefined,
): EquipmentGradeBand | null {
  if (r === null || !bands) return null
  return bands.find((band) => r >= band.min_r) ?? null
}

export function toValueLabelOptions(values: string[]): RiskGradingValueLabel[] {
  return values.map((value) => ({ value, label: value }))
}

export function toNumberOptions(values: number[]): { value: number; label: string }[] {
  return values.map((value) => ({ value, label: String(value) }))
}
