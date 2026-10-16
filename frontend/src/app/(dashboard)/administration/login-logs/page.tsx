import { redirect } from 'next/navigation'

/**
 * 历史地址：登录记录已迁到「系统管理 → 登录记录」。
 * 保留此跳转，避免旧书签 / 外部链接 404。
 */
export default function LegacyLoginLogsPage() {
  redirect('/settings/login-logs')
}
