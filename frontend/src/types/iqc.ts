// ========== IQC 检验类型定义 ==========

// 来源类型
export enum IQCSourceType {
  PURCHASE_INBOUND = "purchase_inbound",  // 采购到货
  SUPPLIER_DELIVERY = "supplier_delivery",  // 供应商直送
}

export const IQCSourceTypeLabels: Record<IQCSourceType, string> = {
  [IQCSourceType.PURCHASE_INBOUND]: "采购到货",
  [IQCSourceType.SUPPLIER_DELIVERY]: "供应商直送",
};

// 物料类别
export enum MaterialCategory {
  RAW_MATERIAL = "raw_material",  // 原料药
  EXCIPIENT = "excipient",  // 辅料
  PACKAGING_MATERIAL = "packaging_material",  // 包装材料
}

export const MaterialCategoryLabels: Record<MaterialCategory, string> = {
  [MaterialCategory.RAW_MATERIAL]: "原料药",
  [MaterialCategory.EXCIPIENT]: "辅料",
  [MaterialCategory.PACKAGING_MATERIAL]: "包装材料",
};

// 检验单状态
export enum InspectionStatus {
  DRAFT = "draft",  // 草稿
  SUBMITTED = "submitted",  // 已提交
  DEPARTMENT_APPROVED = "department_approved",  // 部门负责人已审核
  QA_APPROVED = "qa_approved",  // QA已审核
  FINAL_APPROVED = "final_approved",  // 质量负责人终审通过
  REJECTED = "rejected",  // 驳回
}

export const InspectionStatusLabels: Record<InspectionStatus, string> = {
  [InspectionStatus.DRAFT]: "草稿",
  [InspectionStatus.SUBMITTED]: "已提交",
  [InspectionStatus.DEPARTMENT_APPROVED]: "部门负责人已审核",
  [InspectionStatus.QA_APPROVED]: "QA已审核",
  [InspectionStatus.FINAL_APPROVED]: "质量负责人终审通过",
  [InspectionStatus.REJECTED]: "驳回",
};

export const InspectionStatusColors: Record<InspectionStatus, string> = {
  [InspectionStatus.DRAFT]: "default",
  [InspectionStatus.SUBMITTED]: "processing",
  [InspectionStatus.DEPARTMENT_APPROVED]: "processing",
  [InspectionStatus.QA_APPROVED]: "processing",
  [InspectionStatus.FINAL_APPROVED]: "success",
  [InspectionStatus.REJECTED]: "error",
};

// 检验结论
export enum InspectionConclusion {
  QUALIFIED = "qualified",  // 合格
  UNQUALIFIED = "unqualified",  // 不合格
  CONDITIONAL = "conditional",  // 条件合格
}

export const InspectionConclusionLabels: Record<InspectionConclusion, string> = {
  [InspectionConclusion.QUALIFIED]: "合格",
  [InspectionConclusion.UNQUALIFIED]: "不合格",
  [InspectionConclusion.CONDITIONAL]: "条件合格",
};

export const InspectionConclusionColors: Record<InspectionConclusion, string> = {
  [InspectionConclusion.QUALIFIED]: "success",
  [InspectionConclusion.UNQUALIFIED]: "error",
  [InspectionConclusion.CONDITIONAL]: "warning",
};

// 单项判定
export enum ItemResult {
  PASS = "pass",  // 合格
  FAIL = "fail",  // 不合格
  NA = "na",  // 不适用
}

export const ItemResultLabels: Record<ItemResult, string> = {
  [ItemResult.PASS]: "合格",
  [ItemResult.FAIL]: "不合格",
  [ItemResult.NA]: "不适用",
};

// ========== 接口类型 ==========

// IQC检验明细
export interface IQCInspectionItem {
  id: string;
  iqc_inspection_id: string;
  item_no: number;
  inspection_item: string;
  inspection_method?: string;
  standard_value?: string;
  unit?: string;
  measured_value?: string;
  result?: ItemResult;
  is_repeat_test: boolean;
  raw_data?: string;
  remark?: string;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
}

