'use client'
import { updateDeviationTask, updateDeviationTaskFields, submitDeviationApproval, updateAIResult, generateStandard } from '@/actions/quality'

import { useState, useEffect, useRef } from 'react'
import { use } from 'react'
import {
  Card,
  Button,
  Space,
  Tabs,
  message,
  Spin,
  Divider,
  Descriptions,
  Tag,
  Alert,
} from 'antd'
import {
  DownloadOutlined,
  SaveOutlined,
  ArrowLeftOutlined,
  EyeOutlined,
  EditOutlined,
  RobotOutlined,
} from '@ant-design/icons'
import { useRouter } from 'next/navigation'

const API_BASE = '/api/v1'

interface TaskDetail {
  task_id: number
  deviation_no: string
  creator: string
  auditor: string | null
  report_date: string
  original_file_path: string
  standard_file_path: string | null
  task_status: number
  ai_result: string | null
  create_time: string
}

interface PreviewData {
  task_id: number
  html_content: string
  plain_content: string
}

export default function PreviewPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const resolvedParams = use(params)
  const taskId = parseInt(resolvedParams.id)
  const router = useRouter()
  const iframeRef = useRef<HTMLIFrameElement>(null)

  const [loading, setLoading] = useState(true)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [task, setTask] = useState<TaskDetail | null>(null)
  const [previewData, setPreviewData] = useState<PreviewData | null>(null)
  const [editableContent, setEditableContent] = useState('')
  const [isEdited, setIsEdited] = useState(false)
  const [saving, setSaving] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [activeTab, setActiveTab] = useState('preview')
  const editableRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchTaskDetail()
  }, [taskId])

  useEffect(() => {
    if (task?.ai_result) {
      fetchPreview()
    }
  }, [task])

  const fetchTaskDetail = async () => {
    try {
      const response = await fetch(
        `${API_BASE}/quality/deviation-automation/tasks/${taskId}`
      )
      if (!response.ok) throw new Error('获取任务详情失败')
      const result = await response.json()
      setTask(result.data)
    } catch (error: any) {
      message.error(error.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchPreview = async () => {
    setPreviewLoading(true)
    try {
      const response = await fetch(
        `${API_BASE}/quality/deviation-automation/tasks/${taskId}/preview`
      )
      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || '获取预览失败')
      }
      const result = await response.json()
      setPreviewData(result.data)
      setEditableContent(result.data.plain_content || '')
      setIsEdited(false)
    } catch (error: any) {
      message.error(error.message || '获取预览失败')
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleContentChange = () => {
    if (editableRef.current) {
      setEditableContent(editableRef.current.innerHTML)
      setIsEdited(true)
    }
  }

  const handleSave = async () => {
    if (!task) return
    setSaving(true)
    try {
      await updateAIResult(taskId, editableContent)
      message.success('保存成功')
      setIsEdited(false)
      await fetchTaskDetail()
    } catch (error: any) {
      message.error(error.message || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleGenerateStandard = async () => {
    if (!task || !previewData) return
    setGenerating(true)
    try {
      // 先保存当前编辑的内容
      await updateAIResult(taskId, previewData.plain_content)

      const response = await generateStandard(taskId)
      if (!response) {
        throw new Error('生成失败')
      }
      message.success('标准文件生成成功')
      await fetchTaskDetail()
    } catch (error: any) {
      message.error(error.message || '生成失败')
    } finally {
      setGenerating(false)
    }
  }

  const handleDownloadStandard = () => {
    if (!task?.standard_file_path) {
      message.warning('标准报告文件尚未生成')
      return
    }
    window.open(
      `${API_BASE}/quality/deviation-automation/tasks/${taskId}/download/standard`,
      '_blank'
    )
  }

  const handleDownloadOriginal = () => {
    window.open(
      `${API_BASE}/quality/deviation-automation/tasks/${taskId}/download/original`,
      '_blank'
    )
  }

  const getStatusText = (status: number) => {
    const statusMap: Record<number, string> = {
      1: '待处理',
      2: 'AI处理中',
      3: '已生成',
      4: '已完成',
    }
    return statusMap[status] || '未知'
  }

  const getStatusColor = (status: number) => {
    const colorMap: Record<number, string> = {
      1: 'default',
      2: 'processing',
      3: 'success',
      4: 'blue',
    }
    return colorMap[status] || 'default'
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>加载中...</div>
      </div>
    )
  }

  if (!task) {
    return (
      <div style={{ padding: 24 }}>
        <Card>
          <div style={{ textAlign: 'center', color: '#999' }}>任务不存在</div>
        </Card>
      </div>
    )
  }

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={`报告预览 - ${task.deviation_no}`}
        extra={
          <Space>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => router.push('/quality/deviation-automation/history')}
            >
              返回
            </Button>
            <Button icon={<DownloadOutlined />} onClick={handleDownloadOriginal}>
              原始文件
            </Button>
            <Button icon={<SaveOutlined />} onClick={handleSave} loading={saving}>
              保存修改
            </Button>
            <Button
              icon={<RobotOutlined />}
              onClick={handleGenerateStandard}
              loading={generating}
              disabled={!task.ai_result}
            >
              AI生成标准报告
            </Button>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={handleDownloadStandard}
              disabled={!task.standard_file_path}
            >
              下载标准报告
            </Button>
          </Space>
        }
      >
        {/* 基础信息 */}
        <Card
          title="任务信息"
          size="small"
          style={{ marginBottom: 16 }}
          extra={
            <Tag color={getStatusColor(task.task_status)}>
              {getStatusText(task.task_status)}
            </Tag>
          }
        >
          <Descriptions size="small" column={4}>
            <Descriptions.Item label="偏差编号">
              <strong>{task.deviation_no}</strong>
            </Descriptions.Item>
            <Descriptions.Item label="编制人">{task.creator}</Descriptions.Item>
            <Descriptions.Item label="审核人">{task.auditor || '-'}</Descriptions.Item>
            <Descriptions.Item label="编制日期">{task.report_date}</Descriptions.Item>
          </Descriptions>
        </Card>

        {/* 预览/编辑切换 */}
        <Tabs
          activeKey={activeTab}
          onChange={(key) => {
            setActiveTab(key)
            // 切换到预览时刷新
            if (key === 'preview' && task?.ai_result) {
              fetchPreview()
            }
          }}
          items={[
            {
              key: 'preview',
              label: (
                <span>
                  <EyeOutlined /> 预览视图
                </span>
              ),
              children: (
                <Card
                  size="small"
                  title="标准报告预览"
                  extra={
                    <Button size="small" onClick={fetchPreview} loading={previewLoading}>
                      刷新
                    </Button>
                  }
                  style={{
                    background: '#fff',
                    minHeight: 600,
                    border: '1px solid #f0f0f0',
                  }}
                  styles={{ body: { padding: 0 } }}
                >
                  {task.ai_result ? (
                    previewLoading ? (
                      <div style={{ textAlign: 'center', padding: 60 }}>
                        <Spin size="large" />
                        <div style={{ marginTop: 16 }}>加载预览中...</div>
                      </div>
                    ) : previewData?.plain_content ? (
                      <iframe
                        ref={iframeRef}
                        srcDoc={previewData.plain_content}
                        style={{
                          width: '100%',
                          minHeight: 600,
                          border: 'none',
                          display: 'block',
                        }}
                        title="报告预览"
                      />
                    ) : (
                      <div style={{ textAlign: 'center', color: '#999', padding: 60 }}>
                        预览加载失败，请点击刷新按钮重试
                      </div>
                    )
                  ) : (
                    <div style={{ textAlign: 'center', color: '#999', padding: 60 }}>
                      暂无AI处理结果，请先在新建报告页面触发AI处理
                    </div>
                  )}
                </Card>
              ),
            },
            {
              key: 'edit',
              label: (
                <span>
                  <EditOutlined /> 编辑文本
                  {isEdited && <span style={{ color: '#ff4d4f', marginLeft: 4 }}>*</span>}
                </span>
              ),
              children: (
                <Card
                  title={
                    <span>
                      报告内容编辑（所见即所得）
                      {isEdited && <span style={{ color: '#ff4d4f', fontSize: 12, marginLeft: 8 }}>已修改</span>}
                    </span>
                  }
                  size="small"
                  extra={
                    <Button
                      type="primary"
                      size="small"
                      onClick={handleSave}
                      loading={saving}
                      disabled={!isEdited}
                    >
                      保存修改
                    </Button>
                  }
                >
                  {task.ai_result ? (
                    previewLoading ? (
                      <div style={{ textAlign: 'center', padding: 60 }}>
                        <Spin size="large" />
                        <div style={{ marginTop: 16 }}>加载中...</div>
                      </div>
                    ) : (
                      <div
                        ref={editableRef}
                        contentEditable
                        suppressContentEditableWarning
                        onBlur={handleContentChange}
                        style={{
                          border: '1px solid #d9d9d9',
                          borderRadius: 4,
                          minHeight: 500,
                          padding: 20,
                          background: '#fff',
                          outline: 'none',
                          lineHeight: 1.8,
                        }}
                        dangerouslySetInnerHTML={{
                          __html: editableContent || previewData?.plain_content || '',
                        }}
                      />
                    )
                  ) : (
                    <div style={{ textAlign: 'center', color: '#999', padding: 60 }}>
                      暂无AI处理结果，请先在新建报告页面触发AI处理
                    </div>
                  )}
                </Card>
              ),
            },
          ]}
        />

        {/* 操作提示 */}
        <div style={{ marginTop: 16, padding: '12px 16px', background: '#fafafa', borderRadius: 4, fontSize: 13 }}>
          <strong>操作提示：</strong>
          <ul style={{ margin: '8px 0', paddingLeft: 20 }}>
            <li>在「编辑文本」中可直接编辑报告内容，修改后点击「保存修改」</li>
            <li>在「预览视图」中查看标准格式预览效果</li>
            <li>点击「AI生成标准报告」可生成正式Word文件</li>
            <li>生成后点击「下载标准报告」获取文件</li>
          </ul>
        </div>
      </Card>
    </div>
  )
}
