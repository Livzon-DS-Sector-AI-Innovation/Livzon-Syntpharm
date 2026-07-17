'use client'

import { useState } from 'react'
import { Drawer, Timeline, Tag, Button, Space, Card, Descriptions, Modal, Input, Select, Form, App, Empty, Divider, Row, Col } from 'antd'
import { HistoryOutlined, SwapOutlined, PlusOutlined } from '@ant-design/icons'
import {
  RdStageDeliverable, RdDeliverableStatus,
  DELIVERABLE_STATUS_LABELS,
} from '@/types/research/rd-project'
import { createDeliverable } from '@/actions/research/deliverables'

interface Props {
  open: boolean
  onClose: () => void
  projectId: string
  stage: string
  deliverableType: string
  title: string
  versions: RdStageDeliverable[]
  onRefresh: () => void
}

const statusColorMap: Record<RdDeliverableStatus, string> = {
  draft: 'default',
  in_progress: 'processing',
  completed: 'success',
  approved: 'green',
}

function parseVersion(v: string): number {
  const match = v.match(/v?(\d+)\.(\d+)/)
  if (!match) return 0
  return parseInt(match[1]) * 100 + parseInt(match[2])
}

function incrementVersion(v: string): string {
  const match = v.match(/v?(\d+)\.(\d+)/)
  if (!match) return 'v2.0'
  const major = parseInt(match[1])
  const minor = parseInt(match[2])
  return `v${major}.${minor + 1}`
}

