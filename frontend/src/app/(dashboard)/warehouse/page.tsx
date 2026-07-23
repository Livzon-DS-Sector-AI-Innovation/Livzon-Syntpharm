export const dynamic = 'force-dynamic'

import { redirect } from 'next/navigation'

export default function WarehousePage() {
  redirect('/warehouse/raw-material')
}
