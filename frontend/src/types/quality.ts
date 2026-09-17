import type { components } from '@/types/generated/schema'

// Quality management types (from shared/api.interface.ts)

// ============ Deviation Types ============
export type DeviationLevel = 'minor' | 'moderate' | 'major';
export type DeviationStatus =
  | 'draft'
  | 'pending_ai_analysis'
  | 'pending_investigation'
  | 'pending_dept_head_review'
  | 'pending_cross_dept_head_review'
  | 'pending_qa_review'
  | 'pending_qa_head_review'
  | 'pending_quality_head_review'
  | 'pending_final_code'
  | 'returned'
  | 'closed'
  | 'cancelled';

export type ApprovalStep =
  | 'ai_analysis'
  | 'investigation'
  | 'dept_head_review'
  | 'cross_dept_head_review'
  | 'qa_review'
  | 'qa_head_review'
  | 'quality_head_review'
  | 'final_code_input';

export type ReasonCategory = '人员' | '设施/设备' | '产品/物料' | '文件' | '环境' | '其它';

export interface CrossDeptReviewer {
  department: string;
  investigators: string[];
}

export interface AiAnalysis {
  structured_deviation_description: string;
  preliminary_cause_analysis: string;
  risk_assessment: string;
  capa_suggestions: string;
}

export interface InvestigationRecord {
  content?: string;
  nonconformityDescription?: string;
  rootCauseAnalysis?: string;
  riskAssessment?: string;
  urgentMeasures?: string;
  author: string;
  department?: string;
  createTime: string;
  attachments?: string[];
  isModified?: boolean;
  modifyTime?: string;
  capaProposals?: any[];
}

export interface ReviewOpinion {
  content: string;
  author: string;
  step: ApprovalStep | string;
  result: 'approved' | 'rejected' | 'resubmitted';
  createTime: string;
}

export interface DeviationListItem {
  id: string;
  deviation_code: string;
  final_code: string | null;
  title: string;
  department: string | null;
  discovery_date: string | null;
  status: DeviationStatus;
  level: DeviationLevel | null;
  root_cause_category: ReasonCategory | null;
  reporter_id: string | null;
  handler: string | null;
  status_updated_at: string | null;
  returned_step: ApprovalStep | null;
  created_at: string;
}

export interface DeviationDetail {
  id: string;
  deviation_code: string;
  final_code: string | null;
  title: string;
  department: string | null;
  discovery_date: string | null;
  discovery_time: string | null;
  discovery_location: string | null;
  status: DeviationStatus;
  level: DeviationLevel | null;
  root_cause_category: ReasonCategory | null;
  description: string | null;
  immediate_actions: string | null;
  reporter_id: string | null;
  handler: string | null;
  discoverer: string | null;
  ai_analysis: AiAnalysis | null;
  investigation_records: InvestigationRecord[] | null;
  review_opinions: ReviewOpinion[] | null;
  attachments: string[] | null;
  needs_cross_dept_review: boolean | null;
  cross_dept_reviewers: CrossDeptReviewer[] | null;
  affected_items: string | null;
  batch_number: string | null;
  returned_step: ApprovalStep | null;
  status_updated_at: string | null;
  report_content: string | null;
  report_versions: any[] | null;
  created_at: string;
  updated_at: string;
}

// ============ CAPA Types ============
export type CapaWorkflowStatus =
  | 'draft'
  | 'part_a'
  | 'part_b'
  | 'part_c'
  | 'pending_dept_head_confirm'
  | 'pending_qa_review'
  | 'pending_q_head_approval'
  | 'executing'
  | 'pending_evaluation'
  | 'submitted'
  | 'under_execution'
  | 'evaluation'
  | 'closed'
  | 'returned'
  | 'cancelled';

export type CapaSource = 'deviation' | 'audit' | 'customer_complaint' | 'internal_inspection';
export type CapaCategory = 'A' | 'B' | 'C';

export interface CapaItem {
  id: string;
  description: string;
  content?: string;
  responsible_user_id: string;
  responsible_person?: string;
  due_date: string;
  deadline?: string;
  status: string;
  [key: string]: any;
}

export interface DeptHeadConfirmation {
  department: string;
  deptHeadUserId: string;
  result: string;
  opinion: string;
  confirmTime: string;
}

export interface ExecutionTrack {
  id: string;
  executionStatus: string;
  execution_date?: string;
  execution_notes?: string;
  qaConfirmer?: string;
  qaConfirmDate?: string;
}

