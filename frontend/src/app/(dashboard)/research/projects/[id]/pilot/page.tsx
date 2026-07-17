import { PilotStudyPage } from '@/components/research'

export const dynamic = 'force-dynamic'

export default async function RdProjectPilotPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <PilotStudyPage projectId={id} />
}
