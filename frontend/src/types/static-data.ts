/**
 * 业务静态数据模块 TypeScript 类型定义
 * 包含：3张基础字典 + 5张实验室台账 + 4张质量标准（共12张表，10个子模块）
 */

// ============ 通用枚举 ============

/** 状态：0启用 1停用 */
export type Status0Or1 = 0 | 1

/** 设备状态：0在用 1维修 2封存 3报废 */
export type EqStatus = 0 | 1 | 2 | 3

/** 质量标准状态：0草稿 1待审核 2已生效 3已作废 */
export type StandardStatus = 0 | 1 | 2 | 3

/** 限度类型 */
export type LimitType = '上限' | '下限' | '区间' | '不得检出'

/** 是否放行必检项 */
export type YesNo = 0 | 1

// ============ 通用响应结构 ============

export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
  meta?: {
    page?: number
    page_size?: number
    total?: number
    [key: string]: any
  }
}

export interface PageParams {
  page?: number
  page_size?: number
  [key: string]: any
}

// ============ 一、通用字典表 ============

// 1. 贮存条件字典
export interface StorageCondition {
  id: number
  cond_code: string
  cond_name: string
  temp_min: number | null
  temp_max: number | null
  humidity: string | null
  remark: string | null
  status: Status0Or1
  create_by: number
  create_time: string
  update_by: number | null
  update_time: string | null
  del_flag: number
}

export interface StorageConditionCreate {
  cond_code: string
  cond_name: string
  temp_min?: number | null
  temp_max?: number | null
  humidity?: string | null
  remark?: string | null
  status?: Status0Or1
  create_by: number
}

export interface StorageConditionUpdate {
  cond_name?: string
  temp_min?: number | null
  temp_max?: number | null
  humidity?: string | null
  remark?: string | null
  status?: Status0Or1
}

// 2. 计量单位字典
export interface Unit {
  id: number
  unit_code: string
  unit_name: string
  unit_type: UnitType
  base_value: number | null
  remark: string | null
  status: Status0Or1
  create_by: number
  create_time: string
  update_by: number | null
  update_time: string | null
  del_flag: number
}

export type UnitType = '质量' | '体积' | '浓度' | '微生物' | '比率'

export interface UnitCreate {
  unit_code: string
  unit_name: string
  unit_type: UnitType
  base_value?: number | null
  remark?: string | null
  status?: Status0Or1
  create_by: number
}

export interface UnitUpdate {
  unit_name?: string
  unit_type?: UnitType
  base_value?: number | null
  remark?: string | null
  status?: Status0Or1
}

// 3. 检验项目字典
export interface TestItem {
  id: number
  item_code: string
  item_name: string
  item_category: TestItemCategory
  unit_code: string
  method_desc: string | null
  sort_num: number | null
  status: Status0Or1
  create_by: number
  create_time: string
  update_by: number | null
  update_time: string | null
  del_flag: number
}

export type TestItemCategory = '理化' | '仪器分析' | '微生物'

export interface TestItemCreate {
  item_code: string
  item_name: string
  item_category: TestItemCategory
  unit_code: string
  method_desc?: string | null
  sort_num?: number | null
  status?: Status0Or1
  create_by: number
}

export interface TestItemUpdate {
  item_name?: string
  item_category?: TestItemCategory
  unit_code?: string
  method_desc?: string | null
  sort_num?: number | null
  status?: Status0Or1
}

// ============ 二、实验室资源台账 ============

// 4. 检测设备台账
export interface Equipment {
  id: number
  eq_code: string
  eq_name: string
  model: string
  serial_no: string
  manufacturer: string
  lab_id: number
  location: string
  eq_category: EquipmentCategory
  cal_cycle: number
  last_cal_date: string
  next_cal_date: string
  verify_status: VerifyStatus
  eq_status: EqStatus
  manager_id: number
  attach_file: string | null
  remark: string | null
  create_by: number
  create_time: string
  update_by: number | null
  update_time: string | null
  del_flag: number
}

export type EquipmentCategory = '色谱类' | '称量类' | '灭菌类' | '微生物类'
export type VerifyStatus = '已完成' | '待验证' | '过期'