export interface CapaListItem {
  id: string;
  capa_code: string;
  final_code: string | null;
  title: string;
  status: CapaWorkflowStatus;
  source: string | null;
  source_code: string | null;
  category: CapaCategory | null;
  root_cause_category: ReasonCategory | null;
  deviation_id: string | null;
  expected_completion_date: string | null;
  status_updated_at: string | null;
  created_at: string;
}

export interface CapaDetail {
  id: string;
  capa_code: string;
  final_code: string | null;
  title: string;
  status: CapaWorkflowStatus;
  deviation_id: string | null;
  source: string | null;
  source_code: string | null;
  category: CapaCategory | null;
  root_cause_category: ReasonCategory | null;
  non_conformity_description: string | null;
  root_cause_analysis: string | null;
  capa_content: string | null;
  capa_items: CapaItem[] | null;
  executors: string[] | null;
  expected_completion_date: string | null;
  qa_reviewer_id: string | null;
  qa_review_opinion: string | null;
  qa_review_time: string | null;
  q_head_approver_id: string | null;
  q_head_approval_opinion: string | null;
  q_head_approval_time: string | null;
  execution_status: string | null;
  execution_tracks: ExecutionTrack[] | null;
  dept_head_confirmations: DeptHeadConfirmation[] | null;
  evaluation_result: string | null;
  evaluation_target: string | null;
  evaluation_deadline: string | null;
  evaluation_confirmer_id: string | null;
  evaluation_confirm_date: string | null;
  closure_date: string | null;
  closure_remark: string | null;
  report_content: string | null;
  report_versions: any[] | null;
  returned_step: string | null;
  status_updated_at: string | null;
  reporter: string | null;
  reason_category: string | null;
  created_at: string;
  updated_at: string;
}

// ============ Department Contact Types ============
export interface DepartmentContact {
  id: string;
  department: string;
  dept_head_id: string | null;
  qa_staff_ids: string[] | null;
  gmp_staff_ids: string[] | null;
  production_head_id: string | null;
  quality_head_id: string | null;
  additional_contacts: string[] | null;
  is_production_workshop: boolean | null;
  created_at: string;
  updated_at: string;
}

// ============ Department Weekly Confirmation Types ============
export type ProductionStatus = 'production' | 'stopped';
export type DeviationConfirmationStatus = 'submitted' | 'unsubmitted';

export interface DepartmentWeeklyConfirmation {
  id: string;
  department: string;
  week_key: string;
  production_status: ProductionStatus;
  deviation_status: DeviationConfirmationStatus;
  confirmed_by_id: string | null;
  confirmed_at: string | null;
  created_at: string;
  updated_at: string;
}

// ============ Filter Types ============
export interface DeviationFilters {
  status?: DeviationStatus | '';
  level?: DeviationLevel | '';
  department?: string | '';
  keyword?: string;
  page?: number;
  page_size?: number;
}

export interface CapaFilters {
  status?: CapaWorkflowStatus | '';
  source?: CapaSource | '';
  category?: CapaCategory | '';
  keyword?: string;
  page?: number;
  page_size?: number;
}

