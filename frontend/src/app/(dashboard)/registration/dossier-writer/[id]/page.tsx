import { redirect } from 'next/navigation'
import { DossierWriterDetailPageClient } from '@/components/registration'
import { getDossierWriterUrl } from '@/lib/registration/external'

// 同列表页：动态渲染由 registration/layout.tsx 的 force-dynamic 继承。
export default function DossierDetailPage() {
  // 深链同样跳外部系统，避免旧书签落到已迁走的内部页面；未配置时保持原页面
  const externalUrl = getDossierWriterUrl()
  if (externalUrl) {
    redirect(externalUrl)
  }
  return <DossierWriterDetailPageClient />
}