export interface EquipmentCreate {
  eq_code: string
  eq_name: string
  model: string
  serial_no: string
  manufacturer: string
  lab_id: number
  location: string
  eq_category: EquipmentCategory
  cal_cycle: number
  last_cal_date: string
  next_cal_date: string
  verify_status: VerifyStatus
  eq_status?: EqStatus
  manager_id: number
  attach_file?: string | null
  remark?: string | null
  create_by: number
}

export interface EquipmentUpdate {
  eq_name?: string
  model?: string
  serial_no?: string
  manufacturer?: string
  lab_id?: number
  location?: string
  eq_category?: EquipmentCategory
  cal_cycle?: number
  last_cal_date?: string
  next_cal_date?: string
  verify_status?: VerifyStatus
  eq_status?: EqStatus
  manager_id?: number
  attach_file?: string | null
  remark?: string | null
}

// 5. 色谱柱管理
export interface ChromColumn {
  id: number
  col_code: string
  col_type: string
  spec: string
  manufacturer: string
  serial_no: string
  purchase_date: string
  use_start_date: string | null
  max_use_times: number
  used_times: number
  storage_cond_code: string
  location: string
  col_status: ChromColumnStatus
  column_category: ChromColumnCategory
  apply_method: string | null
  attach_file: string | null
  remark: string | null
  create_by: number
  create_time: string
  update_by: number | null
  update_time: string | null
  del_flag: number
}

export type ChromColumnStatus = 0 | 1 | 2 | 3  // 0在用 1待清洗 2封存 3报废
export type ChromColumnCategory = 0 | 1  // 0液相 1气相

export const CHROM_COLUMN_CATEGORY_OPTIONS = [
  { value: 0, label: '液相色谱柱' },
  { value: 1, label: '气相色谱柱' },
]

export interface ChromColumnCreate {
  col_code: string
  col_type: string
  spec: string
  manufacturer: string
  serial_no: string
  purchase_date: string
  use_start_date?: string | null
  max_use_times: number
  used_times?: number
  storage_cond_code: string
  location: string
  col_status?: ChromColumnStatus
  column_category?: ChromColumnCategory
  apply_method?: string | null
  attach_file?: string | null
  remark?: string | null
  create_by: number
}

export interface ChromColumnUpdate {
  col_type?: string
  spec?: string
  manufacturer?: string
  serial_no?: string
  purchase_date?: string
  use_start_date?: string | null
  max_use_times?: number
  storage_cond_code?: string
  location?: string
  col_status?: ChromColumnStatus
  column_category?: ChromColumnCategory
  apply_method?: string | null
  attach_file?: string | null
  remark?: string | null
}

// 6. 培养基管理
export interface Medium {
  id: number
  medium_code: string
  medium_name: string
  medium_type: string
  manufacturer: string
  batch_no: string
  spec: string
  storage_cond_code: string
  expire_date: string
  verify_status: string
  config_method: string | null
  stock_num: number
  unit_code: string
  min_stock: number
  status: Status0Or1
  attach_file: string | null
  remark: string | null
  create_by: number
  create_time: string
  update_by: number | null
  update_time: string | null
  del_flag: number
}

export interface MediumCreate {
  medium_code: string
  medium_name: string
  medium_type: string
  manufacturer: string
  batch_no: string
  spec: string
  storage_cond_code: string
  expire_date: string
  verify_status: string
  config_method?: string | null
  stock_num: number
  unit_code: string
  min_stock: number
  status?: Status0Or1
  attach_file?: string | null
  remark?: string | null
  create_by: number
}

export interface MediumUpdate {
  medium_name?: string
  medium_type?: string
  manufacturer?: string
  batch_no?: string
  spec?: string
  storage_cond_code?: string
  expire_date?: string
  verify_status?: string
  config_method?: string | null
  stock_num?: number
  unit_code?: string
  min_stock?: number
  status?: Status0Or1
  attach_file?: string | null
  remark?: string | null
}

export const MEDIUM_TYPE_OPTIONS = [
  { label: '干粉培养基', value: '干粉培养基' },
  { label: '颗粒培养基', value: '颗粒培养基' },
  { label: '液体培养基', value: '液体培养基' },
  { label: '显色培养基', value: '显色培养基' },
  { label: '环境监测培养基', value: '环境监测培养基' },
]