// IQC检验单
export interface IQCInspection {
  id: string;
  inspection_no: string;
  sampling_order_id?: string;
  sampling_order_no?: string;
  source_type: IQCSourceType;
  source_no?: string;
  material_code: string;
  material_name?: string;
  material_category?: MaterialCategory;
  specification?: string;
  batch_no?: string;
  supplier_code?: string;
  supplier_name?: string;
  manufacturing_date?: string;
  expiry_date?: string;
  quantity_received?: number;
  unit?: string;
  inspection_date?: string;
  inspector_id?: string;
  inspector_name?: string;
  standard_id?: string;
  standard_name?: string;
  standard_version?: string;
  status: InspectionStatus;
  inspection_conclusion?: InspectionConclusion;
  remark?: string;
  deviation_id?: string;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
  items: IQCInspectionItem[];
}

// IQC检验单列表项
export interface IQCInspectionListItem {
  id: string;
  inspection_no: string;
  source_type: IQCSourceType;
  source_no?: string;
  material_code: string;
  material_name?: string;
  material_category?: MaterialCategory;
  batch_no?: string;
  supplier_name?: string;
  inspection_date?: string;
  inspector_name?: string;
  status: InspectionStatus;
  inspection_conclusion?: InspectionConclusion;
  created_at: string;
}

// IQC检验单列表响应
export interface IQCInspectionListResponse {
  items: IQCInspectionListItem[];
  total: number;
  page: number;
  page_size: number;
}

// 创建IQC检验单
export interface IQCInspectionCreate {
  source_type: IQCSourceType;
  source_no?: string;
  sampling_order_id?: string;
  sampling_order_no?: string;
  material_code: string;
  material_name?: string;
  material_category?: MaterialCategory;
  specification?: string;
  batch_no?: string;
  supplier_code?: string;
  supplier_name?: string;
  manufacturing_date?: string;
  expiry_date?: string;
  quantity_received?: number;
  unit?: string;
  inspection_date?: string;
  inspector_id?: string;
  inspector_name?: string;
  standard_id?: string;
  standard_name?: string;
  standard_version?: string;
  inspection_conclusion?: InspectionConclusion;
  remark?: string;
  items: IQCInspectionItemCreate[];
}

// IQC检验明细创建
export interface IQCInspectionItemCreate {
  item_no: number;
  inspection_item: string;
  inspection_method?: string;
  standard_value?: string;
  unit?: string;
  measured_value?: string;
  result?: ItemResult;
  is_repeat_test?: boolean;
  raw_data?: string;
  remark?: string;
}

// 更新IQC检验单
export interface IQCInspectionUpdate {
  source_type?: IQCSourceType;
  source_no?: string;
  sampling_order_id?: string;
  sampling_order_no?: string;
  material_code?: string;
  material_name?: string;
  material_category?: MaterialCategory;
  specification?: string;
  batch_no?: string;
  supplier_code?: string;
  supplier_name?: string;
  manufacturing_date?: string;
  expiry_date?: string;
  quantity_received?: number;
  unit?: string;
  inspection_date?: string;
  inspector_id?: string;
  inspector_name?: string;
  standard_id?: string;
  standard_name?: string;
  standard_version?: string;
  inspection_conclusion?: InspectionConclusion;
  remark?: string;
  items?: IQCInspectionItemCreate[];
}

// IQC审批记录
export interface IQCApprovalRecord {
  id: string;
  iqc_inspection_id: string;
  approval_level: number;
  approval_status: string;
  approver_role?: string;
  approver_id?: string;
  approver_name?: string;
  approved_at?: string;
  comments?: string;
  created_at: string;
}

// IQC审批操作
export interface IQCApprovalCreate {
  approval_status: "approved" | "rejected";
  comments?: string;
}

// IQC筛选条件
export interface IQCInspectionFilter {
  inspection_no?: string;
  material_code?: string;
  material_name?: string;
  material_category?: MaterialCategory;
  supplier_name?: string;
  status?: InspectionStatus;
  inspection_conclusion?: InspectionConclusion;
  start_date?: string;
  end_date?: string;
}