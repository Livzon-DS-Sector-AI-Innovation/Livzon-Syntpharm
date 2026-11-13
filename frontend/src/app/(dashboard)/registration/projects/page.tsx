import { Suspense } from 'react'
import { ProjectsPageClient } from '@/components/registration'

export const dynamic = 'force-dynamic'

export default function ProjectsPage() {
  return (
    <Suspense>
      <ProjectsPageClient />
    </Suspense>
  )
}
