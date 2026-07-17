// ========== 取样管理类型定义 ==========

// 取样来源
export enum SamplingSource {
  PURCHASED_MATERIAL = "purchased_material",  // 外购原料
  WORKSHOP_INTERMEDIATE = "workshop_intermediate",  // 车间中间体
  FINISHED_PRODUCT = "finished_product",  // 成品
}

export const SamplingSourceLabels: Record<SamplingSource, string> = {
  [SamplingSource.PURCHASED_MATERIAL]: "外购原料",
  [SamplingSource.WORKSHOP_INTERMEDIATE]: "车间中间体",
  [SamplingSource.FINISHED_PRODUCT]: "成品",
};

// 来源类型
export enum SourceType {
  PURCHASE_INBOUND = "purchase_inbound",  // 来料入库单
  BATCH_NO = "batch_no",  // 生产批号
}

export const SourceTypeLabels: Record<SourceType, string> = {
  [SourceType.PURCHASE_INBOUND]: "来料入库单",
  [SourceType.BATCH_NO]: "生产批号",
};

// 取样单状态
export enum SamplingStatus {
  DRAFT = "draft",  // 草稿
  PENDING_WAREHOUSE = "pending_warehouse",  // 待仓储/生产审核
  PENDING_QA = "pending_qa",  // 待QA审核
  APPROVED = "approved",  // 已批准
  EFFECTIVE = "effective",  // 已生效
  REJECTED = "rejected",  // 驳回
}

export const SamplingStatusLabels: Record<SamplingStatus, string> = {
  [SamplingStatus.DRAFT]: "草稿",
  [SamplingStatus.PENDING_WAREHOUSE]: "待仓储/生产审核",
  [SamplingStatus.PENDING_QA]: "待QA审核",
  [SamplingStatus.APPROVED]: "已批准",
  [SamplingStatus.EFFECTIVE]: "已生效",
  [SamplingStatus.REJECTED]: "驳回",
};

export const SamplingStatusColors: Record<SamplingStatus, string> = {
  [SamplingStatus.DRAFT]: "default",
  [SamplingStatus.PENDING_WAREHOUSE]: "processing",
  [SamplingStatus.PENDING_QA]: "processing",
  [SamplingStatus.APPROVED]: "success",
  [SamplingStatus.EFFECTIVE]: "success",
  [SamplingStatus.REJECTED]: "error",
};

// 取样判定
export enum SamplingResult {
  NORMAL = "normal",  // 正常取样
  ABNORMAL = "abnormal",  // 取样异常
}

export const SamplingResultLabels: Record<SamplingResult, string> = {
  [SamplingResult.NORMAL]: "正常取样",
  [SamplingResult.ABNORMAL]: "取样异常",
};

// 样品状态
export enum SampleStatus {
  PENDING = "pending",  // 待留样
  RETAINED = "retained",  // 已留样
  USED = "used",  // 已使用
  EXPIRED = "expired",  // 已到期
}

export const SampleStatusLabels: Record<SampleStatus, string> = {
  [SampleStatus.PENDING]: "待留样",
  [SampleStatus.RETAINED]: "已留样",
  [SampleStatus.USED]: "已使用",
  [SampleStatus.EXPIRED]: "已到期",
};

// 留样状态
export enum RetentionStatus {
  RETAINED = "retained",  // 已留样
  EXPIRED = "expired",  // 已到期
  DISPOSED = "disposed",  // 已处置
}

export const RetentionStatusLabels: Record<RetentionStatus, string> = {
  [RetentionStatus.RETAINED]: "已留样",
  [RetentionStatus.EXPIRED]: "已到期",
  [RetentionStatus.DISPOSED]: "已处置",
};

export const RetentionStatusColors: Record<RetentionStatus, string> = {
  [RetentionStatus.RETAINED]: "processing",
  [RetentionStatus.EXPIRED]: "warning",
  [RetentionStatus.DISPOSED]: "default",
};

// 异常原因选项
export const ExceptionReasonOptions = [
  { value: "package_damaged", label: "包装破损" },
  { value: "moisture_damage", label: "受潮" },
  { value: "appearance_unqualified", label: "外观不合格" },
  { value: "other", label: "其他异常" },
];

// ========== 接口类型 ==========

// 取样明细
export interface SamplingOrderItem {
  id: string;
  sampling_order_id: string;
  item_no: number;
  sample_no: string;
  sampling_count?: number;
  retention_count?: number;
  retention_location?: string;
  sample_status?: SampleStatus;
  retention_date?: string;
  expiry_date?: string;
  is_expired: boolean;
  disposal_date?: string;
  disposal_method?: string;
  remark?: string;
  created_at: string;
  updated_at: string;
}

