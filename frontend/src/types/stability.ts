// ========== 稳定性试验管理类型定义 ==========

// 试验类型
export enum StabilityStudyType {
  LONG_TERM = "long_term",  // 长期试验
  ACCELERATED = "accelerated",  // 加速试验
  INTERMEDIATE = "intermediate",  // 中间条件试验
}

export const StabilityStudyTypeLabels: Record<StabilityStudyType, string> = {
  [StabilityStudyType.LONG_TERM]: "长期试验",
  [StabilityStudyType.ACCELERATED]: "加速试验",
  [StabilityStudyType.INTERMEDIATE]: "中间条件试验",
};

// 试验方案状态
export enum StabilityStudyStatus {
  DRAFT = "draft",  // 草稿
  SUBMITTED = "submitted",  // 已提交（待开发者审核）
  DEVELOPER_APPROVED = "developer_approved",  // 开发者已审核
  QC_SUPERVISOR_APPROVED = "qc_supervisor_approved",  // QC主管已审核
  QA_APPROVED = "qa_approved",  // QA已审核
  FINAL_APPROVED = "final_approved",  // QA负责人终审
  ACTIVE = "active",  // 已批准（进行中）
  COMPLETED = "completed",  // 已完成
  CANCELLED = "cancelled",  // 已取消
  REJECTED = "rejected",  // 驳回
}

export const StabilityStudyStatusLabels: Record<StabilityStudyStatus, string> = {
  [StabilityStudyStatus.DRAFT]: "草稿",
  [StabilityStudyStatus.SUBMITTED]: "待开发者审核",
  [StabilityStudyStatus.DEVELOPER_APPROVED]: "待QC主管审核",
  [StabilityStudyStatus.QC_SUPERVISOR_APPROVED]: "待QA审核",
  [StabilityStudyStatus.QA_APPROVED]: "待QA负责人审核",
  [StabilityStudyStatus.FINAL_APPROVED]: "QA负责人审核通过",
  [StabilityStudyStatus.ACTIVE]: "进行中",
  [StabilityStudyStatus.COMPLETED]: "已完成",
  [StabilityStudyStatus.CANCELLED]: "已取消",
  [StabilityStudyStatus.REJECTED]: "驳回",
};

export const StabilityStudyStatusColors: Record<StabilityStudyStatus, string> = {
  [StabilityStudyStatus.DRAFT]: "default",
  [StabilityStudyStatus.SUBMITTED]: "processing",
  [StabilityStudyStatus.DEVELOPER_APPROVED]: "processing",
  [StabilityStudyStatus.QC_SUPERVISOR_APPROVED]: "processing",
  [StabilityStudyStatus.QA_APPROVED]: "processing",
  [StabilityStudyStatus.FINAL_APPROVED]: "success",
  [StabilityStudyStatus.ACTIVE]: "success",
  [StabilityStudyStatus.COMPLETED]: "success",
  [StabilityStudyStatus.CANCELLED]: "default",
  [StabilityStudyStatus.REJECTED]: "error",
};

// 取样节点状态
export enum SampleNodeStatus {
  PENDING = "pending",  // 待取样
  SAMPLING = "sampling",  // 取样中
  SAMPLED = "sampled",  // 已取样
  INSPECTION_PENDING = "inspection_pending",  // 待检验
  INSPECTION_DONE = "inspection_done",  // 检验完成
  OVERDUE = "overdue",  // 已逾期
}

export const SampleNodeStatusLabels: Record<SampleNodeStatus, string> = {
  [SampleNodeStatus.PENDING]: "待取样",
  [SampleNodeStatus.SAMPLING]: "取样中",
  [SampleNodeStatus.SAMPLED]: "已取样",
  [SampleNodeStatus.INSPECTION_PENDING]: "待检验",
  [SampleNodeStatus.INSPECTION_DONE]: "检验完成",
  [SampleNodeStatus.OVERDUE]: "已逾期",
};

export const SampleNodeStatusColors: Record<SampleNodeStatus, string> = {
  [SampleNodeStatus.PENDING]: "default",
  [SampleNodeStatus.SAMPLING]: "processing",
  [SampleNodeStatus.SAMPLED]: "success",
  [SampleNodeStatus.INSPECTION_PENDING]: "warning",
  [SampleNodeStatus.INSPECTION_DONE]: "success",
  [SampleNodeStatus.OVERDUE]: "error",
};

// 检验记录状态
export enum StabilityInspectionStatus {
  DRAFT = "draft",  // 草稿
  SUBMITTED = "submitted",  // 已提交
  APPROVED = "approved",  // 已审核
  REJECTED = "rejected",  // 驳回
}

export const StabilityInspectionStatusLabels: Record<StabilityInspectionStatus, string> = {
  [StabilityInspectionStatus.DRAFT]: "草稿",
  [StabilityInspectionStatus.SUBMITTED]: "已提交",
  [StabilityInspectionStatus.APPROVED]: "已审核",
  [StabilityInspectionStatus.REJECTED]: "驳回",
};

