import { notFound } from 'next/navigation'

import { PptVideoWorkbench } from '@/components/agent/ppt-video'
import { fetchPptVideoProject, fetchVoiceCatalog } from '@/lib/api/server/agent'
import type { ProjectDetail, VoiceOption } from '@/types/agent/ppt-video'

export const dynamic = 'force-dynamic'

/**
 * 三栏工作台：详情在服务端取一次，之后由客户端持有并局部刷新
 * （保存讲稿 / 试听 / 渲染轮询都只回拉必要数据）。
 */
export default async function PptVideoWorkbenchPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params

  let detail: ProjectDetail
  try {
    detail = await fetchPptVideoProject(id)
  } catch (error) {
    const message = error instanceof Error ? error.message : ''
    // 后端 NotFound 统一是「XXX不存在」；其它错误交给错误边界，不伪装成 404
    if (message.includes('不存在') || message.includes('404')) {
      notFound()
    }
    throw error
  }

  const voices: VoiceOption[] = await fetchVoiceCatalog().catch(() => [])

  return <PptVideoWorkbench initialDetail={detail} voices={voices} />
}