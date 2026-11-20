import Link from 'next/link'

export const dynamic = 'force-dynamic'

interface Capability {
  key: string
  title: string
  description: string
  href?: string
  points: string[]
}

const CAPABILITIES: Capability[] = [
  {
    key: 'ppt-video',
    title: 'PPT 配音视频',
    description: '上传 PPT 与逐页讲稿，生成中英文旁白的成片，支持单页试听与版本复用。',
    href: '/agent/ppt-videos',
    points: ['逐页讲稿 + 中英音色', '单页试听，不必等整片', '每版可下载，复用有据可查'],
  },
]

export default function AgentPage() {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-[20px] font-semibold text-[#1A1A1A]">智能体</h1>
        <p className="mt-1 text-[13px] text-[#5D5B54]">
          把重复的内容加工交给 AI：上传素材、按页校对、出片留痕。当前开放的能力如下。
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {CAPABILITIES.map((item) => (
          <Link
            key={item.key}
            href={item.href ?? '#'}
            className="group flex flex-col justify-between rounded-xl border border-[#E5E3DF] bg-white p-4 transition-all hover:border-[#5645D4] hover:shadow-[0_4px_16px_rgba(86,69,212,0.08)]"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[15px] font-medium text-[#1A1A1A]">{item.title}</span>
                <span className="text-[12px] text-[#5645D4] opacity-0 transition-opacity group-hover:opacity-100">
                  进入 →
                </span>
              </div>
              <p className="mt-1.5 text-[12px] leading-5 text-[#5D5B54]">{item.description}</p>
            </div>
            <ul className="mt-3 flex flex-wrap gap-1.5">
              {item.points.map((point) => (
                <li
                  key={point}
                  className="rounded-md bg-[#F4F1FE] px-2 py-0.5 text-[11px] text-[#5645D4]"
                >
                  {point}
                </li>
              ))}
            </ul>
          </Link>
        ))}

        <div className="flex flex-col justify-center rounded-xl border border-dashed border-[#E5E3DF] bg-[#FAFAF9] p-4">
          <span className="text-[15px] font-medium text-[#A4A097]">更多能力</span>
          <p className="mt-1.5 text-[12px] leading-5 text-[#A4A097]">
            研发文档生成、资料问答等能力在其它模块内提供；本模块按能力逐个开放。
          </p>
        </div>
      </div>
    </div>
  )
}