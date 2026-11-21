'use client'

import { useQueries } from '@tanstack/react-query'
import { Skeleton } from 'antd'
import { DepartmentContactPage } from '@/components/quality'
import {
  fetchDepartmentContacts,
  fetchDeviationNotifyConfig,
  fetchDeviationStatistics,
} from '@/lib/api/client/quality'

/**
 * 「部门联系人配置」嵌入模块配置页签（TC-011）。
 *
 * 旧页面是 Server Component（一次性 allSettled 多个接口）；页签是客户端渲染，
 * 这里用 React Query 并行拉同一批数据，口径与旧页保持一致：
 * - 部门名仍是唯一关联键（不改成部门 id），新建时从组织树选择；
 * - 台账部门分布用于提示「有偏差但没配置联系人」的部门。
 */
export default function QualityDepartmentContactsSettings() {
  const [contactsQuery, notifyQuery, statsQuery] = useQueries({
    queries: [
      { queryKey: ['quality-department-contacts'], queryFn: () => fetchDepartmentContacts() },
      { queryKey: ['quality-deviation-notify'], queryFn: fetchDeviationNotifyConfig },
      { queryKey: ['quality-deviation-statistics'], queryFn: fetchDeviationStatistics },
    ],
  })

  const loading = contactsQuery.isLoading || notifyQuery.isLoading || statsQuery.isLoading

  if (loading) {
    return <Skeleton active paragraph={{ rows: 8 }} />
  }

  const contacts = contactsQuery.data?.items ?? []
  const notifySettings = notifyQuery.data ?? null
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
      notifySettings={notifySettings}
      loadError={loadError}
      unconfiguredDepartments={unconfiguredDepartments}
    />
  )
}