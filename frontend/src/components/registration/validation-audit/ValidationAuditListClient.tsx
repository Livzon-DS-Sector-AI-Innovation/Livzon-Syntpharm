'use client'

import { useState, useCallback } from 'react'
import {Table, Space, App} from 'antd'
import { useRouter } from 'next/navigation'
import dayjs from 'dayjs'
import type { ValidationAuditTaskListItem, TaskStatus, AuditMode } from '@/types/validation-audit'
import {
  AUDIT_MODE_LABELS, STATUS_LABELS, CONCLUSION_LABELS,
} from '@/types/validation-audit'
import { deleteValidationAuditTask } from '@/actions/validation-audit'
import { RegistrationPageHeader } from '../RegistrationPageHeader'
import { tagClassOf } from '../registration-ui'
import ui from '../registration-ui.module.css'
import { IconCheckSquare, IconPlus, IconTrash } from '../registration-icons'

interface Props {
  initialTasks: ValidationAuditTaskListItem[]
  initialTotal: number
}

export default function ValidationAuditListClient({ initialTasks, initialTotal }: Props) {
  const { message, modal } = App.useApp()
  const router = useRouter()
  const [tasks, setTasks] = useState(initialTasks)
  const [total, setTotal] = useState(initialTotal)
  const [loading, _setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  const handleDelete = useCallback((taskId: string, taskName: string) => {
    modal.confirm({
      title: '确认删除',
      content: `确定要删除审核任务「${taskName}」吗？关联的文件、问题和报告将一并删除。`,
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        const result = await deleteValidationAuditTask(taskId)
        if (result.success) {
          message.success(result.message)
          setTasks(prev => prev.filter(t => t.id !== taskId))
          setTotal(prev => prev - 1)
        } else {
          message.error(result.message)
        }
      },
    })
  }, [modal, message])

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'task_name',
      key: 'task_name',
      width: 200,
      ellipsis: true,
    },
    {
      title: '品种',
      dataIndex: 'product_name',
      key: 'product_name',
      width: 150,
      ellipsis: true,
    },
    {
      title: '来源公司',
      dataIndex: 'source_company',
      key: 'source_company',
      width: 160,
      ellipsis: true,
    },
    {
      title: '审核模式',
      dataIndex: 'audit_mode',
      key: 'audit_mode',
      width: 140,
      render: (mode: AuditMode) => AUDIT_MODE_LABELS[mode] || mode,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: TaskStatus) => {
        const cfg = STATUS_LABELS[status]
        return cfg ? <span className={tagClassOf(cfg.color)}>{cfg.label}</span> : status
      },
    },
    {
      title: '审核结论',
      dataIndex: 'conclusion',
      key: 'conclusion',
      width: 110,
      render: (conclusion: string | null) => {
        if (!conclusion) return <span style={{ color: 'var(--ink-3)' }}>—</span>
        const cfg = CONCLUSION_LABELS[conclusion as keyof typeof CONCLUSION_LABELS]
        return cfg ? <span className={tagClassOf(cfg.color)}>{cfg.label}</span> : conclusion
      },
    },
    {
      title: '问题数',
      key: 'issues',
      width: 140,
      render: (_: unknown, record: ValidationAuditTaskListItem) => (
        <Space size={6}>
          {record.serious_count > 0 && <span className={ui.tagRisk}>{record.serious_count} 严重</span>}
          {record.general_count > 0 && <span className={ui.tagWarn}>{record.general_count} 一般</span>}
          {record.suggestion_count > 0 && <span className={ui.tagInfo}>{record.suggestion_count} 建议</span>}
          {record.serious_count + record.general_count + record.suggestion_count === 0 && (
            <span style={{ color: 'var(--ink-3)' }}>—</span>
          )}
        </Space>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (val: string) => dayjs(val).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 160,
      fixed: 'right' as const,
      render: (_: unknown, record: ValidationAuditTaskListItem) => (
        <Space size={0}>
          <button
            type="button"
            className={ui.opLink}
            onClick={() => router.push(`/registration/validation-audit/${record.id}`)}
          >
            查看
          </button>
          <button
            type="button"
            className={ui.opDel}
            title="删除"
            onClick={() => handleDelete(record.id, record.task_name)}
          >
            {IconTrash}
          </button>
        </Space>
      ),
    },
  ]

  return (
    <div className={ui.regUi}>
      <RegistrationPageHeader
        icon={IconCheckSquare}
        title="验证审计"
        sub="上传验证方案/报告，AI 自动审核合规性"
        actions={
          <button
            type="button"
            className={ui.btnPrimary}
            onClick={() => router.push('/registration/validation-audit/new')}
          >
            {IconPlus}
            新建审核任务
          </button>
        }
      />

      <div className={ui.panel}>
        <div className={`${ui.tableWrap} ${ui.tableStd}`}>
          <Table
            columns={columns}
            dataSource={tasks}
            rowKey="id"
            loading={loading}
            pagination={{
              current: page,
              pageSize,
              total,
              showSizeChanger: true,
              showTotal: (t) => `共 ${t} 条`,
              onChange: (p, ps) => { setPage(p); setPageSize(ps) },
            }}
            scroll={{ x: 1200 }}
            size="middle"
          />
        </div>
      </div>
    </div>
  )
}
