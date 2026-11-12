import Link from 'next/link'

import { PptVideoTable } from '@/components/agent/ppt-video'
import { fetchAiConfigs, fetchPptVideoProjects, fetchVoiceCatalog } from '@/lib/api/server/agent'
import type { AiConfigListResponse, ProjectSummary, VoiceOption } from '@/types/agent/ppt-video'

export const dynamic = 'force-dynamic'

/**
 * PPT 配音视频列表：首屏由 RSC 取数，翻页/筛选交给客户端 GET，
 * 避免整页刷新（工作台里的轮询也不会被牵连）。
 */
export default async function PptVideoListPage() {
  let items: ProjectSummary[] = []
  let total = 0
  let voices: VoiceOption[] = []
  let error: string | null = null

  // AI 配置失败不该拖垮列表：拿不到就传 null，抽屉打开时自己再取一次
  const [listResult, voiceResult, aiResult] = await Promise.allSettled([
    fetchPptVideoProjects({ page: 1, page_size: 20 }),
    fetchVoiceCatalog(),
    fetchAiConfigs(),
  ])

  if (listResult.status === 'fulfilled') {
    items = listResult.value.items
    total = listResult.value.total
  } else {
    error =
      listResult.reason instanceof Error ? listResult.reason.message : '数据暂时取不到，请稍后重试'
  }

  if (voiceResult.status === 'fulfilled') voices = voiceResult.value

  const aiConfigs: AiConfigListResponse | null = aiResult.status === 'fulfilled' ? aiResult.value : null

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <div className="flex items-center gap-2 text-[12px] text-[#A4A097]">
            <Link href="/agent" className="hover:text-[#5645D4]">
              智能体
            </Link>
            <span>/</span>
            <span>PPT 配音视频</span>
          </div>
          <h1 className="mt-1 text-[20px] font-semibold text-[#1A1A1A]">PPT 配音视频</h1>
          <p className="mt-1 text-[13px] text-[#5D5B54]">
            上传 PPT 与逐页讲稿，按页校对旁白，生成中英文配音成片。
          </p>
        </div>
      </div>

      <PptVideoTable
        initialItems={items}
        initialTotal={total}
        voices={voices}
        initialError={error}
        initialAiConfigs={aiConfigs}
      />
    </div>
  )
}