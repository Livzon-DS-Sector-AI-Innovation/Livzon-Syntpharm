'use client'

import { ConfigProvider } from 'antd'
import type { PropsWithChildren } from 'react'

export function AntdProvider({ children }: PropsWithChildren) {
  return (
    <ConfigProvider
      warning={{
        // 抑制 useForm 未连接到 Form 元素的警告
        // antd 6.4+ 会检测 Form.useForm() 创建的实例是否连接到 Form
        strict: false,
      }}
    >
      {children}
    </ConfigProvider>
  )
}