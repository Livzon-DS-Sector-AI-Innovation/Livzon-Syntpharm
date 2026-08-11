import { NextRequest, NextResponse } from 'next/server'
import { cookies } from 'next/headers'
import { getApiBaseUrl } from '@/lib/api/server/base'

export async function POST(request: NextRequest) {
  const body = await request.json()
  const cookieStore = await cookies()
  const authCookie = cookieStore.get('auth_token')
  const authHeaders: Record<string, string> = authCookie?.value
    ? { Authorization: `Bearer ${authCookie.value}` }
    : {}

  const res = await fetch(`${getApiBaseUrl()}/api/v1/hr/training-evaluation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    return NextResponse.json({ error: text }, { status: res.status })
  }

  const blob = await res.blob()
  return new NextResponse(blob, {
    headers: {
      'Content-Type': res.headers.get('content-type') || 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': res.headers.get('content-disposition') || 'attachment; filename=evaluation.xlsx',
    },
  })
}
