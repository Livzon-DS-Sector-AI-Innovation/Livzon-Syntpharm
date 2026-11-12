'use client'

import { BgColorsOutlined } from '@ant-design/icons'

import { highlightStyleLabel } from '@/types/agent/ppt-video'

const STYLE_TEXT_RECOLOR = 'text_recolor'
const STYLE_DIM = 'dim'
const STYLE_OUTLINE = 'outline'

export interface HighlightPreviewProps {
  /** 已解析出的最终样式（单页 > 项目 > 系统默认）；空按系统默认处理 */
  style: string
  /** 已解析出的最终主色 #RRGGBB */
  color: string
  /** 本级开关是否勾选；false 时整块置灰并标「未启用」 */
  enabled: boolean
  /** 取值来源说明，如「跟随项目设置」 */
  note?: string
}

/**
 * 高亮效果示意。
 *
 * 四种样式在成片里的差别是「压暗 + 描边 + 文字换色」的不同组合，纯文字摘要看不出
 * 区别（历史上这里只改了颜色，选「仅压暗」时预览毫无变化），所以用一块缩小的页面
 * 示意真实画法：压暗用半透明遮罩，命中行用一个高于遮罩的亮面「还原」，描边用
 * box-shadow 避免撑动布局。
 */
export default function HighlightPreview({ style, color, enabled, note }: HighlightPreviewProps) {
  const dim = style === STYLE_DIM || style === `${STYLE_DIM}_${STYLE_OUTLINE}`
  const outline = style === STYLE_OUTLINE || style === `${STYLE_DIM}_${STYLE_OUTLINE}`
  const recolor = style === STYLE_TEXT_RECOLOR
  const hitStyle = {
    // 描边用 box-shadow：外扩不占位，切换样式时文字不会左右抖动
    boxShadow: outline ? `0 0 0 3px ${color}` : undefined,
    // 文字染色档：命中内容整句换色加粗，没有底色也没有边框
    color: recolor ? color : undefined,
    fontWeight: recolor ? 600 : 500,
  }

  return (
    <div
      className={`rounded-lg border border-[#E5E3DF] bg-[#FAFAF9] p-3 transition-opacity duration-150 ${
        enabled ? 'opacity-100' : 'opacity-60'
      }`}
    >
      <div className="mb-2 flex items-center gap-1.5 text-[12px] text-[#5D5B54]">
        <BgColorsOutlined />
        效果预览
        {!enabled && (
          <span className="ml-auto rounded-full bg-[#EFEDE9] px-2 py-0.5 text-[11px] text-[#A4A097]">未启用</span>
        )}
      </div>

      <div className="relative overflow-hidden rounded-md border border-[#E5E3DF] bg-white px-3 py-2 text-[12px] leading-6 text-[#37352F]">
        <span className="block">这一步的关键是把参数固定下来。</span>
        <span
          className={`relative z-10 block ${dim ? '-mx-1.5 rounded-sm bg-white px-1.5' : ''}`}
          style={hitStyle}
        >
          采样温度控制在 25 摄氏度
        </span>
        <span className="block">记录完成后由复核人确认。</span>
        {/* 遮罩放在内容之后、命中行之下：非命中行被压暗，命中行保持亮面 */}
        {dim && <span className="pointer-events-none absolute inset-0 bg-black/[0.55]" />}
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-[#A4A097]">
        <span>样式：{highlightStyleLabel(style)}</span>
        <span className="h-2.5 w-2.5 rounded-full border border-black/10" style={{ background: color }} />
        <span>颜色 {color}</span>
        {note && <span>· {note}</span>}
      </div>
      <span className="mt-1 block text-[11px] leading-4 text-[#A4A097]">
        示意效果，实际成片会按页面文字位置着色。
      </span>
    </div>
  )
}