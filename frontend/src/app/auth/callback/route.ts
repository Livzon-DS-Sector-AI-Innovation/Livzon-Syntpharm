import { NextRequest, NextResponse } from "next/server"

function getBaseUrl(request: NextRequest): string {
  const forwardedProto = request.headers.get("x-forwarded-proto")
  const forwardedHost = request.headers.get("x-forwarded-host")
  if (forwardedHost) {
    const protocol = forwardedProto || "https"
    return `${protocol}://${forwardedHost}`
  }
  return request.nextUrl.origin
}

export async function GET(request: NextRequest) {
  const token = request.nextUrl.searchParams.get("token")
  if (!token) {
    return NextResponse.redirect(new URL("/login?error=callback_failed", request.url))
  }

  const baseUrl = getBaseUrl(request)
  const isSecure = baseUrl.startsWith("https:")
  const response = NextResponse.redirect(`${baseUrl}/production`)
  response.cookies.set("auth_token", token, {
    httpOnly: true,
    secure: isSecure,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  })
  return response
}