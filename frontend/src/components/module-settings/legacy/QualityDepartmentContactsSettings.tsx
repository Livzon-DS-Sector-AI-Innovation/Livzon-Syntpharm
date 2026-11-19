'use client'

import { useQueries } from '@tanstack/react-query'
import { Skeleton } from 'antd'
import { DepartmentContactPage } from '@/components/quality'
import {
  fetchDepartmentContacts,
  fetchDepartmentMemberOptions,
  fetchDeviationNotifyConfig,
  fetchDeviationStatistics,
  fetchLedgerDepartmentOptions,
} from '@/lib/api/client/quality'

/**
 * 「部门联系人配置」嵌入模块配置页签（TC-011）。
 *
 * 旧页面是 Server Component（一次性 allSettled 五个接口）；页签是客户端渲染，
 * 这里用 React Query 并行拉同一批数据，口径与旧页保持一致：
 * - 部门名仍是唯一关联键（不改成部门 id）；
 * - 组织部门候选用于「同名建议」；
 * - 台账部门分布用于提示「有偏差但没配置联系人」的部门。
 */
export default function QualityDepartmentContactsSettings() {
  const [contactsQuery, memberQuery, notifyQuery, orgQuery, statsQuery] = useQueries({
    queries: [
      { queryKey: ['quality-department-contacts'], queryFn: () => fetchDepartmentContacts() },
      { queryKey: ['quality-department-members'], queryFn: () => fetchDepartmentMemberOptions() },
      { queryKey: ['quality-deviation-notify'], queryFn: fetchDeviationNotifyConfig },
      { queryKey: ['quality-ledger-departments'], queryFn: fetchLedgerDepartmentOptions },
      { queryKey: ['quality-deviation-statistics'], queryFn: fetchDeviationStatistics },
    ],
  })

  const loading =
    contactsQuery.isLoading || memberQuery.isLoading || notifyQuery.isLoading || orgQuery.isLoading || statsQuery.isLoading

  if (loading) {
    return <Skeleton active paragraph={{ rows: 8 }} />
  }

  const contacts = contactsQuery.data?.items ?? []
  const memberOptions = memberQuery.data ?? []
  const notifySettings = notifyQuery.data ?? null
  const departmentSuggestions = (orgQuery.data ?? []).map((item) => item.value)
  const ledgerDepartments = (statsQuery.data?.department_distribution ?? []).map((item) => item.name)

  const configured = new Set(contacts.map((contact) => contact.department.trim()))
  const unconfiguredDepartments = [...new Set(ledgerDepartments.map((name) => name.trim()))]
    .filter((name) => name.length > 0 && !configured.has(name))
    .sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'))

  const loadError = contactsQuery.isError
    ? contactsQuery.error instanceof Error
      ? contactsQuery.error.message
      : '联系人数据加载失败'
    : null

  return (
    <DepartmentContactPage
      embedded
      contacts={contacts}
      memberOptions={memberOptions}
      notifySettings={notifySettings}
      loadError={loadError}
      departmentSuggestions={departmentSuggestions}
      unconfiguredDepartments={unconfiguredDepartments}
    />
  )
}