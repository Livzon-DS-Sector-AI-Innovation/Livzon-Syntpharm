'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Alert, App, Button, Drawer, Form, Input, Select, Space, Switch, Table, Tag, Tooltip } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import {
  fetchDeliverableTemplateAnchorCandidates,
  type DocGenAnchorCandidate,
} from '@/lib/api/client/research/doc-gen'
import { addDeliverableTemplateSlot } from '@/actions/research/doc-gen'

interface Props {
  open: boolean
  /** 目标模板 ID；关闭抽屉时为 null */
  templateId: string | null
  templateName: string
  onClose: () => void
  /** 新增填写项成功后模板的填充项清单已变化，通知父组件刷新 */
  onChanged: () => void
}

/** 候选位置类型的展示文案与颜色 */
const KIND_META: Record<DocGenAnchorCandidate['kind'], { label: string; color: string }> = {
  field: { label: '字段', color: 'blue' },
  paragraph: { label: '段落', color: 'green' },
  table: { label: '表格', color: 'orange' },
  image: { label: '图片', color: 'purple' },
}

const EXPECTS_OPTIONS = [
  { value: 'text', label: '文本' },
  { value: 'number', label: '数值' },
  { value: 'date', label: '日期' },
  { value: 'percent', label: '百分比' },
]

/** 锚点 JSON 作行键：后端按锚点签名去重候选，天然唯一且刷新后稳定 */
const anchorKey = (candidate: DocGenAnchorCandidate) => JSON.stringify(candidate.anchor)

/**
 * 人工「新增填写项」：点选母本里一个尚未被占用的候选锚点位置，补名称与检索语义。
 *
 * 渲染安全铁律：锚点由后端规则扫描器产出，前端只把候选的 ``anchor`` 原样回传，
 * 绝不手写或改写——锚点错则渲染失败。表格类候选随响应携带 ``columns``/``header_rows``
 * （列定义来自真实表头），点选后原样回传即可整表成槽；草拟漏识别的表格与
 * 占位符单元格都会出现在候选里，不再没有补录出口。新增结果回写模板的填充项规格，
 * 该模板以后每次 AI 生成都包含这个填写项。
 */
