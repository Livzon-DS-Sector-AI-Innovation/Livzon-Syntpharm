import { redirect } from 'next/navigation'
import { DossierWriterPageClient } from '@/components/registration'
import { getDossierWriterUrl } from '@/lib/registration/external'

// 动态渲染由 app/(dashboard)/registration/layout.tsx 的 force-dynamic 继承，
// 因此这里读到的是部署环境的运行时变量，而不是构建期快照。
export default function DossierWriterListPage() {
  // 已配置外部撰写系统 → 旧链接/书签直接跳过去；未配置则保持原有系统内页面
  const externalUrl = getDossierWriterUrl()
  if (externalUrl) {
    redirect(externalUrl)
  }
  return <DossierWriterPageClient />
}
