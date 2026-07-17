"use client"

// Stub component for CardPreview
interface CardPreviewProps {
  content?: string
  dataSources?: any[]
  cardTemplate?: string
  headerColor?: string
}

export default function CardPreview({ content, dataSources, cardTemplate, headerColor }: CardPreviewProps) {
  return (
    <div style={{ padding: "16px", border: "1px solid #d9d9d9", borderRadius: "6px", backgroundColor: "#fafafa" }}>
      <div dangerouslySetInnerHTML={{ __html: content || "<p>暂无内容</p>" }} />
    </div>
  )
}