export const MEDIUM_VERIFY_STATUS_OPTIONS = [
  { label: '待验证', value: '待验证' },
  { label: '已验证', value: '已验证' },
  { label: '验证失败', value: '验证失败' },
]

// 7. 标准品管理
export interface Standard {
  id: number
  std_code: string
  std_name: string
  std_type: string  // national/working/international
  cas_no: string | null
  manufacturer: string | null
  batch_no: string
  spec: string | null
  purity: number | null
  content: number | null
  quantity: number
  unit_code: string
  min_stock: number
  produce_date: string | null
  expire_date: string | null
  storage_cond_code: string
  location: string | null
  test_item: string | null
  std_status: StandardStatus
  attach_file: string | null
  remark: string | null
  create_by: number
  create_time: string
  update_by: number | null
  update_time: string | null
}

export const STANDARD_STATUS_OPTIONS = [
  { value: 0, label: '在用', color: '#10b981' },
  { value: 1, label: '用完', color: '#6b7280' },
  { value: 2, label: '过期', color: '#ef4444' },
  { value: 3, label: '停用', color: '#f59e0b' },
]

export const STANDARD_TYPE_OPTIONS = [
  { label: '国家标准品', value: 'national' },
  { label: '工作标准品', value: 'working' },
  { label: '国际标准品', value: 'international' },
]

export interface StandardCreate {
  std_code: string
  std_name: string
  std_type: string
  cas_no?: string
  manufacturer?: string
  batch_no: string
  spec?: string
  purity?: number
  content?: number
  quantity?: number
  unit_code: string
  min_stock?: number
  produce_date?: string | null
  expire_date?: string | null
  storage_cond_code: string
  location?: string
  test_item?: string
  std_status?: StandardStatus
  remark?: string | null
  create_by: number
}

export interface StandardUpdate {
  std_name?: string
  std_type?: string
  cas_no?: string
  manufacturer?: string
  batch_no?: string
  spec?: string
  purity?: number
  content?: number
  quantity?: number
  unit_code?: string
  min_stock?: number
  produce_date?: string | null
  expire_date?: string | null
  storage_cond_code?: string
  location?: string
  test_item?: string
  std_status?: StandardStatus
  remark?: string | null
}

// 8. 试剂管理
export interface Reagent {
  id: number
  reagent_code: string
  reagent_name: string
  cas_no: string
  purity: string
  manufacturer: string
  batch_no: string
  spec: string
  danger_type: string
  storage_cond_code: string
  expire_date: string
  stock_num: number
  unit_code: string
  min_stock: number
  store_location: string
  attach_file: string | null
  status: Status0Or1
  remark: string | null
  create_by: number
  create_time: string
  update_by: number | null
  update_time: string | null
  del_flag: number
}

export interface ReagentCreate {
  reagent_code: string
  reagent_name: string
  cas_no: string
  purity: string
  manufacturer: string
  batch_no: string
  spec: string
  danger_type: string
  storage_cond_code: string
  expire_date: string
  stock_num: number
  unit_code: string
  min_stock: number
  store_location: string
  attach_file?: string | null
  status?: Status0Or1
  remark?: string | null
  create_by: number
}

export interface ReagentUpdate {
  reagent_name?: string
  cas_no?: string
  purity?: string
  manufacturer?: string
  batch_no?: string
  spec?: string
  danger_type?: string
  storage_cond_code?: string
  expire_date?: string
  stock_num?: number
  unit_code?: string
  min_stock?: number
  store_location?: string
  attach_file?: string | null
  status?: Status0Or1
  remark?: string | null
}

// 8. 标准物质管理
export interface StandardMaterial {
  id: number
  std_code: string
  std_name: string
  cas_no: string | null
  manufacturer: string
  batch_no: string
  cert_no: string
  purity: number
  init_stock: number
  remain_stock: number
  unit_code: string
  storage_cond_code: string
  expire_date: string
  store_location: string
  std_type: StdType
  recal_cycle: number | null
  min_stock: number
  attach_file: string | null
  status: StandardMaterialStatus
  remark: string | null
  create_by: number
  create_time: string
  update_by: number | null
  update_time: string | null
  del_flag: number
}

