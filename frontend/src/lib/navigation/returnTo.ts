/**
 * 返回来源签名：进入下级页面时，把「当前页（含筛选参数）的相对地址」塞进 URL，
 * 下级页据此返回原地，而不是硬跳某个固定列表页。
 *
 * 为什么参数名叫 returnTo 而不是 from：研发知识库页已用 `?from=project-detail`
 * 表示来源类型，同名参数语义冲突，这里改用 returnTo 承载完整路径。
 */

/** URL 参数名 */
export const RETURN_TO_PARAM = 'returnTo'

/** 只允许回跳研发模块内的路径：其余一律拒绝，避免被外部链接当开放重定向用 */
const ALLOWED_PREFIX = '/research'

function isSafeResearchPath(value: string): boolean {
  if (!value.startsWith(ALLOWED_PREFIX)) return false
  // `//evil.com` 是协议相对地址；部分浏览器会把 `\` 当成 `/`
  if (value.startsWith('//') || value.includes('\\')) return false
  // 路径里不能出现换行/空白，避免响应头与日志注入
  if (/\s/.test(value)) return false
  return (
    value === ALLOWED_PREFIX ||
    value.startsWith(`${ALLOWED_PREFIX}/`) ||
    value.startsWith(`${ALLOWED_PREFIX}?`)
  )
}

/**
 * 校验并还原来源地址。
 * `useSearchParams().get()` 已经解码一次，但拼接 href 时也可能传未解码的原值，
 * 所以两种形态都试一遍，取第一个合法值。
 */
export function sanitizeReturnTo(raw: string | null | undefined): string | null {
  if (!raw) return null
  const candidates = [raw.trim()]
  try {
    const decoded = decodeURIComponent(raw).trim()
    if (decoded !== candidates[0]) candidates.push(decoded)
  } catch {
    // 非法百分号编码：只按原文判定
  }
  return candidates.find(isSafeResearchPath) ?? null
}

/** 生成可直接拼到 href 后面的 `returnTo=...` 查询串；非法地址返回空串 */
export function buildReturnTo(currentUrl: string | null | undefined): string {
  const safe = sanitizeReturnTo(currentUrl)
  return safe ? `${RETURN_TO_PARAM}=${encodeURIComponent(safe)}` : ''
}

/** 拼接 href 与来源签名：自动处理 `?` / `&` / hash */
export function withReturnTo(href: string, currentUrl: string | null | undefined): string {
  const query = buildReturnTo(currentUrl)
  if (!query) return href
  const [beforeHash, hash = ''] = href.split('#')
  const separator = beforeHash.includes('?') ? '&' : '?'
  const next = `${beforeHash}${separator}${query}`
  return hash ? `${next}#${hash}` : next
}

/** 当前浏览器地址（相对路径 + query）；服务端渲染时返回 null */
export function currentRelativeUrl(): string | null {
  if (typeof window === 'undefined') return null
  return `${window.location.pathname}${window.location.search}`
}

/** 来源路径 → 人类可读页面名，用于「返回报告列表」这类文案 */
const PAGE_LABELS: ReadonlyArray<readonly [RegExp, string]> = [
  [/^\/research\/reports\/generation\//, '生成详情'],
  [/^\/research\/reports\/settings/, '生成设置'],
  [/^\/research\/reports/, '报告列表'],
  [/^\/research\/projects\/[^/]+/, '项目详情'],
  [/^\/research\/knowledge-bases/, '知识库'],
  [/^\/research\/deliverable-templates/, '交付物模板'],
  [/^\/research\/pilot-workflow/, '试点流程'],
]

/**
 * 描述来源地址对应的页面名；识别不出时返回 null，调用方据此退回「上一页」文案。
 * 只取路径部分比较，避免 query 里的参数影响匹配。
 */
export function describeReturnTarget(path: string | null | undefined): string | null {
  if (!path) return null
  const pathname = path.split('?')[0]
  return PAGE_LABELS.find(([pattern]) => pattern.test(pathname))?.[1] ?? null
}