/**
 * Dashboard 段级 loading：路由切换 / 刷新时先渲染骨架，避免出现
 * 「空白 → 旧数据 → 新数据」的内容闪动。纯 CSS，不依赖 antd 水合。
 */
export default function DashboardLoading() {
  return (
    <div className="mx-auto w-full max-w-[1200px] animate-pulse" aria-busy="true" aria-label="页面加载中">
      <div className="mb-4 h-7 w-40 rounded-[var(--rounded-sm)] bg-[var(--color-hairline-soft)]" />
      <div className="rounded-[var(--rounded-lg)] border border-[var(--color-hairline)] bg-[var(--color-canvas)] p-5">
        <div className="flex flex-wrap items-center gap-3">
          <div className="h-9 w-[180px] rounded-[var(--rounded-sm)] bg-[var(--color-hairline-soft)]" />
          <div className="h-9 w-[140px] rounded-[var(--rounded-sm)] bg-[var(--color-hairline-soft)]" />
          <div className="h-9 w-[220px] rounded-[var(--rounded-sm)] bg-[var(--color-hairline-soft)]" />
        </div>
        <div className="mt-6 space-y-3">
          {Array.from({ length: 8 }).map((_, index) => (
            <div
              key={index}
              className="h-11 w-full rounded-[var(--rounded-sm)] bg-[var(--color-hairline-soft)]"
            />
          ))}
        </div>
      </div>
    </div>
  )
}
