import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.API_BASE_URL || 'http://localhost:8000'

/**
 * 消费 `login_redirect` cookie：把「会话过期前所在的页面」还原成一次 307 跳转。
 *
 * - 只接受站内路径，避免被构造成开放重定向（`//host`、`/\host`、`/login` 自身都拒绝）；
 * - 读取后立即删除 cookie —— 否则「返回首页 → 又被弹回原页」会反复跳。
 */
function consumeLoginRedirect(request: NextRequest): NextResponse | null {
  const raw = request.cookies.get('login_redirect')?.value
  if (!raw) return null

  let target = ''
  try {
    target = decodeURIComponent(raw)
  } catch {
    return null
  }

  const isInternal =
    target.startsWith('/') && !target.startsWith('//') && !target.startsWith('/\\')
  if (!isInternal || target.startsWith('/login')) return null

  const [targetPath, search] = target.split('?')
  const url = request.nextUrl.clone()
  url.pathname = targetPath
  url.search = search ? `?${search}` : ''

  const response = NextResponse.redirect(url)
  response.cookies.delete('login_redirect')
  return response
}

export default function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl

  if (pathname.startsWith('/api')) {
    const url = new URL(pathname + request.nextUrl.search, BACKEND_URL)
    return NextResponse.rewrite(url)
  }

  // 会话过期回跳：客户端收到 401 时把原地址写进 login_redirect（见 lib/api/client.ts），
  // 登录成功落到 `/` 后由这里送回原页面。只在根路径处理，其他请求完全不受影响。
  if (pathname === '/') {
    const redirectResponse = consumeLoginRedirect(request)
    if (redirectResponse) return redirectResponse
  }

  const response = NextResponse.next()
  if (
    !pathname.startsWith('/_next/static') &&
    !pathname.startsWith('/_next/image') &&
    !pathname.includes('/favicon.ico')
  ) {
    response.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, private')
    response.headers.set('Pragma', 'no-cache')
    response.headers.set('Expires', '0')
  }
  return response
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
