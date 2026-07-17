// ========== 仪器校准管理类型定义 ==========

// 仪器状态（简化版：只有启用/未启用）
export enum InstrumentStatus {
  ACTIVE = "active",
  INACTIVE = "inactive",
}

export const InstrumentStatusLabels: Record<InstrumentStatus, string> = {
  [InstrumentStatus.ACTIVE]: "已启用",
  [InstrumentStatus.INACTIVE]: "已停用",
};

export const InstrumentStatusColors: Record<InstrumentStatus, string> = {
  [InstrumentStatus.ACTIVE]: "success",
  [InstrumentStatus.INACTIVE]: "default",
};

// 校准方式
export enum CalibrationMethod {
  EXTERNAL = "external",
  INTERNAL = "internal",
}

export const CalibrationMethodLabels: Record<CalibrationMethod, string> = {
  [CalibrationMethod.EXTERNAL]: "外委校准",
  [CalibrationMethod.INTERNAL]: "内部校准",
};

// 校准周期单位
export enum CalibrationCycleUnit {
  MONTH = "month",
  YEAR = "year",
}

export const CalibrationCycleUnitLabels: Record<CalibrationCycleUnit, string> = {
  [CalibrationCycleUnit.MONTH]: "月",
  [CalibrationCycleUnit.YEAR]: "年",
};

// IQ确认状态
export enum IQStatus {
  PENDING = "pending",
  CONFIRMED = "confirmed",
  NOT_REQUIRED = "not_required",
}

export const IQStatusLabels: Record<IQStatus, string> = {
  [IQStatus.PENDING]: "待确认",
  [IQStatus.CONFIRMED]: "已确认",
  [IQStatus.NOT_REQUIRED]: "不需要",
};

export const IQStatusColors: Record<IQStatus, string> = {
  [IQStatus.PENDING]: "warning",
  [IQStatus.CONFIRMED]: "success",
  [IQStatus.NOT_REQUIRED]: "default",
};

// OQ确认状态
export enum OQStatus {
  PENDING = "pending",
  CONFIRMED = "confirmed",
  NOT_REQUIRED = "not_required",
}

export const OQStatusLabels: Record<OQStatus, string> = {
  [OQStatus.PENDING]: "待确认",
  [OQStatus.CONFIRMED]: "已确认",
  [OQStatus.NOT_REQUIRED]: "不需要",
};

export const OQStatusColors: Record<OQStatus, string> = {
  [OQStatus.PENDING]: "warning",
  [OQStatus.CONFIRMED]: "success",
  [OQStatus.NOT_REQUIRED]: "default",
};

// 仪器分类
export enum InstrumentCategory {
  PHYSICOCHEMICAL = "physicochemical",
  CHROMATOGRAPHY = "chromatography",
  MICROBIOLOGY = "microbiology",
  BALANCE = "balance",
  OVEN = "oven",
  OTHER = "other",
}

export const InstrumentCategoryLabels: Record<InstrumentCategory, string> = {
  [InstrumentCategory.PHYSICOCHEMICAL]: "理化",
  [InstrumentCategory.CHROMATOGRAPHY]: "色谱",
  [InstrumentCategory.MICROBIOLOGY]: "微生物",
  [InstrumentCategory.BALANCE]: "天平",
  [InstrumentCategory.OVEN]: "烘箱",
  [InstrumentCategory.OTHER]: "其他",
};

// 校准结论
export enum CalibrationResult {
  QUALIFIED = "qualified",
  UNQUALIFIED = "unqualified",
  LIMITED = "limited",
}

export const CalibrationResultLabels: Record<CalibrationResult, string> = {
  [CalibrationResult.QUALIFIED]: "合格",
  [CalibrationResult.UNQUALIFIED]: "不合格",
  [CalibrationResult.LIMITED]: "限用",
};

export const CalibrationResultColors: Record<CalibrationResult, string> = {
  [CalibrationResult.QUALIFIED]: "success",
  [CalibrationResult.UNQUALIFIED]: "error",
  [CalibrationResult.LIMITED]: "warning",
};

// 校准记录状态（启用/停用）
export enum RecordStatus {
  ACTIVE = "active",
  INACTIVE = "inactive",
}

