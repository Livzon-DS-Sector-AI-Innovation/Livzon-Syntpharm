import { NextRequest, NextResponse } from 'next/server'

// Proxy is Next.js middleware; cannot import getApiBaseUrl from @/lib/api/server/base
// because base.ts uses next/headers which is unavailable in middleware context.
const BACKEND_URL = process.env.API_BASE_URL || 'http://localhost:8000'

export default function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl

  if (pathname.startsWith('/api')) {
    const url = new URL(pathname + request.nextUrl.search, BACKEND_URL)
    return NextResponse.rewrite(url)
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
