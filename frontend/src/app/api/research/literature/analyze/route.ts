/**
 * SSE 流式代理：文献分析
 * 
 * 架构说明：
 * - Client Component → 本地 Route Handler（/api/research/literature/analyze）
 * - Route Handler → 后端 API（${BACKEND_URL}/api/v1/research/literature/analyze）
 * - 后端返回 SSE 流 → Route Handler 透传 → Client 读取流
 * 
 * 为什么不用 Server Actions：
 * Server Actions 不支持流式响应。SSE 流式场景需要客户端直接 fetch 读取 ReadableStream，
 * 这是 Next.js 的限制。POST 到后端的写操作在此 route handler 中完成（服务端），
 * 客户端只读取本地 route handler 的流式响应。
 */
import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.API_BASE_URL || 'http://dazah-backend-app-1:8000'

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    
    // Forward to backend
    const response = await fetch(`${BACKEND_URL}/api/v1/research/literature/analyze`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      return NextResponse.json(
        { error: `Backend request failed: ${response.status}` },
        { status: response.status }
      )
    }

    if (!response.body) {
      return NextResponse.json({ error: 'No response body' }, { status: 500 })
    }

    // Stream the response back to client
    return new NextResponse(response.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    })
  } catch (error) {
    console.error('Literature analysis proxy error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
