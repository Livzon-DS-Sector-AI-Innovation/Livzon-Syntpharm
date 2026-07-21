import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.API_BASE_URL || 'http://localhost:8000'

// 超时配置
const DEFAULT_TIMEOUT = 60000
const AI_PREVIEW_TIMEOUT = 600000 // 10分钟（AI 处理 PDF + OCR 需要较长时间）

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Proxy /api requests to backend (pass-through, not rewrite — Turbopack compatibility)
  if (pathname.startsWith('/api')) {
    const isAiPreview = pathname.includes('/ai-preview') || pathname.includes('/ai-confirm')
    const timeout = isAiPreview ? AI_PREVIEW_TIMEOUT : DEFAULT_TIMEOUT

    try {
      const url = new URL(pathname + request.nextUrl.search, BACKEND_URL)

      const headers: HeadersInit = {}
      request.headers.forEach((value, key) => {
        if (!['host', 'content-length', 'connection', 'expect', 'transfer-encoding'].includes(key.toLowerCase())) {
          headers[key] = value
        }
      })

      const fetchOptions: RequestInit = {
        method: request.method,
        headers,
        signal: AbortSignal.timeout(timeout),
      }

      if (!['GET', 'HEAD'].includes(request.method)) {
        fetchOptions.body = await request.arrayBuffer()
      }

      const backendResponse = await fetch(url.toString(), fetchOptions)

      if (backendResponse.status >= 300 && backendResponse.status < 400) {
        const location = backendResponse.headers.get('location')
        if (location) {
          return NextResponse.redirect(location, backendResponse.status)
        }
      }

      if (backendResponse.headers.get('content-type')?.includes('text/event-stream')) {
        return new NextResponse(backendResponse.body, {
          status: backendResponse.status,
          statusText: backendResponse.statusText,
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
          },
        })
      }

      return new NextResponse(backendResponse.body, {
        status: backendResponse.status,
        statusText: backendResponse.statusText,
        headers: backendResponse.headers,
      })
    } catch (error: any) {
      console.error(`Proxy error for ${pathname}:`, error.message, error.cause || '')
      const status = error.name === 'TimeoutError' || error.name === 'AbortError' ? 504 : 502
      return new NextResponse(null, { status })
    }
  }

}

export const config = {
  matcher: '/api/v1/:path*',
}