export const StabilityInspectionStatusColors: Record<StabilityInspectionStatus, string> = {
  [StabilityInspectionStatus.DRAFT]: "default",
  [StabilityInspectionStatus.SUBMITTED]: "processing",
  [StabilityInspectionStatus.APPROVED]: "success",
  [StabilityInspectionStatus.REJECTED]: "error",
};

// 检验结论
export enum StabilityInspectionConclusion {
  QUALIFIED = "qualified",  // 合格
  UNQUALIFIED = "unqualified",  // 不合格
  SUSPENDED = "suspended",  // 中止
}

export const StabilityInspectionConclusionLabels: Record<StabilityInspectionConclusion, string> = {
  [StabilityInspectionConclusion.QUALIFIED]: "合格",
  [StabilityInspectionConclusion.UNQUALIFIED]: "不合格",
  [StabilityInspectionConclusion.SUSPENDED]: "中止",
};

// 单项判定
export enum StabilityItemResult {
  PASS = "pass",  // 合格
  FAIL = "fail",  // 不合格
  NA = "na",  // 不适用
}

export const StabilityItemResultLabels: Record<StabilityItemResult, string> = {
  [StabilityItemResult.PASS]: "合格",
  [StabilityItemResult.FAIL]: "不合格",
  [StabilityItemResult.NA]: "不适用",
};

// ========== 接口类型 ==========

// 取样节点
export interface StabilitySampleNode {
  id: string;
  stability_study_id: string;
  node_no: number;
  node_month: number;
  node_name: string;
  planned_date?: string;
  actual_date?: string;
  sample_quantity?: number;
  sample_no?: string;
  status: SampleNodeStatus;
  // 关联检验
  inspection_id?: string;
  inspection_no?: string;
  inspection_status?: string;
  inspector_name?: string;
  inspection_date?: string;
  created_at: string;
  updated_at: string;
}

// 取样节点创建
export interface StabilitySampleNodeCreate {
  node_no: number;
  node_month: number;
  node_name?: string;
  planned_date?: string;
  sample_quantity?: number;
}

// 取样节点更新
export interface StabilitySampleNodeUpdate {
  node_name?: string;
  planned_date?: string;
  actual_date?: string;
  sample_quantity?: number;
  sample_no?: string;
  status?: SampleNodeStatus;
  inspection_id?: string;
  inspection_no?: string;
  inspection_status?: string;
  inspector_name?: string;
  inspection_date?: string;
}

// 检验明细
export interface StabilityInspectionItem {
  id: string;
  stability_inspection_id: string;
  item_no: number;
  inspection_item: string;
  inspection_method?: string;
  standard_value?: string;
  unit?: string;
  measured_value?: string;
  result?: StabilityItemResult;
  is_oos: boolean;
  oos_description?: string;
  data_point?: string;
  chromatogram_urls?: string;
  remark?: string;
  created_at: string;
  updated_at: string;
}

// 检验明细创建
export interface StabilityInspectionItemCreate {
  item_no: number;
  inspection_item: string;
  inspection_method?: string;
  standard_value?: string;
  unit?: string;
  measured_value?: string;
  result?: StabilityItemResult;
  is_oos?: boolean;
  oos_description?: string;
  data_point?: string;
  chromatogram_urls?: string;
  remark?: string;
}

// 检验记录
export interface StabilityInspection {
  id: string;
  study_id: string;
  study_no: string;
  sample_node_id: string;
  node_month: number;
  inspection_no: string;
  product_code: string;
  product_name?: string;
  batch_no?: string;
  specification?: string;
  inspection_date?: string;
  inspector_id?: string;
  inspector_name?: string;
  sample_quantity?: number;
  sample_no?: string;
  sample_condition?: string;
  standard_id?: string;
  standard_name?: string;
  status: StabilityInspectionStatus;
  inspection_conclusion?: StabilityInspectionConclusion;
  conclusion_reason?: string;
  remark?: string;
  oos_report_no?: string;
  attachments?: string;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
  items: StabilityInspectionItem[];
}

// 检验记录列表项
export interface StabilityInspectionListItem {
  id: string;
  study_id: string;
  study_no: string;
  inspection_no: string;
  node_month: number;
  product_code: string;
  product_name?: string;
  batch_no?: string;
  inspector_name?: string;
  inspection_date?: string;
  status: StabilityInspectionStatus;
  inspection_conclusion?: StabilityInspectionConclusion;
  created_at: string;
}

// 检验记录列表响应
export interface StabilityInspectionListResponse {
  items: StabilityInspectionListItem[];
  total: number;
  page: number;
  page_size: number;
}