export const RecordStatusLabels: Record<RecordStatus, string> = {
  [RecordStatus.ACTIVE]: "已启用",
  [RecordStatus.INACTIVE]: "已停用",
};

export const RecordStatusColors: Record<RecordStatus, string> = {
  [RecordStatus.ACTIVE]: "success",
  [RecordStatus.INACTIVE]: "default",
};

// 审批类型
export enum ApprovalType {
  INSTRUMENT = "instrument",
  RECORD = "record",
}

// 审批状态
export enum ApprovalStatus {
  PENDING = "pending",
  APPROVED = "approved",
  REJECTED = "rejected",
}

export const ApprovalStatusLabels: Record<ApprovalStatus, string> = {
  [ApprovalStatus.PENDING]: "待审批",
  [ApprovalStatus.APPROVED]: "已批准",
  [ApprovalStatus.REJECTED]: "已驳回",
};

export const ApprovalStatusColors: Record<ApprovalStatus, string> = {
  [ApprovalStatus.PENDING]: "processing",
  [ApprovalStatus.APPROVED]: "success",
  [ApprovalStatus.REJECTED]: "error",
};

// ========== 接口类型 ==========

// 仪器设备台账
export interface Instrument {
  id: string;
  instrument_no: string;
  instrument_name: string;
  model?: string;
  serial_no?: string;
  manufacturer?: string;
  location?: string;
  category?: InstrumentCategory;
  manufacture_date?: string;
  responsible_id?: string;
  responsible_name?: string;
  is_active: boolean;
  deactivate_date?: string;
  deactivate_reason?: string;
  remark?: string;
  status: InstrumentStatus;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
  // 关联校准规则
  calibration_rules?: CalibrationRule[];
  // 计算字段
  next_calibration_date?: string;
  is_overdue?: boolean;
}

// 仪器列表项
export interface InstrumentListItem {
  id: string;
  instrument_no: string;
  instrument_name: string;
  model?: string;
  category?: string;
  location?: string;
  responsible_name?: string;
  is_active: boolean;
  status: InstrumentStatus;
  next_calibration_date?: string;
  is_overdue: boolean;
  created_at: string;
  // 校准记录的到期信息
  valid_until?: string | null;
}

// 仪器列表响应
export interface InstrumentListResponse {
  items: InstrumentListItem[];
  total: number;
  page: number;
  page_size: number;
}

// 创建仪器
export interface InstrumentCreate {
  instrument_no: string;
  instrument_name: string;
  model?: string;
  serial_no?: string;
  manufacturer?: string;
  location?: string;
  category?: InstrumentCategory;
  manufacture_date?: string;
  responsible_id?: string;
  responsible_name?: string;
  is_active?: boolean;
  deactivate_date?: string;
  deactivate_reason?: string;
  remark?: string;
}

// 更新仪器
export interface InstrumentUpdate {
  instrument_name?: string;
  model?: string;
  serial_no?: string;
  manufacturer?: string;
  location?: string;
  category?: InstrumentCategory;
  manufacture_date?: string;
  responsible_id?: string;
  responsible_name?: string;
  is_active?: boolean;
  deactivate_date?: string;
  deactivate_reason?: string;
  remark?: string;
}

// 校准规则
export interface CalibrationRule {
  id: string;
  instrument_id: string;
  calibration_method: CalibrationMethod;
  calibration_cycle?: number;
  calibration_unit?: CalibrationCycleUnit;
  last_calibration_date?: string;
  next_calibration_date?: string;
  calibration_agency?: string;
  agency_contact?: string;
  internal_calibrator_id?: string;
  internal_calibrator_name?: string;
  warning_days: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
}

// 创建校准规则
export interface CalibrationRuleCreate {
  instrument_id: string;
  calibration_method: CalibrationMethod;
  calibration_cycle?: number;
  calibration_unit?: CalibrationCycleUnit;
  last_calibration_date?: string;
  next_calibration_date?: string;
  calibration_agency?: string;
  agency_contact?: string;
  internal_calibrator_id?: string;
  internal_calibrator_name?: string;
  warning_days?: number;
  is_active?: boolean;
}