export type StdType = '法定' | '工作' | '自制'
export type StandardMaterialStatus = 0 | 1 | 2  // 0在用 1封存 2报废

export interface StandardMaterialCreate {
  std_code: string
  std_name: string
  cas_no?: string | null
  manufacturer: string
  batch_no: string
  cert_no: string
  purity: number
  init_stock: number
  remain_stock: number
  unit_code: string
  storage_cond_code: string
  expire_date: string
  store_location: string
  std_type: StdType
  recal_cycle?: number | null
  min_stock: number
  attach_file?: string | null
  status?: StandardMaterialStatus
  remark?: string | null
  create_by: number
}

export interface StandardMaterialUpdate {
  std_name?: string
  cas_no?: string | null
  manufacturer?: string
  batch_no?: string
  cert_no?: string
  purity?: number
  remain_stock?: number
  unit_code?: string
  storage_cond_code?: string
  expire_date?: string
  store_location?: string
  std_type?: StdType
  recal_cycle?: number | null
  min_stock?: number
  attach_file?: string | null
  status?: StandardMaterialStatus
  remark?: string | null
}

// ============ 三、质量标准 ============

// 9. 物料质量标准
export interface MaterialStandard {
  id: number
  material_code: string
  material_name: string
  material_type: MaterialType
  spec: string
  supplier_id: number | null
  standard_source: StandardSource
  standard_no: string
  version: string
  storage_cond_code: string
  status: StandardStatus
  draft_user: number
  audit_user: number | null
  approve_user: number | null
  effect_date: string | null
  invalid_date: string | null
  attach_file: string | null
  remark: string | null
  create_by: number
  create_time: string
  update_by: number | null
  update_time: string | null
  del_flag: number
  items?: MaterialStandardItem[]
}

export type MaterialType = '原料' | '辅料' | '包材' | '中间体'
export type StandardSource = '中国药典' | 'USP' | '内控'

export interface MaterialStandardCreate {
  material_code: string
  material_name: string
  material_type: MaterialType
  spec: string
  supplier_id?: number | null
  standard_source: StandardSource
  standard_no: string
  version: string
  storage_cond_code: string
  status?: StandardStatus
  draft_user: number
  audit_user?: number | null
  approve_user?: number | null
  effect_date?: string | null
  invalid_date?: string | null
  attach_file?: string | null
  remark?: string | null
  items?: MaterialStandardItemCreate[]
}

export interface MaterialStandardUpdate {
  material_name?: string
  material_type?: MaterialType
  spec?: string
  supplier_id?: number | null
  standard_source?: StandardSource
  standard_no?: string
  version?: string
  storage_cond_code?: string
  status?: StandardStatus
  effect_date?: string | null
  invalid_date?: string | null
  attach_file?: string | null
  remark?: string | null
}

// 9a. 物料质量标准-检验项目明细
export interface MaterialStandardItem {
  id: number
  standard_id: number
  item_code: string
  test_method: string | null
  limit_type: LimitType
  limit_min: number | null
  limit_max: number | null
  is_release_item: YesNo
  sort_num: number | null
  create_by: number
  create_time: string
  del_flag: number
}

export interface MaterialStandardItemCreate {
  item_code: string
  test_method?: string | null
  limit_type: LimitType
  limit_min?: number | null
  limit_max?: number | null
  is_release_item?: YesNo
  sort_num?: number | null
}

// 10. 产品质量标准
export interface ProductStandard {
  id: number
  product_code: string
  product_name: string
  trade_name: string | null
  spec: string
  dosage_form: string
  reg_standard_no: string
  inner_standard_no: string
  version: string
  storage_cond_code: string
  valid_period: number
  pack_spec: string
  status: StandardStatus
  draft_user: number
  audit_user: number | null
  approve_user: number | null
  effect_date: string | null
  invalid_date: string | null
  attach_file: string | null
  remark: string | null
  create_by: number
  create_time: string
  update_by: number | null
  update_time: string | null
  del_flag: number
  items?: ProductStandardItem[]
}

