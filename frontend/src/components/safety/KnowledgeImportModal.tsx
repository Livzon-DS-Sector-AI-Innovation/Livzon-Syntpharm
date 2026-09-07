'use client'

import { useState } from 'react'
import { Modal, Upload, Button, Select, App, Progress, Tag, Space } from 'antd'
import { InboxOutlined, FileTextOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import type { UploadFile } from 'antd/es/upload/interface'
import { batchImportKnowledgeArticles } from '@/actions/safety'

const { Dragger } = Upload

interface ImportResult {
  filename: string
  status: 'success' | 'error' | 'skipped'
  message?: string
  article_id?: string
  title?: string
  category?: string
}

interface KnowledgeImportModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

const CATEGORY_OPTIONS = [
  { value: '', label: '自动推断' },
  { value: 'laws_regulations', label: '法律法规' },
  { value: 'standards', label: '标准规范' },
  { value: 'management_systems', label: '管理制度' },
  { value: 'accident_cases', label: '事故案例' },
  { value: 'emergency_plans', label: '应急预案' },
  { value: 'sds', label: '化学品安全技术说明书' },
  { value: 'training_materials', label: '培训教材' },
  { value: 'other', label: '其他' },
]

const ACCEPTED_FORMATS = '.pdf,.docx,.doc,.xlsx,.xls,.txt,.md'

export default function KnowledgeImportModal({
  open,
  onClose,
  onSuccess,
}: KnowledgeImportModalProps) {
  const { message } = App.useApp()
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [category, setCategory] = useState<string>('')
  const [importing, setImporting] = useState(false)
  const [results, setResults] = useState<ImportResult[] | null>(null)

  const handleImport = async () => {
    if (fileList.length === 0) {
      message.warning('请先选择文件')
      return
    }

    setImporting(true)
    setResults(null)

    try {
      const files = fileList.map(f => {
        console.log('File object:', f)
        console.log('originFileObj:', f.originFileObj)
        return f.originFileObj as File
      })
      
      console.log('Files to upload:', files)
      console.log('Category:', category)
      
      const response = await batchImportKnowledgeArticles(files, category || undefined)
      console.log('Response:', response)

      if (response.code === 200) {
        setResults(response.data.results)
        const summary = response.data.summary
        message.success(`导入完成：成功 ${summary.success} 篇，失败 ${summary.error} 篇`)
        onSuccess()
      } else {
        message.error(response.message || '导入失败')
      }
    } catch (error) {
      console.error('Import error:', error)
      message.error('导入失败，请重试')
    } finally {
      setImporting(false)
    }
  }

  const handleClose = () => {
    setFileList([])
    setCategory('')
    setResults(null)
    onClose()
  }

  const successCount = results?.filter(r => r.status === 'success').length || 0
  const errorCount = results?.filter(r => r.status === 'error' || r.status === 'skipped').length || 0

  return (
    <Modal
      title="导入知识文档"
      open={open}
      onCancel={handleClose}
      width={700}
      footer={[
        <Button key="cancel" onClick={handleClose}>
          取消
        </Button>,
        <Button
          key="import"
          type="primary"
          onClick={handleImport}
          loading={importing}
          disabled={fileList.length === 0}
        >
          开始导入
        </Button>,
      ]}
    >
      <div style={{ marginBottom: 16 }}>
        <div style={{ marginBottom: 8, fontWeight: 500 }}>选择分类：</div>
        <Select
          value={category}
          onChange={setCategory}
          style={{ width: '100%' }}
          options={CATEGORY_OPTIONS}
          placeholder="选择分类（可选，不选则自动推断）"
        />
      </div>

      {!results ? (
        <Dragger
          multiple
          fileList={fileList}
          onChange={({ fileList }) => setFileList(fileList)}
          beforeUpload={() => false}
          accept={ACCEPTED_FORMATS}
          maxCount={20}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此区域</p>
          <p className="ant-upload-hint">
            支持 PDF、Word、Excel、TXT 格式，单次最多 20 个文件
          </p>
        </Dragger>
      ) : (
        <div>
          <div style={{ marginBottom: 16, padding: '12px 16px', background: '#f6f5f4', borderRadius: 8 }}>
            <Space>
              <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 18 }} />
              <span>成功导入 <strong>{successCount}</strong> 篇</span>
              {errorCount > 0 && (
                <>
                  <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 18, marginLeft: 16 }} />
                  <span>失败 <strong>{errorCount}</strong> 篇</span>
                </>
              )}
            </Space>
          </div>

          <div style={{ maxHeight: 300, overflowY: 'auto' }}>
            {results.map((result, index) => (
              <div
                key={index}
                style={{
                  padding: '8px 12px',
                  marginBottom: 8,
                  background: result.status === 'success' ? '#f6ffed' : '#fff2f0',
                  borderRadius: 6,
                  border: `1px solid ${result.status === 'success' ? '#b7eb8f' : '#ffccc7'}`,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <FileTextOutlined />
                  <span style={{ flex: 1 }}>{result.filename}</span>
                  <Tag color={result.status === 'success' ? 'success' : 'error'}>
                    {result.status === 'success' ? '成功' : result.status === 'skipped' ? '跳过' : '失败'}
                  </Tag>
                </div>
                {result.status === 'success' && result.title && (
                  <div style={{ marginTop: 4, fontSize: 12, color: '#666' }}>
                    标题：{result.title} | 分类：{result.category}
                  </div>
                )}
                {result.message && (
                  <div style={{ marginTop: 4, fontSize: 12, color: '#ff4d4f' }}>
                    {result.message}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </Modal>
  )
}
