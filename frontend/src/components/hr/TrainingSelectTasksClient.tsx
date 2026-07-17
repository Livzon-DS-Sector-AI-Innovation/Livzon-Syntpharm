'use client'

import { useState } from 'react'
import { Button, Card, Table, Tag, Space, Modal, Input, message } from 'antd'
import { ReloadOutlined, ImportOutlined, LinkOutlined, CopyOutlined } from '@ant-design/icons'
import { fetchTrainingSelectTasks, fetchTrainingSelectTaskResult } from '@/lib/api/client/hr'
import Link from 'next/link'

interface TaskItem {
  token: string
  department: string
  training_date: string
  subject: string
  factory: string
  location: string
  
  trainer: string
  training_method: string
  has_result: boolean
  selected_count: number
  created_at: string
}

interface TrainingSelectTasksClientProps {
  initialTasks: TaskItem[]
}

export default function TrainingSelectTasksClient({ initialTasks }: TrainingSelectTasksClientProps) {
  const [tasks, setTasks] = useState<TaskItem[]>(initialTasks)
  const [loading, setLoading] = useState(false)
  const [tokenInput, setTokenInput] = useState('')
  const [importModalOpen, setImportModalOpen] = useState(false)

  const loadTasks = async () => {
    setLoading(true)
    try {
      const res = await fetchTrainingSelectTasks("default")
      setTasks(res.data || [])
    } catch (err: any) {
      message.error(err.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  const handleImportByToken = async () => {
    if (!tokenInput.trim()) {
      message.warning('请输入任务令牌')
      return
    }
    try {
      const res = await fetchTrainingSelectTaskResult(tokenInput.trim())
      const task = res.data
      if (!task?.employee_numbers?.length) {
        message.warning('该任务尚未提交选择结果')
        return
      }
      // 跳转到培训通知页面，带 token 参数
      const url = `/hr/training/notification?token=${tokenInput.trim()}`
      window.location.href = url
    } catch (err: any) {
      message.error(err.message || '导入失败')
    }
  }

  const columns = [
    {
      title: '培训日期',
      dataIndex: 'training_date',
      key: 'training_date',
      width: 120,
    },
    {
      title: '培训主题',
      dataIndex: 'subject',
      key: 'subject',
      ellipsis: true,
    },
    {
      title: '主办部门',
      dataIndex: 'department',
      key: 'department',
      width: 140,
    },
    {
      title: '厂区',
      dataIndex: 'factory',
      key: 'factory',
      width: 80,
      render: (v: string) => (v === 'new' ? '新厂' : '旧厂'),
    },
    {
      title: '状态',
      key: 'status',
      width: 120,
      render: (_: any, record: TaskItem) =>
        record.has_result ? (
          <Tag color="green">已选择 ({record.selected_count}人)</Tag>
        ) : (
          <Tag color="orange">等待选择</Tag>
        ),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: any, record: TaskItem) => (
        <Space>
          {record.has_result && (
            <Link href={`/hr/training/notification?token=${record.token}`}>
              <Button type="primary" size="small" icon={<ImportOutlined />}>
                回填
              </Button>
            </Link>
          )}
          <Button
            size="small"
            icon={<CopyOutlined />}
            onClick={() => {
              const url = `${window.location.origin}/hr/training/select?token=${record.token}`
              navigator.clipboard.writeText(url)
              message.success('链接已复制')
            }}
          >
            复制链接
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadTasks} loading={loading}>
            刷新
          </Button>
          <Button onClick={() => setImportModalOpen(true)}>通过令牌导入</Button>
        </Space>
      </div>

      <Card>
        <Table
          dataSource={tasks}
          columns={columns}
          rowKey="token"
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: '暂无培训选择任务' }}
        />
      </Card>

      <Modal
        title="通过令牌导入选择结果"
        open={importModalOpen}
        onOk={handleImportByToken}
        onCancel={() => setImportModalOpen(false)}
        okText="导入并回填"
      >
        <p className="text-gray-500 mb-2">输入任务令牌（token），将选择结果回填到培训通知页面。</p>
        <Input
          placeholder="粘贴任务令牌"
          value={tokenInput}
          onChange={(e) => setTokenInput(e.target.value)}
        />
      </Modal>
    </div>
  )
}
