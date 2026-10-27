import type { Metadata, Viewport } from "next"
import { AntdRegistry } from "@ant-design/nextjs-registry"
import "./globals.css"
import { Providers } from "@/components/Providers"

export const metadata: Metadata = {
  title: "工厂管理平台",
  description: "原料药制药厂综合业务管理平台",
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#5645d4",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="zh-CN" className="h-full" suppressHydrationWarning>
      <body className="h-full antialiased" style={{ fontFamily: "'Inter', -apple-system, system-ui, 'Segoe UI', Helvetica, sans-serif" }}>
        {/* antd 的 CSS-in-JS 必须在 SSR 阶段抽取并内联：
            否则首屏 HTML 先以「无 antd 样式」到达浏览器，等 JS 下载执行后才注入，
            公网/弱网下表现为明显的排版错乱与闪动。 */}
        <AntdRegistry>
          <Providers>
            {children}
          </Providers>
        </AntdRegistry>
      </body>
    </html>
  )
}
