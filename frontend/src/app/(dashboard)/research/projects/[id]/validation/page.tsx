import { ProcessValidationPage } from '@/components/research'

export const dynamic = 'force-dynamic'

export default async function RdProjectValidationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <ProcessValidationPage projectId={id} />
}
