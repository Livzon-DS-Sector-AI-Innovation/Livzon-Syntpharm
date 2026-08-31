'use client'

import { useState } from 'react'
import { Button, Upload, message, Modal, Checkbox } from 'antd'
import { UploadOutlined } from '@ant-design/icons'
import type { UploadProps } from 'antd'

const ALLOWED_TYPES = ['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
const ALLOWED_EXTENSIONS = ['.xls', '.xlsx']

export function ExcelSyncButton() {
  const [loading, setLoading] = useState(false)
  const [dryRun, setDryRun] = useState(false)

  const beforeUpload = (file: File) => {
    const isExcel = ALLOWED_TYPES.includes(file.type) || ALLOWED_EXTENSIONS.some(ext => file.name.endsWith(ext))
    if (!isExcel) {
      message.error('只能上传 .xls 或 .xlsx 格式的 Excel 文件！')
      return Upload.LIST_IGNORE
    }
    return true
  }

  const handleSync: UploadProps['customRequest'] = async ({ file, onSuccess, onError }) => {
    setLoading(true)
    const formData = new FormData()
    formData.append('file', file as File)
    
    try {
      // 如果开启预览模式，在 URL 中附加参数
      const url = dryRun 
        ? '/api/v1/equipment/equipments/sync-excel?dry_run=true' 
        : '/api/v1/equipment/equipments/sync-excel'

      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      })
      
      if (!response.ok) throw new Error(`服务器响应错误: ${response.status}`)

      const result = await response.json()
      if (result.code === 200) {
        const { updated, inserted, migrated, deleted, warnings } = result.data
        
        let content = (
          <div style={{ marginTop: 10 }}>
            {dryRun && <p style={{ color: '#1890ff', fontWeight: 'bold' }}>🔍 预览模式（未执行实际变更）:</p>}
            <p>🔄 更新设备: <strong>{updated}</strong> 台</p>
            <p>🚚 位置迁移: <strong>{migrated}</strong> 台</p>
            <p>➕ 新增设备: <strong>{inserted}</strong> 台</p>
            <p>🗑️ 自动停用: <strong>{deleted}</strong> 台</p>
            {warnings && warnings.length > 0 && (
              <div style={{ marginTop: 10, padding: 10, background: '#fffbe6', border: '1px solid #ffe58f' }}>
                <p style={{ color: '#d48806', fontWeight: 'bold' }}>⚠️ 同步警告:</p>
                <ul style={{ paddingLeft: 20, margin: 0 }}>
                  {warnings.map((w: string, i: number) => <li key={i}>{w}</li>)}
                </ul>
              </div>
            )}
          </div>
        )

        Modal.success({
          title: dryRun ? '✅ 预览完成' : '✅ 同步完成',
          content: content,
          width: 600,
          onOk: () => !dryRun && window.location.reload(),
        })
        onSuccess?.(result)
      } else {
        throw new Error(result.message || '同步业务逻辑失败')
      }
    } catch (e: any) {
      message.error(e.message || '网络请求失败，请检查连接')
      onError?.(e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
      <Checkbox checked={dryRun} onChange={e => setDryRun(e.target.checked)}>
        仅预览
      </Checkbox>
      <Upload
        accept=".xls,.xlsx"
        showUploadList={false}
        customRequest={handleSync}
        beforeUpload={beforeUpload}
        disabled={loading}
      >
        <Button icon={<UploadOutlined />} loading={loading} type="primary">
          {loading ? '处理中...' : '同步 Excel'}
        </Button>
      </Upload>
    </div>
  )
}
