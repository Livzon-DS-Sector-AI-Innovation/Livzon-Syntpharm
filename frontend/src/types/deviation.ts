// 偏差管理类型定义

// ============ 枚举定义 ============

export enum DeviationType {
  IPC_DEFECT = 'ipc_defect',                       // 过程控制（IPC）缺陷
  FOREIGN_OBJECT = 'foreign_object',               // 外来异物（有形）
  CALIBRATION_MAINTENANCE = 'calibration_maintenance',  // 校验/预防维修
  MIXUP = 'mixup',                                 // 混淆
  MATERIAL_QUALITY_DEFECT = 'material_quality_defect',  // 物料质量缺陷
  PERSONNEL_ERROR = 'personnel_error',             // 人员失误
  OOS_RESULT = 'oos_result',                       // 超标检验结果
  DOCUMENTATION_DEFECT = 'documentation_defect',   // 文件记录缺陷
  EQUIPMENT_FAILURE = 'equipment_failure',         // 设备故障/过程中断
  ENVIRONMENT = 'environment',                     // 环境
  OTHER = 'other',                                 // 其它
}

export enum DeviationLevel {
  CRITICAL = 'critical',   // 重大
  MAJOR = 'major',         // 主要
  MINOR = 'minor',         // 次要
}

export enum DeviationStatus {
  DRAFT = 'draft',               // 草稿
  SUBMITTED = 'submitted',        // 已提交
  ADMIN_APPROVED = 'admin_approved',    // 部门负责人已审核
  QA_APPROVED = 'qa_approved',          // QA已审核
  QUALITY_APPROVED = 'quality_approved', // 质量负责人已审核
  ACTIVE = 'active',             // 已启用/调查中
  INVESTIGATING = 'investigating',  // 调查中
  INVESTIGATION_COMPLETED = 'investigation_completed',  // 调查完成
  CORRECTION_PENDING = 'correction_pending',  // 待整改
  CORRECTION_IN_PROGRESS = 'correction_in_progress',  // 整改中
  CORRECTION_COMPLETED = 'correction_completed',  // 整改完成
  CLOSING_PENDING = 'closing_pending',  // 待关闭
  CLOSED = 'closed',             // 已关闭
  REJECTED = 'rejected',         // 已驳回
}

export enum InvestigationStatus {
  PENDING = 'pending',           // 待调查
  IN_PROGRESS = 'in_progress',   // 调查中
  COMPLETED = 'completed',       // 已完成
}

export enum CorrectionStatus {
  PENDING = 'pending',           // 待整改
  IN_PROGRESS = 'in_progress',   // 整改中
  COMPLETED = 'completed',       // 已完成
}

// ============ 标签页类型 ============
export type DeviationTabKey = 'list' | 'investigation' | 'correction' | 'closing' | 'statistics';

// ============ 偏差主数据 ============

export interface DeviationCreate {
  occurrence_date?: string;
  discovering_department?: string;
  discoverer?: string;
  product_code?: string;
  product_name?: string;
  production_batch?: string;
  material_code?: string;
  batch_size?: string;
  deviation_type: DeviationType;
  deviation_level: DeviationLevel;
  abnormal_description?: string;
  impact_scope?: string;
  emergency_measures?: string;
  attachments?: string[];
  batch_locked?: boolean;
  batch_lock_reason?: string;
}

export interface DeviationUpdate {
  occurrence_date?: string;
  discovering_department?: string;
  discoverer?: string;
  product_code?: string;
  product_name?: string;
  production_batch?: string;
  material_code?: string;
  batch_size?: string;
  deviation_type?: DeviationType;
  deviation_level?: DeviationLevel;
  abnormal_description?: string;
  impact_scope?: string;
  emergency_measures?: string;
  attachments?: string[];
  batch_locked?: boolean;
  batch_lock_reason?: string;
  status?: string;
  description?: string;
  investigation?: {
    direct_cause?: string;
    root_cause?: string;
    investigation_conclusion?: string;
  };
  correction?: {
    correction_measures?: string;
    responsible_department?: string;
    plan_completion_date?: string;
    actual_completion_date?: string;
  };
}

