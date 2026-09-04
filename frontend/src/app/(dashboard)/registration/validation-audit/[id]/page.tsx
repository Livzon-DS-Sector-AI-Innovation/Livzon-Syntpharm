import { notFound } from 'next/navigation'
import {
  fetchTaskByIdServer,
  fetchFilesServer,
  fetchIssuesServer,
  fetchReportServer,
} from '@/actions/validation-audit'
import type { ValidationAuditTask, ValidationAuditFileListItem, ValidationAuditIssue, ValidationAuditReport } from '@/types/validation-audit'
import { ValidationAuditDetailClient } from '@/components/registration'

export const dynamic = 'force-dynamic'

export default async function ValidationAuditDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const taskRes = await fetchTaskByIdServer(id)
  if (!taskRes?.data) {
    notFound()
  }

  const [filesRes, issuesRes, reportRes] = await Promise.all([
    fetchFilesServer(id),
    fetchIssuesServer(id),
    fetchReportServer(id),
  ])

  return (
    <ValidationAuditDetailClient
      task={(taskRes?.data as any) as ValidationAuditTask}
      initialFiles={((filesRes?.data || []) as any) as ValidationAuditFileListItem[]}
      initialIssues={((issuesRes?.data || []) as any) as ValidationAuditIssue[]}
      initialReport={((reportRes?.data || null) as any) as ValidationAuditReport | null}
    />
  )
}
