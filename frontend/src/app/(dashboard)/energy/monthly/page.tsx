import { getMonthlyRecords } from '@/actions/energy'
import { MonthlyRecordTable } from '@/components/energy/MonthlyRecordTable'

export const dynamic = 'force-dynamic'

export default async function MonthlyPage() {
  return <MonthlyRecordTable />
}