// 检验记录创建
export interface StabilityInspectionCreate {
  study_id: string;
  sample_node_id: string;
  inspection_date?: string;
  inspector_id?: string;
  inspector_name?: string;
  sample_quantity?: number;
  sample_no?: string;
  sample_condition?: string;
  standard_id?: string;
  standard_name?: string;
  inspection_conclusion?: StabilityInspectionConclusion;
  conclusion_reason?: string;
  remark?: string;
  oos_report_no?: string;
  attachments?: string;
  items: StabilityInspectionItemCreate[];
}

// 检验记录更新
export interface StabilityInspectionUpdate {
  inspection_date?: string;
  inspector_id?: string;
  inspector_name?: string;
  sample_quantity?: number;
  sample_no?: string;
  sample_condition?: string;
  standard_id?: string;
  standard_name?: string;
  inspection_conclusion?: StabilityInspectionConclusion;
  conclusion_reason?: string;
  remark?: string;
  oos_report_no?: string;
  attachments?: string;
  items?: StabilityInspectionItemCreate[];
}

// 稳定性试验方案
export interface StabilityStudy {
  id: string;
  study_no: string;
  // 产品信息
  product_code: string;
  product_name?: string;
  product_category?: string;
  // 批号信息
  batch_no?: string;
  batch_quantity?: number;
  packaging_spec?: string;
  // 试验条件
  study_type: StabilityStudyType;
  temperature?: string;
  humidity?: string;
  // 试验时间
  start_date?: string;
  end_date?: string;
  expiry_date?: string;
  // 取样间隔
  sample_intervals?: number[];
  // 质量标准
  standard_id?: string;
  standard_name?: string;
  standard_version?: string;
  // 研发人员
  developer_id?: string;
  developer_name?: string;
  // 状态
  status: StabilityStudyStatus;
  remark?: string;
  attachments?: string;
  // 审批信息
  approved_by?: string;
  approved_at?: string;
  approved_comments?: string;
  // 时间戳
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
  // 关联数据
  sample_nodes?: StabilitySampleNode[];
}

// 稳定性试验方案列表项
export interface StabilityStudyListItem {
  id: string;
  study_no: string;
  product_code: string;
  product_name?: string;
  product_category?: string;
  batch_no?: string;
  study_type: StabilityStudyType;
  temperature?: string;
  humidity?: string;
  start_date?: string;
  status: StabilityStudyStatus;
  developer_name?: string;
  created_at: string;
}

// 稳定性试验方案列表响应
export interface StabilityStudyListResponse {
  items: StabilityStudyListItem[];
  total: number;
  page: number;
  page_size: number;
}

// 稳定性试验方案创建
export interface StabilityStudyCreate {
  product_code: string;
  product_name?: string;
  product_category?: string;
  batch_no?: string;
  batch_quantity?: number;
  packaging_spec?: string;
  study_type: StabilityStudyType;
  temperature?: string;
  humidity?: string;
  start_date?: string;
  end_date?: string;
  expiry_date?: string;
  sample_intervals?: number[];
  standard_id?: string;
  standard_name?: string;
  standard_version?: string;
  developer_id?: string;
  developer_name?: string;
  remark?: string;
  attachments?: string;
  sample_nodes?: StabilitySampleNodeCreate[];
}

// 稳定性试验方案更新
export interface StabilityStudyUpdate {
  product_code?: string;
  product_name?: string;
  product_category?: string;
  batch_no?: string;
  batch_quantity?: number;
  packaging_spec?: string;
  study_type?: StabilityStudyType;
  temperature?: string;
  humidity?: string;
  start_date?: string;
  end_date?: string;
  expiry_date?: string;
  sample_intervals?: number[];
  standard_id?: string;
  standard_name?: string;
  standard_version?: string;
  developer_id?: string;
  developer_name?: string;
  remark?: string;
  attachments?: string;
  sample_nodes?: StabilitySampleNodeCreate[];
}

// 审批记录
export interface StabilityApprovalRecord {
  id: string;
  stability_study_id?: string;
  stability_inspection_id?: string;
  approval_type: "study" | "inspection";
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
export interface StabilityApprovalCreate {
  approval_status: "approved" | "rejected";
  comments?: string;
}

// 筛选条件
export interface StabilityStudyFilter {
  study_no?: string;
  product_code?: string;
  product_name?: string;
  study_type?: StabilityStudyType;
  status?: StabilityStudyStatus;
  batch_no?: string;
  start_date?: string;
  end_date?: string;
}

export interface StabilityInspectionFilter {
  study_id?: string;
  study_no?: string;
  inspection_no?: string;
  batch_no?: string;
  status?: StabilityInspectionStatus;
  start_date?: string;
  end_date?: string;
}

// 趋势数据
export interface TrendDataPoint {
  node_month: number;
  measured_value?: string;
  result?: string;
  inspection_date?: string;
}

export interface TrendData {
  study_no: string;
  product_code: string;
  product_name?: string;
  batch_no?: string;
  study_type: string;
  trend_data: Record<string, TrendDataPoint[]>;
}
