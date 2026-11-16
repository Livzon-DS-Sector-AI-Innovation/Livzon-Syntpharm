import type { Metadata } from 'next'
import { DepartmentContactPage } from '@/components/quality'
import {
  fetchDepartmentContacts,
  fetchDeviationDepartmentOptions,
  fetchDeviationLedgerStatistics,
  fetchDeviationMemberOptions,
  fetchDeviationNotifySettings,
} from '@/lib/api/server/quality'
import type {
  DepartmentContact,
  DepartmentMemberOption,
  DeviationNotifySettings,
} from '@/types/quality'

// 联系人 / 通知配置随运营变化，禁用静态预渲染
export const dynamic = 'force-dynamic'

export const metadata: Metadata = { title: '部门联系人配置' }

export default async function DepartmentContactsPage() {
  // 五块数据独立降级：任一失败只影响对应区域
  const [contactsResult, memberResult, notifyResult, statisticsResult, orgDepartmentResult] = await Promise.allSettled([
    fetchDepartmentContacts(),
    fetchDeviationMemberOptions(),
    fetchDeviationNotifySettings(),
    fetchDeviationLedgerStatistics(),
    fetchDeviationDepartmentOptions(),
  ])

  let loadError: string | null = null
  if (contactsResult.status === 'rejected') {
    console.error('部门联系人加载失败', contactsResult.reason)
    loadError =
      contactsResult.reason instanceof Error ? contactsResult.reason.message : '未知错误，请稍后重试'
  }
  if (memberResult.status === 'rejected') {
    console.error('人员候选加载失败', memberResult.reason)
  }
  if (notifyResult.status === 'rejected') {
    console.error('通知设置加载失败', notifyResult.reason)
  }
  if (statisticsResult.status === 'rejected') {
    console.error('偏差部门分布加载失败', statisticsResult.reason)
  }
  if (orgDepartmentResult.status === 'rejected') {
    console.error('组织部门候选加载失败', orgDepartmentResult.reason)
  }

  const contacts: DepartmentContact[] =
    contactsResult.status === 'fulfilled' ? contactsResult.value.items : []
  const memberOptions: DepartmentMemberOption[] =
    memberResult.status === 'fulfilled' ? memberResult.value : []
  const notifySettings: DeviationNotifySettings | null =
    notifyResult.status === 'fulfilled' ? notifyResult.value : null

  // 部门名是关联键：建议值取组织部门（与台账部门名同源），避免手输出偏差
  const departmentSuggestions =
    orgDepartmentResult.status === 'fulfilled'
      ? orgDepartmentResult.value.map((item) => item.value)
      : []

  // 台账里出现、但还没有联系人配置的部门：这些单子的节点负责人无法自动指派
  const configured = new Set(contacts.map((contact) => contact.department.trim()))
  const ledgerDepartments =
    statisticsResult.status === 'fulfilled'
      ? (statisticsResult.value.department_distribution ?? []).map((item) => item.name)
      : []
  const unconfiguredDepartments = [...new Set(ledgerDepartments.map((name) => name.trim()))]
    .filter((name) => name.length > 0 && !configured.has(name))
    .sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'))

  return (
    <DepartmentContactPage
      contacts={contacts}
      memberOptions={memberOptions}
      notifySettings={notifySettings}
      loadError={loadError}
      departmentSuggestions={departmentSuggestions}
      unconfiguredDepartments={unconfiguredDepartments}
    />
  )
}