'use client'

import { useState } from 'react'
import { Button, Upload, message, Modal } from 'antd'
import { UploadOutlined } from '@ant-design/icons'
import type { UploadProps } from 'antd'

export function ExcelSyncButton() {
  const [loading, setLoading] = useState(false)

  const handleSync: UploadProps['customRequest'] = async ({ file, onSuccess, onError }) => {
    setLoading(true)
    const formData = new FormData()
    formData.append('file', file as File)
    
    try {
      const response = await fetch('/api/v1/equipment/equipments/sync-excel', {
        method: 'POST',
        body: formData,
      })
      const result = await response.json()
      if (result.code === 200) {
        const { updated, inserted, migrated, deleted } = result.data
        Modal.info({
          title: '同步完成',
          content: (
            <div>
              <p>更新: {updated} 台</p>
              <p>迁移: {migrated} 台</p>
              <p>新增: {inserted} 台</p>
              <p>停用: {deleted} 台</p>
            </div>
          ),
          onOk: () => window.location.reload(),
        })
        onSuccess?.(result)
      } else {
        message.error(result.message || '同步失败')
        onError?.(new Error(result.message))
      }
    } catch (e) {
      message.error('网络错误，请重试')
      onError?.(e as Error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Upload
      accept=".xls,.xlsx"
      showUploadList={false}
      customRequest={handleSync}
      disabled={loading}
    >
      <Button icon={<UploadOutlined />} loading={loading}>
        {loading ? '同步中...' : '同步 Excel'}
      </Button>
    </Upload>
  )
}