export interface Deviation {
  id: string;
  deviation_no: string;
  occurrence_date?: string;
  occurrence_location?: string;
  discovering_department?: string;
  discoverer?: string;
  product_code?: string;
  product_name?: string;
  production_batch?: string;
  batch_no?: string;
  material_code?: string;
  batch_size?: string;
  deviation_type: DeviationType;
  deviation_level: DeviationLevel;
  abnormal_description?: string;
  description?: string;
  impact_scope?: string;
  initial_impact?: string;
  emergency_measures?: string;
  attachments?: string[];
  batch_locked: boolean;
  batch_lock_reason?: string;
  batch_locked_at?: string;
  status: DeviationStatus;
  created_at: string;
  updated_at?: string;
  investigation?: Investigation | null;
  corrections?: Correction[];
  closing?: Closing | null;
}

export interface DeviationListItem {
  id: string;
  deviation_no: string;
  occurrence_date?: string;
  discovering_department?: string;
  deviation_type: DeviationType;
  deviation_level: DeviationLevel;
  product_name?: string;
  production_batch?: string;
  status: DeviationStatus;
  batch_locked: boolean;
  has_investigation: boolean;
  has_correction: boolean;
  has_closing: boolean;
  created_at: string;
}

export interface DeviationDetail extends Deviation {
  investigation?: Investigation | null;
  correction?: Correction | null;
  closing?: Closing | null;
  approvals?: Approval[];
}

// ============ 偏差调查 ============

export interface InvestigationCreate {
  investigation_team?: string;
  investigation_start_date?: string;
  investigation_end_date?: string;
  investigation_method?: string;
  direct_cause?: string;
  indirect_cause?: string;
  root_cause?: string;
  why_analysis?: string;
  impact_assessment?: string;
  affected_batches?: string;
  temporary_measures?: string;
  attachments?: string[];
}

export interface InvestigationUpdate extends InvestigationCreate {
  status?: InvestigationStatus;
}

export interface Investigation {
  id: string;
  deviation_id: string;
  investigator?: string;
  investigation_date?: string;
  investigation_team?: string;
  investigation_start_date?: string;
  investigation_end_date?: string;
  investigation_method?: string;
  direct_cause?: string;
  indirect_cause?: string;
  root_cause?: string;
  why_analysis?: string;
  impact_assessment?: string;
  affected_batches?: string;
  temporary_measures?: string;
  attachments?: string[];
  status: InvestigationStatus;
  created_at: string;
  updated_at?: string;
}

export interface InvestigationListItem {
  id: string;
  deviation_id: string;
  deviation_no: string;
  investigation_team?: string;
  investigation_start_date?: string;
  investigation_end_date?: string;
  status: InvestigationStatus;
  created_at: string;
}

// ============ 偏差整改 ============

export interface CorrectiveActionItem {
  content: string;
  department?: string;
  responsible_person?: string;
  plan_date?: string;
  completed: boolean;
  completion_date?: string;
}

export interface CorrectionCreate {
  responsible_department?: string;
  responsible_person?: string;
  plan_completion_date?: string;
  temporary_corrective_actions?: CorrectiveActionItem[];
  long_term_corrective_actions?: CorrectiveActionItem[];
}

export interface CorrectionUpdate extends CorrectionCreate {
  progress?: number;
  status?: CorrectionStatus;
  evidence_attachments?: string[];
}

export interface Correction {
  id: string;
  deviation_id: string;
  responsible_department?: string;
  responsible_person?: string;
  plan_completion_date?: string;
  planned_completion_date?: string;
  actual_completion_date?: string;
  temporary_corrective_actions?: CorrectiveActionItem[];
  long_term_corrective_actions?: CorrectiveActionItem[];
  progress: number;
  status: CorrectionStatus;
  effectiveness_evaluation?: string;
  evidence_attachments?: string[];
  created_at: string;
  updated_at?: string;
}

export interface CorrectionListItem {
  id: string;
  deviation_id: string;
  deviation_no: string;
  responsible_department?: string;
  responsible_person?: string;
  plan_completion_date?: string;
  progress: number;
  status: CorrectionStatus;
  created_at: string;
}

