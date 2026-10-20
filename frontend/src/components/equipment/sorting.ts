import {
  DEFAULT_EQUIPMENT_SORT_BY,
  DEFAULT_EQUIPMENT_SORT_ORDER,
  type EquipmentSortBy,
  type EquipmentSortOrder,
} from '@/lib/api/equipment-query'

/**
 * 后端排序白名单 → 表头列 key。
 * Record<EquipmentSortBy, ...> 使该映射与契约双向对齐：白名单增删字段时这里会编译报错，
 * 而不是运行到某个列「点了排序但结果不对」。
 */
export const SORT_BY_LABEL: Record<EquipmentSortBy, string> = {
  asset_no: '资产编号',
  name: '设备名称',
  commissioning_date: '投用日期',
  current_cost: '当前成本',
  book_value: '账面净值',
  department_name: '归属部门',
  status: '设备状态',
  created_at: '创建时间',
}

/** 归属部门列的 key 是 department，与契约字段名不同，故需要这层映射 */
const SORT_BY_COLUMN_KEY: Record<EquipmentSortBy, string> = {
  asset_no: 'asset_no',
  name: 'name',
  commissioning_date: 'commissioning_date',
  current_cost: 'current_cost',
  book_value: 'book_value',
  department_name: 'department',
  status: 'status',
  created_at: 'created_at',
}

const COLUMN_KEY_TO_SORT_BY: Record<string, EquipmentSortBy> = {}
for (const sortBy of Object.keys(SORT_BY_COLUMN_KEY) as EquipmentSortBy[]) {
  COLUMN_KEY_TO_SORT_BY[SORT_BY_COLUMN_KEY[sortBy]] = sortBy
}

/** 仅白名单内的列返回 sort_by，其余列返回 undefined → 不渲染排序 affordance */
export function sortableColumnKey(key: string): EquipmentSortBy | undefined {
  return COLUMN_KEY_TO_SORT_BY[key]
}

export function isDefaultSort(sortBy: EquipmentSortBy, sortOrder: EquipmentSortOrder): boolean {
  return sortBy === DEFAULT_EQUIPMENT_SORT_BY && sortOrder === DEFAULT_EQUIPMENT_SORT_ORDER
}

export function formatSortLabel(sortBy: EquipmentSortBy, sortOrder: EquipmentSortOrder): string {
  return `${SORT_BY_LABEL[sortBy]} ${sortOrder === 'asc' ? '↑' : '↓'}`
}
