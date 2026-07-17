// ========== IPQC 过程检验类型定义 ==========

// IPQC检验单状态
export enum IPQCInspectionStatus {
  DRAFT = "draft",  // 草稿
  SUBMITTED = "submitted",  // 已提交
  WORKSHOP_APPROVED = "workshop_approved",  // 车间工艺负责人已审核
  QC_SUPERVISOR_APPROVED = "qc_supervisor_approved",  // QC主管已复核
  QA_FINAL_APPROVED = "qa_final_approved",  // QA终审通过
  REJECTED = "rejected",  // 驳回
}

export const IPQCInspectionStatusLabels: Record<IPQCInspectionStatus, string> = {
  [IPQCInspectionStatus.DRAFT]: "草稿",
  [IPQCInspectionStatus.SUBMITTED]: "已提交",
  [IPQCInspectionStatus.WORKSHOP_APPROVED]: "车间工艺负责人已审核",
  [IPQCInspectionStatus.QC_SUPERVISOR_APPROVED]: "QC主管已复核",
  [IPQCInspectionStatus.QA_FINAL_APPROVED]: "QA终审通过",
  [IPQCInspectionStatus.REJECTED]: "驳回",
};

export const IPQCInspectionStatusColors: Record<IPQCInspectionStatus, string> = {
  [IPQCInspectionStatus.DRAFT]: "default",
  [IPQCInspectionStatus.SUBMITTED]: "processing",
  [IPQCInspectionStatus.WORKSHOP_APPROVED]: "processing",
  [IPQCInspectionStatus.QC_SUPERVISOR_APPROVED]: "processing",
  [IPQCInspectionStatus.QA_FINAL_APPROVED]: "success",
  [IPQCInspectionStatus.REJECTED]: "error",
};

// 检验结论
export enum IPQCInspectionConclusion {
  QUALIFIED = "qualified",  // 合格
  UNQUALIFIED = "unqualified",  // 不合格
  CONDITIONAL = "conditional",  // 条件合格
}

export const IPQCInspectionConclusionLabels: Record<IPQCInspectionConclusion, string> = {
  [IPQCInspectionConclusion.QUALIFIED]: "合格",
  [IPQCInspectionConclusion.UNQUALIFIED]: "不合格",
  [IPQCInspectionConclusion.CONDITIONAL]: "条件合格",
};

export const IPQCInspectionConclusionColors: Record<IPQCInspectionConclusion, string> = {
  [IPQCInspectionConclusion.QUALIFIED]: "success",
  [IPQCInspectionConclusion.UNQUALIFIED]: "error",
  [IPQCInspectionConclusion.CONDITIONAL]: "warning",
};

// 单项判定
export enum IPQCItemResult {
  PASS = "pass",  // 合格
  FAIL = "fail",  // 不合格
  NA = "na",  // 不适用
}

export const IPQCItemResultLabels: Record<IPQCItemResult, string> = {
  [IPQCItemResult.PASS]: "合格",
  [IPQCItemResult.FAIL]: "不合格",
  [IPQCItemResult.NA]: "不适用",
};

// ========== 接口类型 ==========

// IPQC检验明细
export interface IPQCInspectionItem {
  id: string;
  ipqc_inspection_id: string;
  item_no: number;
  inspection_item: string;
  inspection_method?: string;
  standard_value?: string;
  upper_limit?: string;
  lower_limit?: string;
  unit?: string;
  measured_value?: string;
  result?: IPQCItemResult;
  is_repeat_test: boolean;
  repeat_times: number;
  raw_data?: string;
  remark?: string;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
}

