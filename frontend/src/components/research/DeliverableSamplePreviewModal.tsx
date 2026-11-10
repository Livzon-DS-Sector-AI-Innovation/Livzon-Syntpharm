'use client'

import { useRef, useState } from 'react'
import { Alert, Button, Modal, Spin } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import { renderAsync } from 'docx-preview'
import { downloadDeliverableTemplateVersion } from '@/lib/api/client/research/deliverable-template'
import { saveBlob } from '@/lib/utils/download'
import type { components } from '@/types/generated/schema'

type DocGenTemplateSampleData = components['schemas']['DocGenTemplateSampleData']

export interface SamplePreviewTarget {
  templateId: string
  fileName: string
  data: DocGenTemplateSampleData
}

interface Props {
  /** 非空即打开；父组件用它在「生成示例稿」成功后弹出预览 */
  target: SamplePreviewTarget | null
  onClose: () => void
}

/**
 * 填充示例稿在线预览。
 *
 * 示例稿是一个独立的「示例稿」版本，拿历史版本下载接口取字节流即可复用 docx-preview，
 * 不需要额外的预览端点。这里不复刻模板页的预览逻辑，是因为它只服务一种来源，
 * 且要顺带展示覆盖率（标注了多少项、多少项没定位到）。
 */
export function DeliverableSamplePreviewModal({ target, onClose }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [downloading, setDownloading] = useState(false)

  const runRender = async () => {
    if (!target) return
    setLoading(true)
    setError(null)
    try {
      const blob = await downloadDeliverableTemplateVersion(target.templateId, target.data.version_id)
      if (!containerRef.current) return
      containerRef.current.innerHTML = ''
      await renderAsync(blob, containerRef.current, undefined, { inWrapper: true, ignoreWidth: true })
    } catch (e) {
      setError(e instanceof Error ? e.message : '示例稿预览失败，可以下载后用 Word 打开')
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = async () => {
    if (!target) return
    setDownloading(true)
    try {
      const blob = await downloadDeliverableTemplateVersion(target.templateId, target.data.version_id)
      saveBlob(blob, target.fileName)
    } catch (e) {
      setError(e instanceof Error ? e.message : '下载示例稿失败')
    } finally {
      setDownloading(false)
    }
  }

  const notice = target
    ? [
        `已标注 ${target.data.slot_count} 项`,
        target.data.skipped_count > 0 ? `${target.data.skipped_count} 项未启用或未绑定位置已跳过` : '',
        target.data.unresolved_count > 0 ? `${target.data.unresolved_count} 项在母本里找不到位置` : '',
      ]
        .filter(Boolean)
        .join('；')
    : ''

  return (
    <Modal
      title={`填充示例稿：${target?.fileName ?? ''}`}
      open={target !== null}
      onCancel={onClose}
      width={880}
      destroyOnHidden
      afterOpenChange={(visible) => {
        if (visible) void runRender()
        else {
          setError(null)
          setLoading(false)
        }
      }}
      footer={
        <Button icon={<DownloadOutlined />} loading={downloading} onClick={() => void handleDownload()}>
          下载示例稿
        </Button>
      }
    >
      <Alert type="info" showIcon style={{ marginBottom: 12 }} title={notice} description="标记文本是提示，不是正式内容：正式生成时按填充项逐条填写，不会带这些【】标记。" />
      {error && <Alert type="warning" showIcon style={{ marginBottom: 12 }} title={error} />}
      {loading && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin tip="正在渲染示例稿…" />
        </div>
      )}
      {!error && (
        <div
          ref={containerRef}
          style={{ border: '1px solid #f0f0f0', padding: 12, minHeight: 320, maxHeight: 560, overflow: 'auto' }}
        />
      )}
    </Modal>
  )
}