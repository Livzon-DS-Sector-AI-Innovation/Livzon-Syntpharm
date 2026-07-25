import { getCurrentUser } from '@/actions/auth'
import SettingsAdminClient from '@/components/settings/SettingsAdminClient'
import { NoAccessResult } from '@/components/settings/NoAccessResult'

export const dynamic = 'force-dynamic'

export default async function SettingsPage() {
  const user = await getCurrentUser()

  if (!user) {
    return <NoAccessResult />
  }

  return <SettingsAdminClient />
}
