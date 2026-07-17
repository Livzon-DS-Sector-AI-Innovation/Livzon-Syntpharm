// ========== FQC 成品检验类型定义 ==========

// FQC检验单状态
export enum FQCInspectionStatus {
  DRAFT = "draft",  // 草稿
  SUBMITTED = "submitted",  // 已提交
  QC_SUPERVISOR_APPROVED = "qc_supervisor_approved",  // QC主管已审核
  QA_APPROVED = "qa_approved",  // QA已审核
  FINAL_APPROVED = "final_approved",  // 质量负责人终审
  RELEASED = "released",  // 已放行
  LOCKED = "locked",  // 锁定
  CLOSED = "closed",  // 已关闭
  REJECTED = "rejected",  // 驳回
}

export const FQCInspectionStatusLabels: Record<FQCInspectionStatus, string> = {
  [FQCInspectionStatus.DRAFT]: "草稿",
  [FQCInspectionStatus.SUBMITTED]: "已提交",
  [FQCInspectionStatus.QC_SUPERVISOR_APPROVED]: "QC主管已审核",
  [FQCInspectionStatus.QA_APPROVED]: "QA已审核",
  [FQCInspectionStatus.FINAL_APPROVED]: "质量负责人终审",
  [FQCInspectionStatus.RELEASED]: "已放行",
  [FQCInspectionStatus.LOCKED]: "锁定",
  [FQCInspectionStatus.CLOSED]: "已关闭",
  [FQCInspectionStatus.REJECTED]: "驳回",
};

export const FQCInspectionStatusColors: Record<FQCInspectionStatus, string> = {
  [FQCInspectionStatus.DRAFT]: "default",
  [FQCInspectionStatus.SUBMITTED]: "processing",
  [FQCInspectionStatus.QC_SUPERVISOR_APPROVED]: "processing",
  [FQCInspectionStatus.QA_APPROVED]: "processing",
  [FQCInspectionStatus.FINAL_APPROVED]: "success",
  [FQCInspectionStatus.RELEASED]: "success",
  [FQCInspectionStatus.LOCKED]: "error",
  [FQCInspectionStatus.CLOSED]: "default",
  [FQCInspectionStatus.REJECTED]: "error",
};

// 检验结论
export enum FQCInspectionConclusion {
  QUALIFIED = "qualified",  // 合格
  UNQUALIFIED = "unqualified",  // 不合格
}

export const FQCInspectionConclusionLabels: Record<FQCInspectionConclusion, string> = {
  [FQCInspectionConclusion.QUALIFIED]: "合格",
  [FQCInspectionConclusion.UNQUALIFIED]: "不合格",
};

export const FQCInspectionConclusionColors: Record<FQCInspectionConclusion, string> = {
  [FQCInspectionConclusion.QUALIFIED]: "success",
  [FQCInspectionConclusion.UNQUALIFIED]: "error",
};

// 放行状态
export enum FQCReleaseStatus {
  PENDING_RELEASE = "pending_release",  // 待放行
  RELEASED = "released",  // 已放行
  NOT_RELEASED = "not_released",  // 未放行
}

export const FQCReleaseStatusLabels: Record<FQCReleaseStatus, string> = {
  [FQCReleaseStatus.PENDING_RELEASE]: "待放行",
  [FQCReleaseStatus.RELEASED]: "已放行",
  [FQCReleaseStatus.NOT_RELEASED]: "未放行",
};

// 单项判定
export enum FQCItemResult {
  PASS = "pass",  // 合格
  FAIL = "fail",  // 不合格
  NA = "na",  // 不适用
}

export const FQCItemResultLabels: Record<FQCItemResult, string> = {
  [FQCItemResult.PASS]: "合格",
  [FQCItemResult.FAIL]: "不合格",
  [FQCItemResult.NA]: "不适用",
};

// 检验类别
export enum FQCInspectionCategory {
  CONTENT = "content",  // 含量
  RELATED_SUBSTANCES = "related_substances",  // 有关物质
  RESIDUAL_SOLVENTS = "residual_solvents",  // 残留溶剂
  PHYSICAL_CHEMICAL = "physical_chemical",  // 理化
  MICROBIOLOGY = "microbiology",  // 微生物
}

export const FQCInspectionCategoryLabels: Record<FQCInspectionCategory, string> = {
  [FQCInspectionCategory.CONTENT]: "含量",
  [FQCInspectionCategory.RELATED_SUBSTANCES]: "有关物质",
  [FQCInspectionCategory.RESIDUAL_SOLVENTS]: "残留溶剂",
  [FQCInspectionCategory.PHYSICAL_CHEMICAL]: "理化",
  [FQCInspectionCategory.MICROBIOLOGY]: "微生物",
};

// ========== 接口类型 ==========

// FQC检验明细
export interface FQCInspectionItem {
  id: string;
  fqc_inspection_id: string;
  item_no: number;
  inspection_category?: FQCInspectionCategory;
  inspection_item: string;
  inspection_method?: string;
  standard_value?: string;
  unit?: string;
  measured_value?: string;
  result?: FQCItemResult;
  is_oos: boolean;
  oos_description?: string;
  is_repeat_test: boolean;
  repeat_times: number;
  chromatogram_urls?: string;
  raw_record_url?: string;
  remark?: string;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
}

