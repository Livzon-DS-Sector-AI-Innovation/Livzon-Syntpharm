/**
 * 根级 loading：登录 / 根路径重定向到首页期间显示，避免白屏一闪。
 * 只占位、不取数，保证在 Providers 水合前也能正常渲染。
 */
export default function RootLoading() {
  return (
    <div
      className="flex min-h-screen items-center justify-center bg-[var(--color-surface)]"
      aria-busy="true"
      aria-label="加载中"
    >
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--color-hairline)] border-t-[var(--color-primary)]" />
    </div>
  )
}