// 取样单
export interface SamplingOrder {
  id: string;
  order_no: string;
  source_type: SourceType;
  source_no?: string;
  material_code: string;
  material_name?: string;
  material_category?: string;
  batch_no?: string;
  specification?: string;
  unit?: string;
  quantity?: number;
  sampling_source: SamplingSource;
  sampling_quantity?: number;
  sampling_location?: string;
  sampling_date?: string;
  sampler_id?: string;
  sampler_name?: string;
  status: SamplingStatus;
  sampling_result?: SamplingResult;
  exception_reasons?: string;
  deviation_id?: string;
  remark?: string;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
  items: SamplingOrderItem[];
}

// 取样单列表项
export interface SamplingOrderListItem {
  id: string;
  order_no: string;
  source_type: SourceType;
  source_no?: string;
  material_code: string;
  material_name?: string;
  material_category?: string;
  batch_no?: string;
  sampling_source: SamplingSource;
  sampling_date?: string;
  sampler_name?: string;
  status: SamplingStatus;
  sampling_result?: SamplingResult;
  created_at: string;
}

// 取样单列表响应
export interface SamplingOrderListResponse {
  items: SamplingOrderListItem[];
  total: number;
  page: number;
  page_size: number;
}

// 创建取样单
export interface SamplingOrderCreate {
  source_type: SourceType;
  source_no?: string;
  material_code: string;
  material_name?: string;
  material_category?: string;
  batch_no?: string;
  specification?: string;
  unit?: string;
  quantity?: number;
  sampling_source: SamplingSource;
  sampling_quantity?: number;
  sampling_location?: string;
  sampling_date?: string;
  sampler_id?: string;
  sampler_name?: string;
  sampling_result?: SamplingResult;
  exception_reasons?: string;
  remark?: string;
  items: SamplingOrderItemCreate[];
}

// 取样明细创建
export interface SamplingOrderItemCreate {
  item_no: number;
  sample_no?: string;
  sampling_count?: number;
  retention_count?: number;
  retention_location?: string;
  sample_status?: SampleStatus;
  retention_date?: string;
  expiry_date?: string;
  remark?: string;
}

// 更新取样单
export interface SamplingOrderUpdate {
  source_type?: SourceType;
  source_no?: string;
  material_code?: string;
  material_name?: string;
  material_category?: string;
  batch_no?: string;
  specification?: string;
  unit?: string;
  quantity?: number;
  sampling_source?: SamplingSource;
  sampling_quantity?: number;
  sampling_location?: string;
  sampling_date?: string;
  sampler_id?: string;
  sampler_name?: string;
  sampling_result?: SamplingResult;
  exception_reasons?: string;
  remark?: string;
  items?: SamplingOrderItemCreate[];
}

// 审批记录
export interface SamplingApprovalRecord {
  id: string;
  sampling_order_id: string;
  approval_level: number;
  approval_status: string;
  approver_role?: string;
  approver_id?: string;
  approver_name?: string;
  approved_at?: string;
  comments?: string;
  created_at: string;
}

// 审批操作
export interface SamplingApprovalCreate {
  approval_status: "approved" | "rejected";
  comments?: string;
}

// 留样台账
export interface SampleRetentionLedger {
  id: string;
  sampling_item_id: string;
  sampling_order_id: string;
  order_no: string;
  sample_no: string;
  material_code: string;
  material_name?: string;
  batch_no?: string;
  retention_count?: number;
  retention_location?: string;
  retention_date?: string;
  expiry_date?: string;
  retention_status: RetentionStatus;
  disposal_date?: string;
  disposal_method?: string;
  disposal_remark?: string;
  remark?: string;
  created_at: string;
}

// 留样台账列表响应
export interface RetentionLedgerListResponse {
  items: SampleRetentionLedger[];
  total: number;
  page: number;
  page_size: number;
}

// 筛选条件
export interface SamplingOrderFilter {
  material_code?: string;
  material_name?: string;
  sampling_source?: SamplingSource;
  status?: SamplingStatus;
  sampling_result?: SamplingResult;
  order_no?: string;
  start_date?: string;
  end_date?: string;
}

// 留样台账筛选
export interface RetentionLedgerFilter {
  material_code?: string;
  material_name?: string;
  retention_status?: RetentionStatus;
  order_no?: string;
  sample_no?: string;
}