// ============ 偏差关闭 ============

export interface ClosingCreate {
  verification_plan?: string;
  verification_data?: string;
  verification_result?: string;
  is_resolved?: boolean;
  conclusion?: string;
  attachments?: string[];
}

export type ClosingUpdate = ClosingCreate

export interface Closing {
  id: string;
  deviation_id: string;
  closing_date?: string;
  closed_by?: string;
  verification_plan?: string;
  verification_data?: string;
  verification_result?: string;
  is_resolved: boolean;
  conclusion?: string;
  has_remaining_issues?: boolean;
  follow_up_action?: string;
  attachments?: string[];
  batch_unlocked: boolean;
  archived: boolean;
  archived_at?: string;
  created_at: string;
  updated_at?: string;
}

export interface ClosingListItem {
  id: string;
  deviation_id: string;
  deviation_no: string;
  is_resolved: boolean;
  conclusion?: string;
  archived: boolean;
  created_at: string;
}

// ============ 审批 ============

export interface Approval {
  id: string;
  deviation_id: string;
  approval_type: string;
  approver_name?: string;
  approver_department?: string;
  approval_comments?: string;
  approved: boolean;
  approved_at?: string;
  created_at: string;
}

// ============ 统计 ============

export interface DeviationStatistics {
  total_count: number;
  this_month_count?: number;
  major_count?: number;
  avg_resolution_days?: number;
  pending_count?: number;
  investigating_count?: number;
  correcting_count?: number;
  closed_count?: number;
  by_type: { type: string; count: number }[];
  by_level: { level: string; count: number }[];
  by_status: Record<string, number>;
}

// ============ 筛选条件 ============

export interface DeviationFilter {
  deviation_no?: string;
  deviation_type?: DeviationType;
  deviation_level?: DeviationLevel;
  status?: DeviationStatus;
  start_date?: string;
  end_date?: string;
  product_batch?: string;
  department?: string;
}

// ============ 枚举标签映射 ============

export const DeviationTypeLabels: Record<DeviationType, string> = {
  [DeviationType.IPC_DEFECT]: '过程控制（IPC）缺陷',
  [DeviationType.FOREIGN_OBJECT]: '外来异物（有形）',
  [DeviationType.CALIBRATION_MAINTENANCE]: '校验/预防维修',
  [DeviationType.MIXUP]: '混淆',
  [DeviationType.MATERIAL_QUALITY_DEFECT]: '物料质量缺陷',
  [DeviationType.PERSONNEL_ERROR]: '人员失误',
  [DeviationType.OOS_RESULT]: '超标检验结果',
  [DeviationType.DOCUMENTATION_DEFECT]: '文件记录缺陷',
  [DeviationType.EQUIPMENT_FAILURE]: '设备故障/过程中断',
  [DeviationType.ENVIRONMENT]: '环境',
  [DeviationType.OTHER]: '其它',
};

export const DeviationLevelLabels: Record<DeviationLevel, string> = {
  [DeviationLevel.CRITICAL]: '重大',
  [DeviationLevel.MAJOR]: '主要',
  [DeviationLevel.MINOR]: '次要',
};

export const DeviationStatusLabels: Record<DeviationStatus, string> = {
  [DeviationStatus.DRAFT]: '草稿',
  [DeviationStatus.SUBMITTED]: '已提交',
  [DeviationStatus.ADMIN_APPROVED]: '部门已审核',
  [DeviationStatus.QA_APPROVED]: 'QA已审核',
  [DeviationStatus.QUALITY_APPROVED]: '质量已审核',
  [DeviationStatus.ACTIVE]: '已启用',
  [DeviationStatus.INVESTIGATING]: '调查中',
  [DeviationStatus.INVESTIGATION_COMPLETED]: '调查完成',
  [DeviationStatus.CORRECTION_PENDING]: '待整改',
  [DeviationStatus.CORRECTION_IN_PROGRESS]: '整改中',
  [DeviationStatus.CORRECTION_COMPLETED]: '整改完成',
  [DeviationStatus.CLOSING_PENDING]: '待关闭',
  [DeviationStatus.CLOSED]: '已关闭',
  [DeviationStatus.REJECTED]: '已驳回',
};