export function VersionHistoryDrawer({ open, onClose, projectId, stage, deliverableType, title, versions, onRefresh }: Props) {
  const { message: msgApi } = App.useApp()
  const [compareMode, setCompareMode] = useState(false)
  const [compareLeft, setCompareLeft] = useState<string | null>(null)
  const [compareRight, setCompareRight] = useState<string | null>(null)
  const [newVersionModalOpen, setNewVersionModalOpen] = useState(false)
  const [newVersionForm] = Form.useForm()

  const sorted = [...versions].sort((a, b) => parseVersion(b.version) - parseVersion(a.version))
  const latest = sorted[0]

  const handleCreateNewVersion = async () => {
    if (!latest) return
    const values = await newVersionForm.validateFields()
    try {
      await createDeliverable({
        project_id: projectId,
        stage: stage as any,
        deliverable_type: deliverableType,
        title: values.title || `${title} (${values.version})`,
        status: 'draft',
        version: values.version,
        content: values.copyContent ? (latest.content || '') : '',
      })
      msgApi.success('新版本创建成功')
      setNewVersionModalOpen(false)
      newVersionForm.resetFields()
      onRefresh()
    } catch (e: any) {
      msgApi.error(e.message || '创建失败')
    }
  }

  const renderContent = (item: RdStageDeliverable | undefined) => {
    if (!item) return <Empty description="无内容" />
    return (
      <div>
        <Descriptions bordered size="small" column={2} style={{ marginBottom: 12 }}>
          <Descriptions.Item label="版本">{item.version}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={statusColorMap[item.status as RdDeliverableStatus] || 'default'}>
              {DELIVERABLE_STATUS_LABELS[item.status as RdDeliverableStatus] || item.status}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="创建时间" span={2}>{item.created_at ? new Date(item.created_at).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
          {item.file_name && (
            <Descriptions.Item label="附件" span={2}>
              <a href={item.file_url || '#'} target="_blank" rel="noopener noreferrer">{item.file_name}</a>
            </Descriptions.Item>
          )}
        </Descriptions>
        {item.content && (
          <Card size="small" title="内容">
            <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, maxHeight: 300, overflow: 'auto' }}>
              {item.content}
            </div>
          </Card>
        )}
      </div>
    )
  }

  const getFindById = (id: string) => versions.find(v => v.id === id)

  return (
    <>
      <Drawer
        title={
          <Space>
            <HistoryOutlined />
            <span>版本历史 - {title}</span>
            <Tag>{sorted.length} 个版本</Tag>
          </Space>
        }
        open={open}
        onClose={onClose}
        styles={{ wrapper: { width: 680 } }}
        extra={
          <Space>
            <Button
              icon={<SwapOutlined />}
              onClick={() => setCompareMode(!compareMode)}
              type={compareMode ? 'primary' : 'default'}
            >
              {compareMode ? '退出对比' : '版本对比'}
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                newVersionForm.setFieldsValue({
                  version: latest ? incrementVersion(latest.version) : 'v1.0',
                  copyContent: true,
                })
                setNewVersionModalOpen(true)
              }}
            >
              新版本
            </Button>
          </Space>
        }
      >
        {sorted.length === 0 ? (
          <Empty description="暂无版本记录" />
        ) : compareMode ? (
          <div>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={12}>
                <Select
                  style={{ width: '100%' }}
                  placeholder="选择版本 A"
                  value={compareLeft}
                  onChange={setCompareLeft}
                  options={sorted.map(v => ({ value: v.id, label: `${v.version} (${DELIVERABLE_STATUS_LABELS[v.status as RdDeliverableStatus] || v.status})` }))}
                />
              </Col>
              <Col span={12}>
                <Select
                  style={{ width: '100%' }}
                  placeholder="选择版本 B"
                  value={compareRight}
                  onChange={setCompareRight}
                  options={sorted.map(v => ({ value: v.id, label: `${v.version} (${DELIVERABLE_STATUS_LABELS[v.status as RdDeliverableStatus] || v.status})` }))}
                />
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <Card size="small" title="版本 A" styles={{ body: { maxHeight: 500, overflow: 'auto' } }}>
                  {compareLeft ? renderContent(getFindById(compareLeft)) : <Empty description="请选择" />}
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small" title="版本 B" styles={{ body: { maxHeight: 500, overflow: 'auto' } }}>
                  {compareRight ? renderContent(getFindById(compareRight)) : <Empty description="请选择" />}
                </Card>
              </Col>
            </Row>
          </div>
        ) : (
          <Timeline
            items={sorted.map((item, idx) => ({
              color: idx === 0 ? 'green' : 'blue',
              children: (
                <Card
                  size="small"
                  title={
                    <Space>
                      <span style={{ fontWeight: 600 }}>{item.version}</span>
                      {idx === 0 && <Tag color="green">最新版</Tag>}
                      <Tag color={statusColorMap[item.status as RdDeliverableStatus] || 'default'}>
                        {DELIVERABLE_STATUS_LABELS[item.status as RdDeliverableStatus] || item.status}
                      </Tag>
                    </Space>
                  }
                  extra={
                    <span style={{ fontSize: 12, color: '#999' }}>
                      {item.created_at ? new Date(item.created_at).toLocaleString('zh-CN') : ''}
                    </span>
                  }
                  style={{ marginBottom: 8 }}
                >
                  {item.content ? (
                    <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, maxHeight: 120, overflow: 'auto' }}>
                      {item.content}
                    </div>
                  ) : (
                    <span style={{ color: '#999' }}>无内容</span>
                  )}
                  {item.file_name && (
                    <div style={{ marginTop: 8, fontSize: 12 }}>
                      📎 {item.file_name}
                    </div>
                  )}
                </Card>
              ),
            }))}
          />
        )}
      </Drawer>

      <Modal
        title="创建新版本"
        open={newVersionModalOpen}
        onOk={handleCreateNewVersion}
        onCancel={() => { setNewVersionModalOpen(false); newVersionForm.resetFields() }}
      >
        <Form form={newVersionForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="version" label="版本号" rules={[{ required: true }]}>
            <Input placeholder="如 v2.0" />
          </Form.Item>
          <Form.Item name="title" label="标题（可选）">
            <Input placeholder="留空则自动生成" />
          </Form.Item>
          <Form.Item name="copyContent" label="复制上一版内容" valuePropName="checked">
            <Select options={[{ value: true, label: '是 - 基于上一版修改' }, { value: false, label: '否 - 空白新版本' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