export function DeliverableTemplateAddSlotDrawer({ open, templateId, templateName, onClose, onChanged }: Props) {
  const { message: msgApi } = App.useApp()
  const [form] = Form.useForm()
  /** 当前选中候选的锚点签名；null 表示尚未选择 */
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const { data: candidates = [], isLoading, refetch } = useQuery({
    queryKey: ['deliverable-template-anchor-candidates', templateId],
    queryFn: async () => {
      if (!templateId) return []
      try {
        return await fetchDeliverableTemplateAnchorCandidates(templateId)
      } catch (e: unknown) {
        msgApi.error(e instanceof Error ? e.message : '加载候选位置失败')
        return []
      }
    },
    enabled: open && templateId !== null,
  })

  const selected = candidates.find((c) => anchorKey(c) === selectedKey) ?? null

  const selectCandidate = (candidate: DocGenAnchorCandidate) => {
    setSelectedKey(anchorKey(candidate))
    // 名称预填候选标签，用户可改
    form.setFieldsValue({ label: candidate.label })
  }

  const handleClose = () => {
    // 抽屉带 destroyOnHidden，关闭前先清选中与表单，下次打开是干净状态
    setSelectedKey(null)
    form.resetFields()
    onClose()
  }

  const handleSubmit = async () => {
    if (!templateId || !selected || submitting) return
    let values
    try {
      values = await form.validateFields()
    } catch {
      msgApi.warning('请检查表单必填项后再提交')
      return
    }
    setSubmitting(true)
    try {
      const result = await addDeliverableTemplateSlot(templateId, {
        anchor: selected.anchor,
        label: values.label,
        kind: selected.kind,
        expects: values.expects,
        required: values.required ?? false,
        query_hint: (values.query_hint ?? '').trim(),
        search_terms: values.search_terms?.length ? values.search_terms : undefined,
        // 表格候选：列定义与表头行数来自后端扫描的真实表头，原样回传整表成槽；
        // 非表格 kind 后端忽略这两项
        columns: selected.kind === 'table' ? (selected.columns ?? []) : undefined,
        header_rows: selected.header_rows ?? 1,
      })
      msgApi.success(`已新增填写项「${values.label}」（${result.slot_key}），当前共 ${result.total_slots} 个填写项`)
      setSelectedKey(null)
      form.resetFields()
      onChanged()
      // 刚加的位置已被占用，重拉候选（后端按锚点签名过滤）
      void refetch()
    } catch (e: unknown) {
      // 后端 400（位置已被占用 / 名称为空 / 表格缺列定义）会带具体文案，直接透出
      msgApi.error(e instanceof Error ? e.message : '新增填写项失败')
    } finally {
      setSubmitting(false)
    }
  }

  const columns = [
    {
      title: '位置',
      key: 'label',
      width: 220,
      render: (_: unknown, record: DocGenAnchorCandidate) => (
        <Space size={4} wrap>
          <span style={{ fontWeight: 500 }}>{record.label}</span>
          {record.kind === 'table' && (
            <Tooltip title={`列定义来自表头：${(record.columns ?? []).join(' / ') || '（无表头文本）'}`}>
              <Tag color="orange">{(record.columns ?? []).length} 列</Tag>
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: '类型',
      key: 'kind',
      width: 80,
      render: (_: unknown, record: DocGenAnchorCandidate) => (
        <Tag color={KIND_META[record.kind].color}>{KIND_META[record.kind].label}</Tag>
      ),
    },
    {
      title: '上下文线索',
      key: 'context',
      render: (_: unknown, record: DocGenAnchorCandidate) =>
        record.context ? (
          <Tooltip title={record.context}>
            <span
              style={{
                color: '#666',
                fontSize: 12,
                display: 'inline-block',
                maxWidth: '100%',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {record.context}
            </span>
          </Tooltip>
        ) : (
          <span style={{ color: '#bbb' }}>—</span>
        ),
    },
  ]

  return (
    <Drawer
      title={`新增填写项：${templateName}`}
      open={open}
      onClose={handleClose}
      styles={{ wrapper: { width: 880 } }}
      destroyOnHidden
      footer={
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <Button onClick={handleClose}>关闭</Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            disabled={!selected}
            loading={submitting}
            onClick={() => void handleSubmit()}
          >
            新增填写项
          </Button>
        </div>
      }
    >
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 12 }}
        title="从母本中点选位置，人工新增填写项"
        description="候选位置由规则扫描器产出（锚点保证渲染期可解析），已被现有填写项占用的位置不会列出。自动识别漏掉的表格与「/」「—」占位单元格也会补扫进候选：整表候选自带列定义，单元格候选自带防错位校验，点选即可补录。只需补「叫什么、要什么值」，新增后该模板以后每次 AI 生成都会包含这个填写项。"
      />

      <div style={{ fontWeight: 600, marginBottom: 8 }}>
        候选位置
        <span style={{ color: '#999', fontWeight: 400, fontSize: 12, marginLeft: 8 }}>
          共 {candidates.length} 个，点击行选择
        </span>
      </div>
      <Table
        rowKey={(record) => anchorKey(record)}
        dataSource={candidates}
        columns={columns}
        loading={isLoading}
        size="small"
        pagination={candidates.length > 10 ? { pageSize: 10, size: 'small' } : false}
        scroll={{ y: 320 }}
        rowSelection={{
          type: 'radio',
          selectedRowKeys: selectedKey ? [selectedKey] : [],
          onChange: (keys) => {
            const candidate = candidates.find((c) => anchorKey(c) === String(keys[0] ?? ''))
            if (candidate) selectCandidate(candidate)
          },
        }}
        onRow={(record) => ({
          onClick: () => selectCandidate(record),
          style: { cursor: 'pointer' },
        })}
        locale={{ emptyText: '母本中没有可新增的位置：所有可锚定点都已被现有填写项占用' }}
      />

      <div style={{ fontWeight: 600, margin: '16px 0 8px' }}>填写项信息</div>
      {selected && (
        <div
          style={{
            marginBottom: 12,
            padding: '8px 12px',
            background: '#f6ffed',
            border: '1px solid #b7eb8f',
            borderRadius: 6,
          }}
        >
          <Space size={4} wrap>
            <span>已选位置：</span>
            <span style={{ fontWeight: 600 }}>{selected.label}</span>
            <Tag color={KIND_META[selected.kind].color}>{KIND_META[selected.kind].label}</Tag>
          </Space>
          {selected.kind === 'table' && (selected.columns?.length ?? 0) > 0 && (
            <div style={{ color: '#666', fontSize: 12, marginTop: 4 }}>
              表格列（来自表头，共 {selected.columns?.length ?? 0} 列
              {selected.header_rows > 1 ? '，双行表头' : ''}）：{selected.columns?.join(' / ')}
            </div>
          )}
          {selected.context && <div style={{ color: '#666', fontSize: 12, marginTop: 4 }}>{selected.context}</div>}
        </div>
      )}
      <Form form={form} layout="vertical" disabled={!selected} initialValues={{ expects: 'text', required: false }}>
        <Form.Item
          name="label"
          label="填写项名称"
          rules={[{ required: true, whitespace: true, message: '请输入填写项名称' }]}
        >
          <Input placeholder="如：验证结论" maxLength={100} showCount />
        </Form.Item>
        <Space size={16} style={{ display: 'flex' }} align="start">
          <Form.Item name="expects" label="值类型" style={{ width: 200 }}>
            <Select options={EXPECTS_OPTIONS} />
          </Form.Item>
          <Form.Item name="required" label="是否必填" valuePropName="checked" tooltip="必填项缺值时，生成任务会提示补齐">
            <Switch />
          </Form.Item>
        </Space>
        <Form.Item name="query_hint" label="检索提示" extra="告诉 AI 到项目知识库的什么位置找这个值（可选）">
          <Input placeholder="如：验证报告的结论段" maxLength={200} />
        </Form.Item>
        <Form.Item name="search_terms" label="检索词" extra="用于知识库检索的同义词，输入后按回车添加（可选）">
          <Select mode="tags" placeholder="如：验证结论、结论摘要" tokenSeparators={[',', '，']} notFoundContent={null} />
        </Form.Item>
      </Form>
    </Drawer>
  )
}
