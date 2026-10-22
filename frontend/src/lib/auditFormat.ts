/**
 * 操作记录的可读化格式化。
 *
 * 后端 `audit.logs` 的 old_value / new_value 是 JSON 对象，直接渲染成 JSON 大括号
 * 既难读又占空间。这里做两件事：
 * 1. 字段名与常见枚举值转中文（未知字段保留原名，不隐藏信息）；
 * 2. 只保留真正发生变化的字段，按「字段 / 改前 / 改后」输出。
 */

export interface AuditValueRecord {
  action: string
  old_value?: Record<string, unknown> | null
  new_value?: Record<string, unknown> | null
}

export interface AuditDiffRow {
  field: string
  label: string
  before: string
  after: string
}

const FIELD_LABELS: Record<string, string> = {
  // 账号
  username: '账号',
  name: '姓名',
  en_name: '英文名',
  status: '状态',
  email: '邮箱',
  mobile: '手机号',
  employee_no: '工号',
  department: '部门',
  position: '职位',
  auth_source: '登录来源',
  password_generated: '自动生成密码',
  random: '随机生成',
  is_deleted: '是否删除',
  account_deleted: '连带删除账号',
  revoked_grants: '清空授权数',
  batch: '批量操作',
  // 角色 / 授权
  code: '编码',
  description: '描述',
  permission_codes: '权限',
  user_id: '用户',
  role_id: '角色',
  role_code: '角色',
  scope_type: '数据范围',
  scope_dept_codes: '部门范围',
  granted_by: '授权人',
  // 菜单
  items: '菜单项',
  custom: '自定义菜单',
}

const VALUE_LABELS: Record<string, string> = {
  active: '启用',
  disabled: '禁用',
  local: '本地账号',
  feishu: '飞书',
  all: '全部',
  department: '指定部门',
  department_and_children: '部门及下级',
  user: '用户',
  role: '角色',
  grant: '授权',
  menu: '菜单',
}

/** 口令类动作：内容一律不展示。 */
const PASSWORD_ACTIONS = new Set(['user.reset_password', 'user.change_password'])

function formatScalar(value: unknown): string {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (typeof value === 'number') return String(value)
  if (typeof value === 'string') return VALUE_LABELS[value] ?? value
  if (Array.isArray(value)) {
    return value.length ? value.map((item) => formatScalar(item)).join('、') : '无'
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    if (!entries.length) return '无'
    // 嵌套对象扁平化为「字段：值；…」，避免再次出现 JSON 花括号
    return entries.map(([key, item]) => `${FIELD_LABELS[key] ?? key}：${formatScalar(item)}`).join('；')
  }
  return String(value)
}

/** 逐字段比较 old_value / new_value，只返回发生变化的字段。 */
export function auditDiffRows(record: AuditValueRecord): AuditDiffRow[] {
  if (PASSWORD_ACTIONS.has(record.action)) return []

  const before = record.old_value ?? {}
  const after = record.new_value ?? {}
  const fields = Array.from(new Set([...Object.keys(before), ...Object.keys(after)]))
  const rows: AuditDiffRow[] = []

  for (const field of fields) {
    const hasBefore = Object.prototype.hasOwnProperty.call(before, field)
    const hasAfter = Object.prototype.hasOwnProperty.call(after, field)
    const beforeText = formatScalar(before[field])
    const afterText = formatScalar(after[field])
    if (hasBefore && hasAfter && beforeText === afterText) continue
    rows.push({
      field,
      label: FIELD_LABELS[field] ?? field,
      before: hasBefore ? beforeText : '-',
      after: hasAfter ? afterText : '-',
    })
  }

  return rows
}

/** 列表「变更内容」列的摘要文字，如 `状态：启用 → 禁用；姓名：张三 → 李四`。 */
export function auditDiffSummary(record: AuditValueRecord, maxParts = 3): string {
  if (PASSWORD_ACTIONS.has(record.action)) return '口令已更新（内容不展示）'

  const rows = auditDiffRows(record)
  if (!rows.length) return '-'

  const parts = rows.slice(0, maxParts).map((row) => {
    // 新建类记录只有改后值，不必显示「- →」
    if (row.before === '-') return `${row.label}：${row.after}`
    return `${row.label}：${row.before} → ${row.after}`
  })
  return rows.length > maxParts ? `${parts.join('；')} 等 ${rows.length} 项` : parts.join('；')
}
