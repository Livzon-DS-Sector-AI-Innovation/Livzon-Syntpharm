'use client'

import { useState, type CSSProperties } from 'react'
import {
  Alert, App, Button, Drawer, Form, Input, Modal, Popconfirm, Space, Switch, Table, Tag, Typography,
} from 'antd'
import type { TableProps } from 'antd'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { deleteReportGenExample, updateReportGenExample } from '@/actions/research/report-gen'
import { fetchTemplateExamples } from '@/lib/api/client/research/report-gen'
import type { ReportGenExample } from '@/types/research/report-gen'

interface Props {
  open: boolean
  templateId: string | null
  templateName: string
  onClose: () => void
}

const drawerStyles: { wrapper: CSSProperties } = { wrapper: { width: '68vw' } }

/** 示例的来源口径：追查「这条正确答案是谁给的」 */
const SOURCE_META: Record<string, { label: string; color: string }> = {
  manual_edit: { label: '人工修正', color: 'green' },
  agent_filled: { label: '模型填充', color: 'default' },
  feedback_promoted: { label: '意见沉淀', color: 'blue' },
}

interface EditValues {
  value: string
  evidence_text: string
}

/**
 * 槽位示例库（右侧抽屉）。
 *
 * 示例是「下次生成照这个写法填」的 few-shot 参照，来源只有两条：人工在详情页改值，
 * 或把已落实的评审意见沉淀下来。这里让人看见全集、停用错例、补一句依据——
 * 在此之前示例只能被写入，写错了没人能撤，错法就会被一次次固化。
 */
export function ReportGenExampleDrawer({ open, templateId, templateName, onClose }: Props) {
  const { message: msgApi } = App.useApp()
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState<ReportGenExample | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm<EditValues>()

  const { data, isLoading, error } = useQuery({
    queryKey: ['template-examples', templateId],
    queryFn: () => fetchTemplateExamples(templateId as string),
    enabled: open && Boolean(templateId),
    staleTime: 0,
    gcTime: 0,
    retry: false,
  })

  const items = data?.items ?? []
  const activeTotal = data?.active_total ?? 0

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['template-examples', templateId] })

  const toggleActive = async (row: ReportGenExample, next: boolean) => {
    try {
      await updateReportGenExample(row.id, { is_active: next })
      msgApi.success(next ? '已启用，下次生成会参考它' : '已停用，不再注入下次生成')
      void refresh()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '更新失败')
    }
  }

  const handleDelete = async (row: ReportGenExample) => {
    try {
      await deleteReportGenExample(row.id)
      msgApi.success('已删除')
      void refresh()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '删除失败')
    }
  }

  const openEdit = (row: ReportGenExample) => {
    setEditing(row)
    form.setFieldsValue({ value: row.value, evidence_text: row.evidence_text ?? '' })
  }

  const submitEdit = async () => {
    if (!editing) return
    const values = await form.validateFields()
    setSaving(true)
    try {
      await updateReportGenExample(editing.id, {
        value: values.value,
        evidence_text: values.evidence_text,
      })
      msgApi.success('已保存')
      setEditing(null)
      void refresh()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const columns: TableProps<ReportGenExample>['columns'] = [
    {
      title: '槽位',
      dataIndex: 'slot_key',
      width: 190,
      render: (_: unknown, row) => (
        <div>
          <div>{row.slot_label || row.slot_key}</div>
          <Typography.Text type="secondary" style={{ fontFamily: 'monospace', fontSize: 12 }}>
            {row.slot_key}
          </Typography.Text>
        </div>
      ),
    },
    {
      title: '示例写法',
      dataIndex: 'value',
      render: (value: string) => (
        <Typography.Paragraph ellipsis={{ rows: 2, tooltip: value }} style={{ marginBottom: 0 }}>
          {value}
        </Typography.Paragraph>
      ),
    },
    {
      title: '依据',
      dataIndex: 'evidence_text',
      width: 190,
      render: (value: string | null) =>
        value ? (
          <Typography.Paragraph ellipsis={{ rows: 2, tooltip: value }} style={{ marginBottom: 0, fontSize: 12 }}>
            {value}
          </Typography.Paragraph>
        ) : (
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            未填
          </Typography.Text>
        ),
    },
    {
      title: '来源',
      dataIndex: 'source',
      width: 100,
      render: (value: string) => {
        const meta = SOURCE_META[value] ?? { label: value, color: 'default' }
        return <Tag color={meta.color}>{meta.label}</Tag>
      },
    },
    {
      title: '引用',
      dataIndex: 'usage_count',
      width: 70,
      render: (value: number) => `${value} 次`,
    },
    {
      title: '启用',
      dataIndex: 'is_active',
      width: 80,
      render: (value: boolean, row) => (
        <Switch size="small" checked={value} onChange={(next) => void toggleActive(row, next)} />
      ),
    },
    {
      title: '操作',
      width: 120,
      render: (_: unknown, row) => (
        <Space size={4}>
          <Button type="link" size="small" style={{ padding: 0 }} onClick={() => openEdit(row)}>
            编辑
          </Button>
          <Popconfirm
            title="删除这条示例？"
            description="删除后不再参与生成；停用则保留记录可追。"
            okText="删除"
            cancelText="取消"
            onConfirm={() => void handleDelete(row)}
          >
            <Button type="link" size="small" danger style={{ padding: 0 }}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <Drawer
      title={`槽位示例：${templateName}`}
      open={open}
      onClose={onClose}
      destroyOnHidden
      styles={drawerStyles}
    >
      <Alert
        type="info"
        showIcon
        title="示例是下次生成要照抄的写法"
        description="来源只有人工修正与评审意见沉淀两种。写错了就停用或删除，否则同一处错法会被一次次教给模型。"
        style={{ marginBottom: 12 }}
      />
      <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 8, fontSize: 12 }}>
        共 {items.length} 条，启用 {activeTotal} 条（只有启用的会被注入下一次生成）
      </Typography.Text>
      <Table<ReportGenExample>
        rowKey="id"
        size="small"
        loading={isLoading}
        columns={columns}
        dataSource={items}
        pagination={false}
        scroll={{ x: 880 }}
        locale={{ emptyText: error instanceof Error ? error.message : '该模板还没有沉淀示例' }}
      />
      <Modal
        title={`编辑示例：${editing?.slot_label || editing?.slot_key || ''}`}
        open={Boolean(editing)}
        onCancel={() => setEditing(null)}
        onOk={() => void submitEdit()}
        confirmLoading={saving}
        okText="保存"
        cancelText="取消"
        destroyOnHidden
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            name="value"
            label="示例写法"
            rules={[{ required: true, message: '示例写法不能为空；要撤掉就停用这条示例' }]}
          >
            <Input.TextArea rows={4} placeholder="这一处应该怎么写" />
          </Form.Item>
          <Form.Item name="evidence_text" label="依据" extra="写清为什么这么写，下次有人质疑时不用重新查">
            <Input.TextArea rows={3} placeholder="可选：出处、评审意见原文" />
          </Form.Item>
        </Form>
      </Modal>
    </Drawer>
  )
}