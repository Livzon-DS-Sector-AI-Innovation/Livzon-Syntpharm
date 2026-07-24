export interface HazardRevisionRecord {
  id: string
  regulation_id: string
  revision_type: string
  description: string | null
  status: string
  revised_by: string | null
  revised_at: string | null
  approved_by: string | null
  approved_at: string | null
  document_id: string | null
  archive_id: string | null
  created_at: string
  updated_at: string
}

export interface HazardRevisionRecordFormData {
  regulation_id: string
  revision_type: string
  description?: string
  status?: string
}

export interface HazardRevisionArchive {
  id: string
  name: string
  description: string | null
  regulation_id: string
  archive_type: string
  file_url: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface HazardRevisionArchiveFormData {
  name: string
  regulation_id: string
  archive_type: string
  description?: string
  file_url?: string
  status?: string
}

export const IDENTIFICATION_TYPE_OPTIONS = [
  { value: 'jha', label: 'JHA (作业危害分析)' },
  { value: 'scl', label: 'SCL (安全检查表)' },
  { value: 'lopa', label: 'LOPA (保护层分析)' },
  { value: 'hazop', label: 'HAZOP (危险与可操作性分析)' },
  { value: 'fmea', label: 'FMEA (失效模式与影响分析)' },
  { value: 'eta', label: 'ETA (事件树分析)' },
  { value: 'fta', label: 'FTA (故障树分析)' },
  { value: 'pha', label: 'PHA (预先危险性分析)' },
  { value: 'other', label: '其他' },
]

export const ARCHIVE_STATUS_OPTIONS = [
  { value: 'active', label: '有效', color: 'green' },
  { value: 'archived', label: '已归档', color: 'default' },
  { value: 'expired', label: '已过期', color: 'red' },
  { value: 'draft', label: '草稿', color: 'default' },
]