// FQC检验单
export interface FQCInspection {
  id: string;
  inspection_no: string;
  // 单据关联
  batch_record_id?: string;
  batch_record_no?: string;
  batch_no?: string;
  product_code: string;
  product_name?: string;
  sampling_order_id?: string;
  sampling_order_no?: string;
  batch_quantity?: number;
  production_workshop?: string;
  // 基础信息
  cas_no?: string;
  manufacturing_date?: string;
  expiry_date?: string;
  manufacturer?: string;
  specification?: string;
  // 检验信息
  inspection_date?: string;
  inspector_id?: string;
  inspector_name?: string;
  // 质量标准
  standard_id?: string;
  standard_name?: string;
  standard_version?: string;
  // 检验结论
  status: FQCInspectionStatus;
  inspection_conclusion?: FQCInspectionConclusion;
  conclusion_reason?: string;
  remark?: string;
  // OOS与偏差
  oos_report_no?: string;
  deviation_id?: string;
  // 批次状态
  batch_locked: boolean;
  batch_lock_reason?: string;
  warehouse_isolation: boolean;
  // 放行状态
  release_status?: FQCReleaseStatus;
  release_reason?: string;
  // 复检
  reinspection_applied: boolean;
  reinspection_reason?: string;
  // 附件
  attachments?: string;
  // 检验报告
  report_no?: string;
  report_url?: string;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
  items: FQCInspectionItem[];
}

// FQC检验单列表项
export interface FQCInspectionListItem {
  id: string;
  inspection_no: string;
  batch_no?: string;
  product_code: string;
  product_name?: string;
  production_workshop?: string;
  batch_quantity?: number;
  manufacturing_date?: string;
  inspector_name?: string;
  inspection_date?: string;
  status: FQCInspectionStatus;
  inspection_conclusion?: FQCInspectionConclusion;
  release_status?: FQCReleaseStatus;
  batch_locked: boolean;
  created_at: string;
}

// FQC检验单列表响应
export interface FQCInspectionListResponse {
  items: FQCInspectionListItem[];
  total: number;
  page: number;
  page_size: number;
}

// 创建FQC检验单
export interface FQCInspectionCreate {
  batch_record_id?: string;
  batch_record_no?: string;
  batch_no?: string;
  product_code: string;
  product_name?: string;
  sampling_order_id?: string;
  sampling_order_no?: string;
  batch_quantity?: number;
  production_workshop?: string;
  cas_no?: string;
  manufacturing_date?: string;
  expiry_date?: string;
  manufacturer?: string;
  specification?: string;
  inspection_date?: string;
  inspector_id?: string;
  inspector_name?: string;
  standard_id?: string;
  standard_name?: string;
  standard_version?: string;
  inspection_conclusion?: FQCInspectionConclusion;
  conclusion_reason?: string;
  remark?: string;
  oos_report_no?: string;
  reinspection_applied?: boolean;
  reinspection_reason?: string;
  attachments?: string;
  items: FQCInspectionItemCreate[];
}

// FQC检验明细创建
export interface FQCInspectionItemCreate {
  item_no: number;
  inspection_category?: FQCInspectionCategory;
  inspection_item: string;
  inspection_method?: string;
  standard_value?: string;
  unit?: string;
  measured_value?: string;
  result?: FQCItemResult;
  is_oos?: boolean;
  oos_description?: string;
  is_repeat_test?: boolean;
  repeat_times?: number;
  chromatogram_urls?: string;
  raw_record_url?: string;
  remark?: string;
}

// 更新FQC检验单
export interface FQCInspectionUpdate {
  batch_record_id?: string;
  batch_record_no?: string;
  batch_no?: string;
  product_code?: string;
  product_name?: string;
  sampling_order_id?: string;
  sampling_order_no?: string;
  batch_quantity?: number;
  production_workshop?: string;
  cas_no?: string;
  manufacturing_date?: string;
  expiry_date?: string;
  manufacturer?: string;
  specification?: string;
  inspection_date?: string;
  inspector_id?: string;
  inspector_name?: string;
  standard_id?: string;
  standard_name?: string;
  standard_version?: string;
  inspection_conclusion?: FQCInspectionConclusion;
  conclusion_reason?: string;
  remark?: string;
  oos_report_no?: string;
  reinspection_applied?: boolean;
  reinspection_reason?: string;
  attachments?: string;
  items?: FQCInspectionItemCreate[];
}

// FQC审批记录
export interface FQCApprovalRecord {
  id: string;
  fqc_inspection_id: string;
  approval_level: number;
  approval_status: string;
  approver_role?: string;
  approver_id?: string;
  approver_name?: string;
  approved_at?: string;
  comments?: string;
  created_at: string;
}

// FQC审批操作
export interface FQCApprovalCreate {
  approval_status: "approved" | "rejected";
  comments?: string;
}

// FQC筛选条件
export interface FQCInspectionFilter {
  inspection_no?: string;
  batch_no?: string;
  product_code?: string;
  product_name?: string;
  production_workshop?: string;
  status?: FQCInspectionStatus;
  inspection_conclusion?: FQCInspectionConclusion;
  release_status?: FQCReleaseStatus;
  batch_locked?: boolean;
  start_date?: string;
  end_date?: string;
}
