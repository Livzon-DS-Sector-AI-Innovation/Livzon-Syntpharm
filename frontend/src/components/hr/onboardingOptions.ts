export const POSITION_LEVEL_OPTIONS = [
  '员工级',
  '主管级',
  '经理级',
  '总监级',
  '副总经理级',
  '总经理级',
]

export const PERSONNEL_IDENTITY_OPTIONS = ['正式工', '实习生', '返聘人员']

export const JOIN_CATEGORY_OPTIONS = ['社招', '校招', '猎头推荐', '内部推荐', '集团内部调动', '事业部内部调动']

export const EDUCATION_OPTIONS = ['博士', '硕士', '本科', '大专', '大专以下']

export const GENDER_OPTIONS = ['男', '女']

export const GROUP_CLASSIFICATION_OPTIONS = [
  '职能管理',
  '生产一线',
  '生产一线：管理',
  '生产辅助',
  '研发一线',
  '技术一线',
  '后勤服务',
]

export function toOptions(values: readonly string[]) {
  return values.map((value) => ({ value, label: value }))
}

export const AVATAR_COLORS = ['#1e88e5', '#8a6a00', '#cf4a00', '#7a0000', '#5645d4', '#1a7f68']

export function avatarColor(name: string): string {
  let hash = 0
  for (const char of name) hash = (hash * 31 + char.charCodeAt(0)) % 997
  return AVATAR_COLORS[hash % AVATAR_COLORS.length]
}
