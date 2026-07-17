import { RegistrationFilingPage } from '@/components/research'

export const dynamic = 'force-dynamic'

export default async function RdProjectFilingPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <RegistrationFilingPage projectId={id} />
}
