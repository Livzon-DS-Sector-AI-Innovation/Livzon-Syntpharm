import { redirect } from 'next/navigation'

/** 「部门联系人配置」已并入「模块配置 · 部门联系人配置」页签（TC-011），旧地址只做重定向。 */
export default function Page() {
  redirect('/quality/settings?tab=department-contacts')
}