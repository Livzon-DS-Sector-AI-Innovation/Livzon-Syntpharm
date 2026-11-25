import { redirect } from 'next/navigation'

/** 「人员配置」已并入「模块配置 · 人员配置」页签（TC-011），旧地址只做重定向。 */
export default function Page() {
  redirect('/equipment/settings?tab=personnel')
}