export interface ProductStandardCreate {
  product_code: string
  product_name: string
  trade_name?: string | null
  spec: string
  dosage_form: string
  reg_standard_no: string
  inner_standard_no: string
  version: string
  storage_cond_code: string
  valid_period: number
  pack_spec: string
  status?: StandardStatus
  draft_user: number
  audit_user?: number | null
  approve_user?: number | null
  effect_date?: string | null
  invalid_date?: string | null
  attach_file?: string | null
  remark?: string | null
  items?: ProductStandardItemCreate[]
}

export interface ProductStandardUpdate {
  product_name?: string
  trade_name?: string | null
  spec?: string
  dosage_form?: string
  reg_standard_no?: string
  inner_standard_no?: string
  version?: string
  storage_cond_code?: string
  valid_period?: number
  pack_spec?: string
  status?: StandardStatus
  effect_date?: string | null
  invalid_date?: string | null
  attach_file?: string | null
  remark?: string | null
}

// 10a. 产品质量标准-检验项目明细
export interface ProductStandardItem {
  id: number
  standard_id: number
  item_code: string
  test_method: string | null
  legal_limit_min: number | null
  legal_limit_max: number | null
  inner_limit_min: number | null
  inner_limit_max: number | null
  is_release_item: YesNo
  sort_num: number | null
  create_by: number
  create_time: string
  del_flag: number
}

export interface ProductStandardItemCreate {
  item_code: string
  test_method?: string | null
  legal_limit_min?: number | null
  legal_limit_max?: number | null
  inner_limit_min?: number | null
  inner_limit_max?: number | null
  is_release_item?: YesNo
  sort_num?: number | null
}

// ============ 预警相关类型 ============

export interface WarningItem {
  type: string
  subtype: string
  title: string
  message: string
  severity: 'critical' | 'warning' | 'info'
  record_id: number
  record_code: string
  record_name: string
  field: string
  current_value: string
  threshold: string
  days_remaining?: number
}

export interface WarningsResponse {
  equipment_cal: WarningItem[]
  medium_expire: WarningItem[]
  reagent_expire: WarningItem[]
  std_mat_expire: WarningItem[]
  std_mat_low_stock: WarningItem[]
  chrom_column_usage: WarningItem[]
  total: number
}

// ============ 下拉选项类型 ============

export interface DictOption {
  label: string
  value: string
}

// ============ 字典选项常量 ============

export const EQ_STATUS_OPTIONS = [
  { label: '在用', value: 0 },
  { label: '维修', value: 1 },
  { label: '封存', value: 2 },
  { label: '报废', value: 3 },
]

export const CHROM_COLUMN_STATUS_OPTIONS = [
  { label: '在用', value: 0 },
  { label: '待清洗', value: 1 },
  { label: '封存', value: 2 },
  { label: '报废', value: 3 },
]

export const YES_NO_OPTIONS = [
  { label: '否', value: 0 },
  { label: '是', value: 1 },
]

export const MATERIAL_TYPE_OPTIONS = [
  { label: '原料', value: '原料' },
  { label: '辅料', value: '辅料' },
  { label: '包材', value: '包材' },
  { label: '中间体', value: '中间体' },
]

export const STANDARD_SOURCE_OPTIONS = [
  { label: '中国药典', value: '中国药典' },
  { label: 'USP', value: 'USP' },
  { label: '内控', value: '内控' },
]

export const LIMIT_TYPE_OPTIONS = [
  { label: '上限', value: '上限' },
  { label: '下限', value: '下限' },
  { label: '区间', value: '区间' },
  { label: '不得检出', value: '不得检出' },
]

export const VERIFY_STATUS_OPTIONS = [
  { label: '已完成', value: '已完成' },
  { label: '待验证', value: '待验证' },
  { label: '过期', value: '过期' },
]

export const STD_TYPE_OPTIONS = [
  { label: '法定', value: '法定' },
  { label: '工作', value: '工作' },
  { label: '自制', value: '自制' },
]

// ============ 审计日志类型 ============

export interface AuditLogItem {
  id: number
  module_type: string
  record_id: number
  record_code: string | null
  operate_type: string
  operate_by: number
  operate_by_name?: string
  operate_time: string
  old_value: string | null
  new_value: string | null
  change_summary: string | null
}

