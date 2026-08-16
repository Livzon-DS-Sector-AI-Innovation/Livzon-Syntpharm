import { NextRequest, NextResponse } from 'next/server'

// Proxy is Next.js middleware; cannot import getApiBaseUrl from @/lib/api/server/base
// because base.ts uses next/headers which is unavailable in middleware context.
const BACKEND_URL = process.env.API_BASE_URL || 'http://localhost:8000'

export default async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl

  if (pathname.startsWith('/api/v1')) {
    const url = new URL(pathname + request.nextUrl.search, BACKEND_URL)
    
    // Forward the request to the backend
    const headers = new Headers(request.headers)
    headers.delete('host') // Remove host header to avoid conflicts
    
    try {
      const response = await fetch(url.toString(), {
        method: request.method,
        headers: headers,
        body: request.method !== 'GET' && request.method !== 'HEAD' ? await request.text() : undefined,
      })
      
      // Create a new response with the backend's response
      const newResponse = new NextResponse(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
      })
      
      return newResponse
    } catch (error) {
      console.error('Proxy error:', error)
      return NextResponse.json({ error: 'Proxy error' }, { status: 500 })
    }
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
