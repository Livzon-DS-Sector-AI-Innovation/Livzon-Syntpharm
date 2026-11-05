'use client'

import { Empty, Tag, Typography } from 'antd'

import { formatDuration, type SlideItem } from '@/types/agent/ppt-video'

interface Props {
  slides: SlideItem[]
  activeSlideUid: string
  onSelect: (slideUid: string) => void
}

/** 状态条颜色：琥珀=画面已变待重写，紫=AI 稿，绿=换源新增待补稿 */
const STATUS_BAR: Record<'stale' | 'ai' | 'added', { color: string; title: string }> = {
  stale: { color: '#D97706', title: '画面已变，讲稿待按新画面重写' },
  ai: { color: '#5645D4', title: 'AI 生成的讲稿' },
  added: { color: '#16A34A', title: '换源新增页，尚未生成讲稿' },
}

/**
 * 页级状态判定（后端没单独存「新增」标记，用现有字段推）：
 * - 换源新增页：script_stale 为真且还没有任何讲稿；
 * - 换源变更页：script_stale 为真但保留了旧讲稿；
 * - AI 稿：script_source 为 ai。
 */
function resolveStatus(slide: SlideItem): keyof typeof STATUS_BAR | null {
  const hasScript = Boolean((slide.script_text || '').trim())
  if (slide.script_stale) return hasScript ? 'stale' : 'added'
  if (slide.script_source === 'ai' && hasScript) return 'ai'
  return null
}

/**
 * 左栏页时间轴：缩略图 + 页号角标 + 讲稿摘要 + 配音状态。
 * 第 1 页标「片头」，提示它单独参与合成、改它不会重算正文。
 */
export default function SlideTimeline({ slides, activeSlideUid, onSelect }: Props) {
  if (!slides.length) {
    return <Empty description="还没有页面，请先上传 PPT" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  }

  return (
    <div className="flex flex-col gap-2">
      {slides.map((slide) => {
        const active = slide.slide_uid === activeSlideUid
        const empty = !(slide.script_text || '').trim()
        const noSourceText = !slide.has_page_text && empty
        const excerpt = (slide.script_text || slide.page_text || '').replace(/\s+/g, ' ').slice(0, 34)
        const statusKey = resolveStatus(slide)
        const status = statusKey ? STATUS_BAR[statusKey] : null
        return (
          <button
            key={slide.slide_uid}
            type="button"
            data-slide-uid={slide.slide_uid}
            onClick={() => onSelect(slide.slide_uid)}
            title={status?.title}
            className={[
              'group relative flex w-full cursor-pointer gap-3 overflow-hidden rounded-lg border p-2 pl-3 text-left transition-all',
              active
                ? 'border-[#5645D4] bg-[#F4F1FE] shadow-[0_0_0_1px_#5645D4]'
                : 'border-[#E5E3DF] bg-white hover:border-[#C9C1F0] hover:bg-[#FAFAF9]',
            ].join(' ')}
          >
            {status && (
              <span
                aria-hidden
                className="absolute bottom-0 left-0 top-0 w-[2px]"
                style={{ backgroundColor: status.color }}
              />
            )}

            <span className="relative block h-[54px] w-[96px] shrink-0 overflow-hidden rounded-md bg-[#1A1A1A]">
              {slide.image_url ? (
                // 缩略图走后端代理，浏览器带 cookie 鉴权；缺缩略图时回退大图，老项目不至于空着
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={slide.thumb_url || slide.image_url}
                  alt={`第 ${slide.slide_no} 页`}
                  loading="lazy"
                  decoding="async"
                  className="h-full w-full object-contain"
                />
              ) : (
                <span className="flex h-full w-full items-center justify-center text-[11px] text-[#A4A097]">
                  暂无预览
                </span>
              )}
              <span className="absolute left-1 top-1 rounded bg-black/65 px-1 text-[11px] font-medium text-white">
                {slide.slide_no}
              </span>
            </span>

            <span className="flex min-w-0 flex-1 flex-col justify-between py-0.5">
              <span className="flex items-center gap-1">
                {slide.slide_no === 1 && <Tag color="gold" className="!m-0 !px-1 !text-[11px]">片头</Tag>}
                {noSourceText && (
                  <Tag className="!m-0 !px-1 !text-[11px]">本页无文字</Tag>
                )}
                {slide.script_stale && (
                  <Tag color="orange" className="!m-0 !px-1 !text-[11px]">
                    {empty ? '待补稿' : '待重写'}
                  </Tag>
                )}
                {slide.script_source === 'ai' && (
                  <Tag color="purple" className="!m-0 !px-1 !text-[11px]">AI 初稿</Tag>
                )}
                {slide.has_audio ? (
                  <Tag color="green" className="!m-0 !px-1 !text-[11px]">已配音</Tag>
                ) : (
                  <Tag className="!m-0 !px-1 !text-[11px]">未配音</Tag>
                )}
                {slide.duration_ms > 0 && (
                  <Typography.Text type="secondary" className="text-[11px]">
                    {formatDuration(slide.duration_ms)}
                  </Typography.Text>
                )}
              </span>
              <span className="block truncate text-[12px] text-[#5D5B54]">
                {noSourceText ? '本页无文字，需手工填写' : excerpt || '未填写讲稿'}
              </span>
            </span>
          </button>
        )
      })}
    </div>
  )
}