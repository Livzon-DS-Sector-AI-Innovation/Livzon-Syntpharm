import type { Metadata } from "next"
import "./globals.css"
import { Providers } from "@/components/Providers"

export const metadata: Metadata = {
  title: "工厂管理平台",
  description: "原料药制药厂综合业务管理平台",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  // Add error handler to catch startTime errors
  if (typeof window !== 'undefined') {
    const originalError = console.error
    console.error = function(...args) {
      if (args[0]?.includes?.('startTime')) {
        console.warn('[CAUGHT] startTime error suppressed:', args)
        return
      }
      originalError.apply(console, args)
    }
    
    window.addEventListener('error', (event) => {
      if (event.message?.includes('startTime')) {
        console.warn('[CAUGHT] Global startTime error:', event.message)
        event.preventDefault()
      }
    })
    
    window.addEventListener('unhandledrejection', (event) => {
      if (event.reason?.message?.includes('startTime')) {
        console.warn('[CAUGHT] Unhandled rejection startTime error:', event.reason)
        event.preventDefault()
      }
    })
  }

  return (
    <html lang="zh-CN" className="h-full" suppressHydrationWarning>
      <body className="h-full antialiased" style={{ fontFamily: "'Inter', -apple-system, system-ui, 'Segoe UI', Helvetica, sans-serif" }}>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
}
