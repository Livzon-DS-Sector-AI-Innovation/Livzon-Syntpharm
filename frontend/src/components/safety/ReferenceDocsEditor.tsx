'use client'

// Stub component for ReferenceDocsEditor
export default function ReferenceDocsEditor({ value, onChange }: { value?: string; onChange?: (value: string) => void }) {
  return (
    <textarea
      value={value || ''}
      onChange={(e) => onChange?.(e.target.value)}
      style={{ width: '100%', minHeight: '200px', padding: '8px', border: '1px solid #d9d9d9', borderRadius: '6px' }}
      placeholder="参考文档编辑器（功能开发中）"
    />
  )
}