// ============ List Response Types ============
export interface DeviationListResponse {
  items: DeviationListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface CapaListResponse {
  items: CapaListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface DepartmentContactListResponse {
  items: DepartmentContact[];
  total: number;
  page: number;
  page_size: number;
}

// ============ Create/Update Request Types ============
export interface CreateDeviationRequest {
  title: string;
  description: string;
  deviation_type: string;
  deviation_level: string;
  [key: string]: any;
}

export interface UpdateDeviationRequest {
  [key: string]: any;
}

export interface CreateCapaRequest {
  [key: string]: any;
}

export interface UpdateCapaRequest {
  [key: string]: any;
}

export interface CreateDepartmentContactRequest {
  department: string;
  dept_head_id?: string | null;
  qa_staff_ids?: string[] | null;
  gmp_staff_ids?: string[] | null;
  production_head_id?: string | null;
  quality_head_id?: string | null;
}

export interface UpdateDepartmentContactRequest {
  dept_head_id?: string | null;
  qa_staff_ids?: string[] | null;
  gmp_staff_ids?: string[] | null;
  production_head_id?: string | null;
  quality_head_id?: string | null;
  additional_contacts?: string[] | null;
  is_production_workshop?: boolean | null;
}


// ============ File Attachment Types ============
export interface FileAttachmentInfo {
  bucketId?: string;
  fileName?: string;
  filePath?: string;
  downloadUrl?: string;
}

// ============ Report Version Types ============
export interface ReportVersion {
  content: string;
  editor: string;
  editTime: string;
  changeSummary?: string;
}

// ============ Attachment Review Types ============
export interface AttachmentReview {
  id: string;
  deviation_id?: string;
  capa_id?: string;
  attachment_url: string;
  reviewer_id: string;
  review_time?: string;
  content: string;
  status: string;
  created_at: string;
  updated_at: string;
}

// ============ LC Report Types ============
export interface ImpurityResult {
  name: string
  value: number
  unit: string
  limit: number | string
  first_percent?: number
  second_percent?: number
  is_pass?: boolean
  [key: string]: unknown
}

export interface CalculatedResult {
  name: string
  value: number
  unit: string
  formula: string
  first_percent?: number
  rounded_first?: number
  rounded_second?: number
  second_percent?: number
  limit?: number | string
  is_pass?: boolean
  [key: string]: unknown
}

export interface LcReportData {
  sample_id: string
  sample_name: string
  product_name?: string
  batch_no: string
  batch_number?: string
  standard_type?: string
  form_id?: string
  test_date: string
  tester: string
  impurities: ImpurityResult[]
  impurity_results?: ImpurityResult[]
  calculated: CalculatedResult[]
  conclusion: string
  all_pass?: boolean
  has_oot?: boolean
  total_peak_area_a_first?: number
  total_peak_area_a_second?: number
  main_peak_area_a_first?: number
  main_peak_area_a_second?: number
  main_peak_area_b_first?: number
  main_peak_area_b_second?: number
  total_impurity_area_first?: number
  total_impurity_area_second?: number
  vancomycin_b?: CalculatedResult
  total_impurities?: CalculatedResult
  standards?: Record<string, unknown>[]
  raw_data?: Record<string, unknown>
  [key: string]: unknown
}

export interface UploadLcResponse {
  success: boolean
  report?: LcReportData
  message: string
}
// quality module TypeScript types

export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
  meta?: {
    page?: number
    page_size?: number
    total?: number
  }
}

// ============ Enums ============

export enum MaterialCategory {
  RAW_MATERIAL = 'raw_material',       // 原料
  EXCIPIENT = 'excipient',            // 辅料
  PACKAGING_MATERIAL = 'packaging_material',  // 包装材料
  INTERMEDIATE = 'intermediate',      // 中间体
  FINISHED_PRODUCT = 'finished_product',    // 原料药成品
}

export enum Pharmacopeia {
  CHP = 'ChP',       // 中国药典
  USP = 'USP',       // 美国药典
  EP = 'EP',         // 欧洲药典
  BP = 'BP',         // 英国药典
  INTERNAL = 'internal',  // 企业内控
}

export enum StandardStatus {
  DRAFT = 'draft',           // 草稿
  TECH_REVIEW = 'tech_review',     // 技术部门审核
  QA_REVIEW = 'qa_review',         // QA审核
  APPROVED = 'approved',           // 已批准
  EFFECTIVE = 'effective',         // 已生效
  OBSOLETE = 'obsolete',           // 已作废
  REJECTED = 'rejected',           // 已驳回
}

export enum LimitType {
  UPPER_LIMIT = 'upper_limit',     // 上限
  LOWER_LIMIT = 'lower_limit',     // 下限
  RANGE = 'range',                 // 区间
  NOT_DETECTABLE = 'not_detectable', // 不得检出
}

export enum ItemCategory {
  PHYSICAL_CHEMICAL = 'physical_chemical',   // 理化
  RELATED_SUBSTANCES = 'related_substances',  // 有关物质
  RESIDUAL_SOLVENTS = 'residual_solvents',    // 残留溶剂
  MICROBIAL = 'microbial',                    // 微生物
}

export const MATERIAL_CATEGORY_OPTIONS = [
  { value: MaterialCategory.RAW_MATERIAL, label: '原料' },
  { value: MaterialCategory.EXCIPIENT, label: '辅料' },
  { value: MaterialCategory.PACKAGING_MATERIAL, label: '包装材料' },
  { value: MaterialCategory.INTERMEDIATE, label: '中间体' },
  { value: MaterialCategory.FINISHED_PRODUCT, label: '原料药成品' },
]

export const PHARMACOPEIA_OPTIONS = [
  { value: Pharmacopeia.CHP, label: 'ChP 中国药典' },
  { value: Pharmacopeia.USP, label: 'USP 美国药典' },
  { value: Pharmacopeia.EP, label: 'EP 欧洲药典' },
  { value: Pharmacopeia.BP, label: 'BP 英国药典' },
  { value: Pharmacopeia.INTERNAL, label: '企业内控' },
]

export const STANDARD_STATUS_OPTIONS = [
  { value: StandardStatus.DRAFT, label: '草稿', color: 'default' },
  { value: StandardStatus.TECH_REVIEW, label: '技术部门审核', color: 'processing' },
  { value: StandardStatus.QA_REVIEW, label: 'QA审核', color: 'processing' },
  { value: StandardStatus.APPROVED, label: '已批准', color: 'blue' },
  { value: StandardStatus.EFFECTIVE, label: '已生效', color: 'success' },
  { value: StandardStatus.OBSOLETE, label: '已作废', color: 'warning' },
  { value: StandardStatus.REJECTED, label: '已驳回', color: 'error' },
]

export const LIMIT_TYPE_OPTIONS = [
  { value: LimitType.UPPER_LIMIT, label: '上限' },
  { value: LimitType.LOWER_LIMIT, label: '下限' },
  { value: LimitType.RANGE, label: '区间' },
  { value: LimitType.NOT_DETECTABLE, label: '不得检出' },
]

export const ITEM_CATEGORY_OPTIONS = [
  { value: ItemCategory.PHYSICAL_CHEMICAL, label: '理化' },
  { value: ItemCategory.RELATED_SUBSTANCES, label: '有关物质' },
  { value: ItemCategory.RESIDUAL_SOLVENTS, label: '残留溶剂' },
  { value: ItemCategory.MICROBIAL, label: '微生物' },
]

// ============ InspectionStandard Types ============

export interface InspectionStandardItem {
  id: string
  standard_id: string
  item_no: number
  item_name: string
  test_method?: string
  instrument_code?: string
  reference_materials?: string
  limit_type: LimitType
  limit_value?: string
  item_category?: ItemCategory
  is_critical: boolean
  notes?: string
  created_at: string
  updated_at: string
}

export interface InspectionStandard {
  id: string
  standard_no: string
  material_code: string
  material_name?: string
  cas_no?: string
  material_category: MaterialCategory
  pharmacopeia?: Pharmacopeia
  version: string
  status: StandardStatus
  effective_date?: string
  obsolete_date?: string
  is_obsolete: boolean
  obsolete_reason?: string
  sop_no?: string
  attachment_urls?: string
  notes?: string
  source_version?: string
  items: InspectionStandardItem[]
  created_at: string
  updated_at: string
}

export interface InspectionStandardFormData {
  material_code: string
  material_name?: string
  cas_no?: string
  material_category: MaterialCategory
  pharmacopeia?: Pharmacopeia
  version?: string
  effective_date?: string
  obsolete_date?: string
  sop_no?: string
  attachment_urls?: string
  notes?: string
  items?: InspectionStandardItemFormData[]
}

export interface InspectionStandardItemFormData {
  item_no: number
  item_name: string
  test_method?: string
  instrument_code?: string
  reference_materials?: string
  limit_type: LimitType
  limit_value?: string
  item_category?: ItemCategory
  is_critical?: boolean
  notes?: string
}

export interface StandardCopyData {
  source_id: string
  new_version: string
}

export interface ObsoleteData {
  obsolete_reason: string
}

// ============ ApprovalRecord Types ============

export interface ApprovalRecord {
  id: string
  standard_id: string
  approval_level: number
  approval_status: string
  approver_role?: string
  approver_id?: string
  approver_name?: string
  approved_at?: string
  comments?: string
  created_at: string
  updated_at: string
}

// ============ Query Parameters ============

export interface StandardQueryParams {
  page?: number
  page_size?: number
  status?: StandardStatus
  material_code?: string
  material_name?: string
  material_category?: MaterialCategory
  pharmacopeia?: Pharmacopeia
  version?: string
  is_effective?: boolean
}

// ============ AI 交互日志 ============

export interface AiLogItem {
  id: string
  bill_no: string | null
  operate_type: string
  operator: string
  system_prompt: string | null
  user_input: string | null
  ai_response: string | null
  error_message: string | null
  tokens_used: number | null
  latency_ms: number | null
  created_at: string
}

export interface AiLogListResponse {
  items: AiLogItem[]
  total: number
  page: number
  page_size: number
}

export interface AiLogFilter {
  operate_type?: string
  operator?: string
  start_date?: string
  end_date?: string
  keyword?: string
}