// 更新校准规则
export interface CalibrationRuleUpdate {
  calibration_method?: CalibrationMethod;
  calibration_cycle?: number;
  calibration_unit?: CalibrationCycleUnit;
  last_calibration_date?: string;
  next_calibration_date?: string;
  calibration_agency?: string;
  agency_contact?: string;
  internal_calibrator_id?: string;
  internal_calibrator_name?: string;
  warning_days?: number;
  is_active?: boolean;
}

// 校准记录
export interface CalibrationRecord {
  id: string;
  instrument_id: string;
  rule_id?: string;
  calibration_no: string;
  calibration_date: string;
  calibration_end_date?: string;
  calibration_method: CalibrationMethod;
  calibration_agency?: string;
  calibrator_id?: string;
  calibrator_name?: string;
  certificate_no?: string;
  certificate_url?: string;
  calibration_result: CalibrationResult;
  result_reason?: string;
  valid_from?: string;
  valid_until?: string;
  is_scheduled: boolean;
  scheduled_date?: string;
  remark?: string;
  status: RecordStatus;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
  // 关联仪器信息
  instrument_no?: string;
  instrument_name?: string;
}

// 校准记录列表项
export interface CalibrationRecordListItem {
  id: string;
  calibration_no: string;
  instrument_id: string;
  rule_id?: string | null;
  instrument_no: string;
  instrument_name: string;
  calibration_date: string;
  valid_until?: string;
  calibration_method: string;
  calibration_result: CalibrationResult;
  status: RecordStatus;
  calibrator_name?: string;
  certificate_no?: string;
  created_at: string;
}

// 校准记录列表响应
export interface CalibrationRecordListResponse {
  items: CalibrationRecordListItem[];
  total: number;
  page: number;
  page_size: number;
}

// 创建校准记录
export interface CalibrationRecordCreate {
  instrument_id: string;
  rule_id?: string;
  calibration_no?: string;
  calibration_date: string;
  calibration_end_date?: string;
  calibration_method: CalibrationMethod;
  calibration_agency?: string;
  calibrator_id?: string;
  calibrator_name?: string;
  certificate_no?: string;
  certificate_url?: string;
  calibration_result: CalibrationResult;
  result_reason?: string;
  valid_from?: string;
  valid_until?: string;
  is_scheduled?: boolean;
  scheduled_date?: string;
  remark?: string;
}

// 更新校准记录
export interface CalibrationRecordUpdate {
  calibration_date?: string;
  calibration_end_date?: string;
  calibration_method?: CalibrationMethod;
  calibration_agency?: string;
  calibrator_id?: string;
  calibrator_name?: string;
  certificate_no?: string;
  certificate_url?: string;
  calibration_result?: CalibrationResult;
  result_reason?: string;
  valid_from?: string;
  valid_until?: string;
  is_scheduled?: boolean;
  scheduled_date?: string;
  remark?: string;
  is_active?: boolean;
}

// 审批记录
export interface ApprovalRecord {
  id: string;
  related_type: ApprovalType;
  related_id: string;
  approval_type: string;
  sequence: number;
  status: ApprovalStatus;
  approval_date?: string;
  comments?: string;
  approver_id?: string;
  approver_name?: string;
  created_at: string;
  updated_at: string;
}

// 审批操作
export interface ApprovalCreate {
  status: ApprovalStatus;
  comments?: string;
}

// 筛选条件
export interface InstrumentFilter {
  instrument_no?: string;
  instrument_name?: string;
  category?: InstrumentCategory;
  is_active?: boolean;
  status?: InstrumentStatus;
  is_overdue?: boolean;
  page?: number;
  page_size?: number;
}

export interface CalibrationRecordFilter {
  instrument_id?: string;
  rule_id?: string;
  calibration_no?: string;
  calibration_result?: CalibrationResult;
  status?: RecordStatus;
  calibration_method?: CalibrationMethod;
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
}

// AI 识别的仪器信息
export interface AIRecognizedInstrumentInfo {
  instrument_no?: string
  instrument_name?: string
  category?: string
  manufacturer?: string
  model?: string
  serial_number?: string
  location?: string
  calibration_method?: string
  calibration_cycle?: number
  calibration_cycle_unit?: string
  iqc_status?: string
  next_calibration_date?: string
  [key: string]: any
}
