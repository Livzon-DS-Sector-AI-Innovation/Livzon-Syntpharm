/**
 * 注册项目状态元数据（注册项目页 / 申报进度查询页共用）
 *
 * 配色以注册项目页原型为准；两页引用同一份，避免「审评中」一边蓝一边橙的漂移。
 * 受理后状态（postAcceptance）唯一维护入口为申报进度查询，注册项目页只读并带「· 同步」标。
 */

import ui from './registration-ui.module.css'

export interface ProjectStatusMeta {
  /** 中文名 */
  label: string
  /** 标签类名，来自 registration-ui.module.css */
  tagClass: string
  /** 是否为受理后状态（由申报进度查询侧同步维护） */
  postAcceptance: boolean
}

export const PROJECT_STATUS_META: Record<string, ProjectStatusMeta> = {
  draft: { label: '草稿', tagClass: ui.tagPlain, postAcceptance: false },
  preparing: { label: '准备中', tagClass: ui.tagInfo, postAcceptance: false },
  submitted: { label: '已申报', tagClass: ui.tagBrand, postAcceptance: false },
  accepted: { label: '已受理', tagClass: ui.tagInfo, postAcceptance: true },
  under_review: { label: '审评中', tagClass: ui.tagInfo, postAcceptance: true },
  supplementary: { label: '发补中', tagClass: ui.tagWarn, postAcceptance: true },
  approved: { label: '已获批', tagClass: ui.tagOk, postAcceptance: true },
  withdrawn: { label: '已撤回', tagClass: ui.tagRisk, postAcceptance: true },
  terminated: { label: '已终止', tagClass: ui.tagPlain, postAcceptance: true },
}

/** 状态元数据；未知状态原样展示为灰色标签 */
export function projectStatusMeta(status: string): ProjectStatusMeta {
  return PROJECT_STATUS_META[status] ?? {
    label: status || '未知',
    tagClass: ui.tagPlain,
    postAcceptance: false,
  }
}

/** 是否为受理后状态（只读 + 同步徽标） */
export function isPostAcceptance(status: string): boolean {
  return PROJECT_STATUS_META[status]?.postAcceptance ?? false
}

/** 状态筛选下拉选项（顺序与状态机一致） */
export const PROJECT_STATUS_OPTIONS = Object.entries(PROJECT_STATUS_META).map(([value, meta]) => ({
  value,
  label: meta.label,
}))
