export interface ScheduledTask {
  id: string
  name: string
  description?: string | null
  cron_expression: string
  cron_desc?: string | null
  feishu_chat_id: string
  feishu_chat_name?: string | null
  header_color: string
  is_enabled: boolean
  data_sources: DataSourceItem[]
  card_template: string
  last_run_at?: string | null
  last_run_status?: string | null
  next_run_at?: string | null
  created_at: string
  updated_at: string
}

export interface ScheduledTaskFormData {
  name: string
  description?: string
  cron_expression: string
  cron_desc?: string
  feishu_chat_id: string
  feishu_chat_name?: string
  header_color?: HeaderColor
  is_enabled?: boolean
  data_sources?: DataSourceItem[]
  card_template?: string
}

export interface DataSourceItem {
  key: string
  label: string
  enabled: boolean
}

export interface DataSourceOption {
  key: string
  label: string
  default_enabled: boolean
}

export interface FeishuChat {
  chat_id: string
  name: string
}

export type HeaderColor = 'blue' | 'green' | 'red' | 'orange' | 'purple' | 'cyan' | 'yellow' | 'turquoise' | 'carmine' | 'indigo' | 'grey'

export interface CardPreviewRequest {
  data_sources: DataSourceItem[]
  card_template: string
  header_color: HeaderColor
}

export const HEADER_COLOR_OPTIONS = [
  { value: 'blue', label: '蓝色', color: '#3370ff' },
  { value: 'green', label: '绿色', color: '#34a853' },
  { value: 'red', label: '红色', color: '#e03131' },
  { value: 'orange', label: '橙色', color: '#dd5b00' },
  { value: 'purple', label: '紫色', color: '#5645d4' },
  { value: 'cyan', label: '青色', color: '#0891b2' },
  { value: 'yellow', label: '黄色', color: '#d4b106' },
  { value: 'turquoise', label: '青绿色', color: '#0d9488' },
  { value: 'carmine', label: '胭脂红', color: '#c92a2a' },
  { value: 'indigo', label: '靛蓝色', color: '#4c51bf' },
  { value: 'grey', label: '灰色', color: '#787671' },
]

export const CRON_PRESETS = [
  { value: '0 9 * * *', label: '每天早上9点', desc: '每天上午9点执行' },
  { value: '0 9 * * 1', label: '每周一早9点', desc: '每周一上午9点执行' },
  { value: '0 9 1 * *', label: '每月1号早9点', desc: '每月1号上午9点执行' },
  { value: '0 9 * * 1-5', label: '工作日早9点', desc: '周一至周五上午9点执行' },
  { value: '0 14 * * *', label: '每天下午2点', desc: '每天下午2点执行' },
  { value: '0 */6 * * *', label: '每6小时', desc: '每6小时执行一次' },
]

export interface ScheduledTaskLog {
  id: string
  task_id: string
  started_at: string
  completed_at?: string | null
  status: string
  duration_ms?: number | null
  error_message?: string | null
  feishu_msg_id?: string | null
  data_snapshot?: Record<string, unknown> | null
}