// IPQC检验单
export interface IPQCInspection {
  id: string;
  inspection_no: string;
  // 批次关联信息
  batch_record_id?: string;
  batch_record_no?: string;
  batch_no?: string;
  product_code: string;
  product_name?: string;
  product_specification?: string;
  // 工序信息
  process_stage?: string;
  sampling_point?: string;
  sampling_no?: string;
  sampling_time?: string;
  sampling_quantity?: number;
  sampling_unit?: string;
  sampling_location?: string;
  production_date?: string;
  // 检验信息
  inspection_date?: string;
  inspector_id?: string;
  inspector_name?: string;
  // 质量标准
  standard_id?: string;
  standard_name?: string;
  standard_version?: string;
  // 检验结论
  status: IPQCInspectionStatus;
  inspection_conclusion?: IPQCInspectionConclusion;
  conclusion_reason?: string;
  remark?: string;
  deviation_id?: string;
  oos_report_no?: string;
  // 批次状态
  batch_locked: boolean;
  batch_lock_reason?: string;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
  items: IPQCInspectionItem[];
}

// IPQC检验单列表项
export interface IPQCInspectionListItem {
  id: string;
  inspection_no: string;
  batch_no?: string;
  product_code: string;
  product_name?: string;
  product_specification?: string;
  process_stage?: string;
  sampling_point?: string;
  sampling_time?: string;
  inspector_name?: string;
  status: IPQCInspectionStatus;
  inspection_conclusion?: IPQCInspectionConclusion;
  batch_locked: boolean;
  created_at: string;
}

// IPQC检验单列表响应
export interface IPQCInspectionListResponse {
  items: IPQCInspectionListItem[];
  total: number;
  page: number;
  page_size: number;
}

// 创建IPQC检验单
export interface IPQCInspectionCreate {
  batch_record_id?: string;
  batch_record_no?: string;
  batch_no?: string;
  product_code: string;
  product_name?: string;
  product_specification?: string;
  process_stage?: string;
  sampling_point?: string;
  sampling_no?: string;
  sampling_time?: string;
  sampling_quantity?: number;
  sampling_unit?: string;
  sampling_location?: string;
  production_date?: string;
  inspection_date?: string;
  inspector_id?: string;
  inspector_name?: string;
  standard_id?: string;
  standard_name?: string;
  standard_version?: string;
  inspection_conclusion?: IPQCInspectionConclusion;
  conclusion_reason?: string;
  remark?: string;
  oos_report_no?: string;
  items: IPQCInspectionItemCreate[];
}

// IPQC检验明细创建
export interface IPQCInspectionItemCreate {
  item_no: number;
  inspection_item: string;
  inspection_method?: string;
  standard_value?: string;
  upper_limit?: string;
  lower_limit?: string;
  unit?: string;
  measured_value?: string;
  result?: IPQCItemResult;
  is_repeat_test?: boolean;
  repeat_times?: number;
  raw_data?: string;
  remark?: string;
}

// 更新IPQC检验单
export interface IPQCInspectionUpdate {
  batch_record_id?: string;
  batch_record_no?: string;
  batch_no?: string;
  product_code?: string;
  product_name?: string;
  product_specification?: string;
  process_stage?: string;
  sampling_point?: string;
  sampling_no?: string;
  sampling_time?: string;
  sampling_quantity?: number;
  sampling_unit?: string;
  sampling_location?: string;
  production_date?: string;
  inspection_date?: string;
  inspector_id?: string;
  inspector_name?: string;
  standard_id?: string;
  standard_name?: string;
  standard_version?: string;
  inspection_conclusion?: IPQCInspectionConclusion;
  conclusion_reason?: string;
  remark?: string;
  oos_report_no?: string;
  items?: IPQCInspectionItemCreate[];
}

// IPQC审批记录
export interface IPQCApprovalRecord {
  id: string;
  ipqc_inspection_id: string;
  approval_level: number;
  approval_status: string;
  approver_role?: string;
  approver_id?: string;
  approver_name?: string;
  approved_at?: string;
  comments?: string;
  created_at: string;
}

// IPQC审批操作
export interface IPQCApprovalCreate {
  approval_status: "approved" | "rejected";
  comments?: string;
}

// IPQC筛选条件
export interface IPQCInspectionFilter {
  inspection_no?: string;
  batch_no?: string;
  product_code?: string;
  product_name?: string;
  process_stage?: string;
  status?: IPQCInspectionStatus;
  inspection_conclusion?: IPQCInspectionConclusion;
  batch_locked?: boolean;
  start_date?: string;
  end_date?: string;
}
