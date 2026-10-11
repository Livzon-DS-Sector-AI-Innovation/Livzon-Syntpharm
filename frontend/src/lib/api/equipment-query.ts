import type { operations } from '@/types/generated/schema'

/** 设备列表查询参数：直接取 OpenAPI 生成契约，前端不再手写一份 */
export type EquipmentListQuery = NonNullable<
  operations['get_equipments_api_v1_equipment_equipments_get']['parameters']['query']
>

/** 排序白名单（spec D2）。前端可点列集合以此为准，两侧不各写一份清单 */
export type EquipmentSortBy = NonNullable<EquipmentListQuery['sort_by']>
export type EquipmentSortOrder = NonNullable<EquipmentListQuery['sort_order']>

/** URL 唯一持有的查询状态：排序 + 分页。筛选条件仍由 store 单一来源管理 */
export type EquipmentUrlState = Required<
  Pick<EquipmentListQuery, 'sort_by' | 'sort_order' | 'page' | 'page_size'>
>

const QUERY_KEYS = [
  'category_id',
  'location_id',
  'department_id',
  'status',
  'keyword',
  'sort_by',
  'sort_order',
  'page',
  'page_size',
] as const satisfies readonly (keyof EquipmentListQuery)[]

export const DEFAULT_EQUIPMENT_SORT_BY: EquipmentSortBy = 'asset_no'
export const DEFAULT_EQUIPMENT_SORT_ORDER: EquipmentSortOrder = 'asc'
export const DEFAULT_EQUIPMENT_PAGE = 1
export const DEFAULT_EQUIPMENT_PAGE_SIZE = 15

/**
 * URL 是不可信输入，出站前必须做运行时校验（否则 ?sort_by=x 会让列表页 422 空转）。
 * 联合类型只存在于编译期、无法 Object.keys 派生，故此处写全量清单，
 * 并用 Record<EquipmentSortBy, true> 双向约束：契约增删字段都会编译报错。
 */
const SORT_BY_VALUES: Record<EquipmentSortBy, true> = {
  asset_no: true,
  name: true,
  commissioning_date: true,
  current_cost: true,
  book_value: true,
  department_name: true,
  status: true,
  created_at: true,
}

const SORT_ORDER_VALUES: Record<EquipmentSortOrder, true> = { asc: true, desc: true }

export const EQUIPMENT_SORT_FIELDS = Object.keys(SORT_BY_VALUES) as EquipmentSortBy[]

interface ParamReader {
  get(name: string): string | string[] | null | undefined
}

function readString(reader: ParamReader, key: string): string | undefined {
  const value = reader.get(key)
  const single = Array.isArray(value) ? value[0] : value
  return single || undefined
}

function readPositiveInt(reader: ParamReader, key: string): number | undefined {
  const raw = readString(reader, key)
  if (!raw) return undefined
  const parsed = Number(raw)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined
}

/** 请求参数 → query string。SSR 与客户端共用，避免首屏与二次请求参数分叉 */
export function buildEquipmentQuery(query: EquipmentListQuery): URLSearchParams {
  const params = new URLSearchParams()
  for (const key of QUERY_KEYS) {
    const value = query[key]
    if (value === undefined || value === null || value === '') continue
    params.append(key, String(value))
  }
  return params
}

/**
 * 解析结果：state 是可直接发往后端的干净参数；rejectedSort 是被丢弃的原始值。
 * D12 要求未知排序字段不得静默兜底——前端不发脏参数（否则列表 422 空转），
 * 但必须把丢弃情况交给界面提示，不能让用户以为按某个字段排了序。
 */
export interface EquipmentUrlParse {
  state: EquipmentUrlState
  rejectedSort: string[]
}

function parseEquipmentUrlState(reader: ParamReader): EquipmentUrlParse {
  const sortBy = readString(reader, 'sort_by')
  const sortOrder = readString(reader, 'sort_order')
  const rejectedSort: string[] = []
  if (sortBy && !(sortBy in SORT_BY_VALUES)) rejectedSort.push(`sort_by=${sortBy}`)
  if (sortOrder && !(sortOrder in SORT_ORDER_VALUES)) rejectedSort.push(`sort_order=${sortOrder}`)
  return {
    state: {
      sort_by: sortBy && sortBy in SORT_BY_VALUES ? (sortBy as EquipmentSortBy) : DEFAULT_EQUIPMENT_SORT_BY,
      sort_order:
        sortOrder && sortOrder in SORT_ORDER_VALUES ? (sortOrder as EquipmentSortOrder) : DEFAULT_EQUIPMENT_SORT_ORDER,
      page: readPositiveInt(reader, 'page') ?? DEFAULT_EQUIPMENT_PAGE,
      page_size: readPositiveInt(reader, 'page_size') ?? DEFAULT_EQUIPMENT_PAGE_SIZE,
    },
    rejectedSort,
  }
}

/** 浏览器侧 URL → 查询状态（useSearchParams 返回值即可传入） */
export function parseEquipmentUrlParams(reader: ParamReader): EquipmentUrlParse {
  return parseEquipmentUrlState(reader)
}

/** Server Component 拿到的是普通对象而非 URLSearchParams，走同一套解析 */
export function parseEquipmentUrlRecord(
  record: Record<string, string | string[] | undefined>,
): EquipmentUrlParse {
  return parseEquipmentUrlState({ get: (name) => record[name] })
}

/** 查询状态写回 URL：保留其它未知参数，默认值不落进地址栏，保持链接短且可分享 */
export function writeEquipmentUrlQuery(current: URLSearchParams, state: EquipmentUrlState): string {
  const next = new URLSearchParams(current)
  const entries: Array<[string, string | null]> = [
    ['sort_by', state.sort_by === DEFAULT_EQUIPMENT_SORT_BY ? null : state.sort_by],
    ['sort_order', state.sort_order === DEFAULT_EQUIPMENT_SORT_ORDER ? null : state.sort_order],
    ['page', state.page === DEFAULT_EQUIPMENT_PAGE ? null : String(state.page)],
    ['page_size', state.page_size === DEFAULT_EQUIPMENT_PAGE_SIZE ? null : String(state.page_size)],
  ]
  for (const [key, value] of entries) {
    if (value === null) next.delete(key)
    else next.set(key, value)
  }
  return next.toString()
}