// ============ 11. 液相色谱对照品 ==========

export interface HplcReference {
  id: number
  ref_code: string
  ref_name: string
  project_name: string | null
  internal_batch: string | null
  cas_no: string | null
  cat_no: string | null
  manufacturer_batch: string | null
  manufacturer: string | null
  spec: string | null
  spec_unit: string | null
  purity: number | null
  content: number | null
  quantity: number | null
  total_amount: number | null
  remaining_amount: number | null
  remaining_unit: string | null
  recal_threshold: number | null
  need_recal: boolean
  stock_status: string | null
  arrival_date: string | null
  produce_date: string | null
  expire_date: string | null
  recal_cycle_days: number | null
  open_date: string | null
  open_expire_days: number | null
  storage_cond_code: string | null
  location: string | null
  has_coa: boolean
  handover_no: string | null
  ref_status: number
  remark: string | null
  attach_file: string | null
  create_by: number
  create_time: string
  update_by: number | null
  update_time: string | null
  del_flag: number
}

export interface HplcReferenceCreate {
  ref_code: string
  ref_name: string
  project_name?: string | null
  internal_batch?: string | null
  cas_no?: string | null
  cat_no?: string | null
  manufacturer_batch?: string | null
  manufacturer?: string | null
  spec?: string | null
  spec_unit?: string | null
  purity?: number | null
  content?: number | null
  quantity?: number | null
  total_amount?: number | null
  remaining_amount?: number | null
  remaining_unit?: string | null
  recal_threshold?: number | null
  need_recal?: boolean
  stock_status?: string | null
  arrival_date?: string | null
  produce_date?: string | null
  expire_date?: string | null
  recal_cycle_days?: number | null
  open_date?: string | null
  open_expire_days?: number | null
  storage_cond_code?: string | null
  location?: string | null
  has_coa?: boolean
  handover_no?: string | null
  ref_status?: number
  remark?: string | null
  attach_file?: string | null
  create_by: number
}

export interface HplcReferenceUpdate {
  ref_name?: string | null
  project_name?: string | null
  internal_batch?: string | null
  cas_no?: string | null
  cat_no?: string | null
  manufacturer_batch?: string | null
  manufacturer?: string | null
  spec?: string | null
  spec_unit?: string | null
  purity?: number | null
  content?: number | null
  quantity?: number | null
  total_amount?: number | null
  remaining_amount?: number | null
  remaining_unit?: string | null
  recal_threshold?: number | null
  need_recal?: boolean | null
  stock_status?: string | null
  arrival_date?: string | null
  produce_date?: string | null
  expire_date?: string | null
  recal_cycle_days?: number | null
  open_date?: string | null
  open_expire_days?: number | null
  storage_cond_code?: string | null
  location?: string | null
  has_coa?: boolean
  handover_no?: string | null
  ref_status?: number
  remark?: string | null
  attach_file?: string | null
}

export const HPLC_REF_STATUS_OPTIONS = [
  { label: '在用', value: 0 },
  { label: '用完', value: 1 },
  { label: '过期', value: 2 },
  { label: '报废', value: 3 },
]

// 对照品规格单位选项
export const HPLC_REF_SPEC_UNIT_OPTIONS = [
  { label: 'mg', value: 'mg' },
  { label: 'g', value: 'g' },
]

// 对照品领用记录
export interface HplcReferenceUsage {
  id: number
  ref_id: number
  ref_code: string
  ref_name: string
  usage_amount: number
  usage_unit: string
  remaining_after: number
  usage_person: string | null
  usage_purpose: string | null
  usage_date: string | null
  remark: string | null
  create_by: number
  create_time: string
  del_flag: number
}

export interface HplcReferenceUsageCreate {
  ref_id: number
  usage_amount: number
  usage_unit?: string
  usage_person?: string | null
  usage_purpose?: string | null
  usage_date?: string | null
  remark?: string | null
}

// ============ 文件上传类型 ============

export interface UploadResponse {
  file_id: string
  original_name: string
  stored_name: string
  url: string
  size: number
  content_type: string
}