'use client'

import { Spin } from 'antd'

export function LoadingSpinner({ description }: { description?: string }) {
  return (
    <div className="flex items-center justify-center py-20">
      <Spin size="large" description={description} />
    </div>
  )
}
