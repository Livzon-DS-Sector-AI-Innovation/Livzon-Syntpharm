/**
 * 质量检验试剂/标准品管理类型定义
 */

/** 试剂/标准品记录 */
export interface Reagent {
  id: string
  reagent_label_urls: string[] | null
  reagent_name: string
  arrival_date: string
  production_date: string | null
  lot_no: string
  incoming_lot_no: string | null
  expiration_date: string
  specification: string | null
  category: string
  reagent_no: string | null
  content: string | null
  manufacturer: string | null
  quantity: number
  unit: string
  status: string
  created_by: string | null
  created_at: string
  updated_at: string | null
}

/** 试剂列表响应 */
export interface ReagentListResponse {
  items: Reagent[]
  total: number
  page: number
  page_size: number
}

/** 创建试剂请求 */
export interface CreateReagentRequest {
  reagent_label_urls: string[]
  reagent_name: string
  arrival_date: string
  production_date?: string
  lot_no: string
  incoming_lot_no?: string
  expiration_date: string
  specification?: string
  category: string
  reagent_no?: string
  content?: string
  manufacturer?: string
  unit: string
}

/** 更新试剂请求 */
export interface UpdateReagentRequest {
  reagent_label_urls?: string[]
  reagent_name?: string
  arrival_date?: string
  production_date?: string
  lot_no?: string
  incoming_lot_no?: string
  expiration_date?: string
  specification?: string
  category?: string
  reagent_no?: string
  content?: string
  manufacturer?: string
  unit?: string
  status?: string
}

/** AI识别响应 */
export interface AiRecognizeResponse {
  reagent_name: string | null
  lot_no: string | null
  manufacturer: string | null
  production_date: string | null
  expiration_date: string | null
  category: string | null
  content: string | null
  specification: string | null
  confidence: number
}

/** 试剂状态选项 */
export const REAGENT_STATUS_OPTIONS = [
  { value: 'available', label: '可用' },
  { value: 'used_up', label: '已用完' },
  { value: 'low_stock', label: '库存不足' },
  { value: 'expired', label: '已过期' },
  { value: 'quarantine', label: '待验' },
  { value: 'scrap', label: '已报废' },
] as const

/** 试剂分类选项（AI识别用） */
export const REAGENT_CATEGORY_OPTIONS = [
  { value: '（A溶剂）', label: '（A溶剂）' },
  { value: '（B滴定剂）', label: '（B滴定剂）' },
  { value: '/', label: '/' },
  { value: 'GC', label: 'GC' },
  { value: 'GR(优级纯)', label: 'GR(优级纯)' },
  { value: 'HPLC', label: 'HPLC' },
  { value: 'HPLC梯度级', label: 'HPLC梯度级' },
  { value: 'IND（指示剂）', label: 'IND（指示剂）' },
  { value: '单元素标准溶液', label: '单元素标准溶液' },
  { value: '分析纯AR', label: '分析纯AR' },
  { value: '分析纯II类ARII', label: '分析纯II类ARII' },
  { value: '光谱纯SP', label: '光谱纯SP' },
  { value: '化学纯CP', label: '化学纯CP' },
  { value: '缓冲液标准品', label: '缓冲液标准品' },
  { value: '基准试剂', label: '基准试剂' },
  { value: '色谱HPLC级', label: '色谱HPLC级' },
  { value: '色谱级', label: '色谱级' },
  { value: '试剂级', label: '试剂级' },
  { value: '液相色谱纯', label: '液相色谱纯' },
] as const

/** 单位选项 */
export const UNIT_OPTIONS = [
  { value: 'g', label: '克(g)' },
  { value: 'kg', label: '千克(kg)' },
  { value: 'mg', label: '毫克(mg)' },
  { value: 'mL', label: '毫升(mL)' },
  { value: 'L', label: '升(L)' },
  { value: '支', label: '支' },
  { value: '瓶', label: '瓶' },
  { value: '盒', label: '盒' },
] as const