'use client'

export default function MeetingRequestPage() {

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden">
      <div className="px-6 py-4 shrink-0">
        <h1 className="text-[22px] font-semibold text-[var(--color-charcoal)]">领用记录</h1>
      </div>
      <iframe
        src="https://j0eukrlohu.feishu.cn/share/base/form/shrcngZbqXpLyfbg38hcPVvyghg"
        className="w-full flex-1 border-none"
        title="飞书领用申请表单"
      />
    </div>
  )
}
