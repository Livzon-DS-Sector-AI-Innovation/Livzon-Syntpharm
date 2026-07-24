'use client'

import { WorkshopTable } from '@/components/energy'

export default function WorkshopsPage() {
  return (
    <div style={{ padding: '28px 32px', maxWidth: 1280, minHeight: '100%', background: '#fafaf9' }}>
      {/* ════ 数据表格 ════ */}
      <div
        style={{
          background: '#ffffff',
          borderRadius: 12,
          padding: '18px 20px',
          boxShadow: '0 1px 3px rgba(10, 10, 10, 0.04)',
          border: '1px solid #ede9e4',
        }}
      >
        <WorkshopTable />
      </div>
    </div>
  )
}
