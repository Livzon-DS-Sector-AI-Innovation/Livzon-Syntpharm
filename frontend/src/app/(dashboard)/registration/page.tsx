export const dynamic = 'force-dynamic'

import { RegistrationHomeClient } from '@/components/registration'
import { getDossierWriterUrl } from '@/lib/registration/external'

export default function RegistrationPage() {
  // 外部撰写系统地址为空时，概览卡片保持原有的系统内页面入口
  return <RegistrationHomeClient dossierWriterUrl={getDossierWriterUrl()} />
}