export const DeviationStatusColors: Record<DeviationStatus, string> = {
  [DeviationStatus.DRAFT]: 'default',
  [DeviationStatus.SUBMITTED]: 'processing',
  [DeviationStatus.ADMIN_APPROVED]: 'processing',
  [DeviationStatus.QA_APPROVED]: 'processing',
  [DeviationStatus.QUALITY_APPROVED]: 'processing',
  [DeviationStatus.ACTIVE]: 'warning',
  [DeviationStatus.INVESTIGATING]: 'warning',
  [DeviationStatus.INVESTIGATION_COMPLETED]: 'success',
  [DeviationStatus.CORRECTION_PENDING]: 'warning',
  [DeviationStatus.CORRECTION_IN_PROGRESS]: 'warning',
  [DeviationStatus.CORRECTION_COMPLETED]: 'success',
  [DeviationStatus.CLOSING_PENDING]: 'processing',
  [DeviationStatus.CLOSED]: 'success',
  [DeviationStatus.REJECTED]: 'error',
};

export const DeviationLevelColors: Record<DeviationLevel, string> = {
  [DeviationLevel.CRITICAL]: 'red',
  [DeviationLevel.MAJOR]: 'orange',
  [DeviationLevel.MINOR]: 'blue',
};

// ============ 调查状态标签映射 ============
export const InvestigationStatusLabels: Record<InvestigationStatus, string> = {
  [InvestigationStatus.PENDING]: '待调查',
  [InvestigationStatus.IN_PROGRESS]: '调查中',
  [InvestigationStatus.COMPLETED]: '已完成',
};

// 小写别名
export const investigationStatusLabels: Record<string, string> = {
  pending: '待调查',
  in_progress: '调查中',
  completed: '已完成',
};

// ============ 整改状态标签映射 ============
export const CorrectionStatusLabels: Record<CorrectionStatus, string> = {
  [CorrectionStatus.PENDING]: '待整改',
  [CorrectionStatus.IN_PROGRESS]: '整改中',
  [CorrectionStatus.COMPLETED]: '已完成',
};

// 小写别名
export const correctionStatusLabels: Record<string, string> = {
  pending: '待整改',
  in_progress: '整改中',
  completed: '已完成',
};

// ============ 状态颜色获取函数 ============
export const getStatusColor = (status: string): string => {
  const statusColors: Record<string, string> = {
    draft: 'default',
    submitted: 'processing',
    admin_approved: 'processing',
    qa_approved: 'processing',
    quality_approved: 'processing',
    active: 'warning',
    investigating: 'warning',
    investigation_completed: 'success',
    correction_pending: 'warning',
    correction_in_progress: 'warning',
    correction_completed: 'success',
    closing_pending: 'processing',
    closed: 'success',
    rejected: 'error',
  };
  return statusColors[status] || 'default';
};

// ============ 简化的标签映射（用于 Select options） ============
export const deviationTypeLabels: Record<string, string> = {
  ipc_defect: '过程控制（IPC）缺陷',
  foreign_object: '外来异物（有形）',
  calibration_maintenance: '校验/预防维修',
  mixup: '混淆',
  material_quality_defect: '物料质量缺陷',
  personnel_error: '人员失误',
  oos_result: '超标检验结果',
  documentation_defect: '文件记录缺陷',
  equipment_failure: '设备故障/过程中断',
  environment: '环境',
  other: '其它',
};

export const deviationLevelLabels: Record<string, string> = {
  critical: '重大',
  major: '主要',
  minor: '次要',
};

export const deviationStatusLabels: Record<string, string> = {
  draft: '草稿',
  submitted: '已提交',
  admin_approved: '部门已审核',
  qa_approved: 'QA已审核',
  quality_approved: '质量已审核',
  active: '已启用',
  investigating: '调查中',
  investigation_completed: '调查完成',
  correction_pending: '待整改',
  correction_in_progress: '整改中',
  correction_completed: '整改完成',
  closing_pending: '待关闭',
  closed: '已关闭',
  rejected: '已驳回',
};