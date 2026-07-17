import { getWorkshops } from '@/actions/energy'
import { WorkshopTable } from '@/components/energy/WorkshopTable'

export const dynamic = 'force-dynamic'

export default async function WorkshopsPage() {
  return <WorkshopTable />
}
