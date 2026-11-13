'use client'

import { useEffect } from 'react'
import { App, Form, Input, Modal, Select } from 'antd'
import { updateHazard } from '@/actions/safety'
import type { HazardReport } from '@/types/safety'

const { TextArea } = Input

/**
 * 整改进度可人工维护的两态：
 * 「待复核 / 已驳回 / 已关闭」由整改回复与复核流程驱动，这里不放开，避免绕过状态机。
 */
const PROGRESS_EDITABLE_OPTIONS = [
  { value: 'pending', label: '待整改' },
  { value: 'in_progress', label: '整改中' },
]

interface Props {
  open: boolean
  hazard: HazardReport | null
  onClose: () => void
  onSaved: () => void
}

interface FormValues {
  rectification_status: string
  rectification_progress_note?: string
}

/** 整改进度编辑弹框：状态单选 + 自定义进度说明 */
export default function HazardProgressEditModal({ open, hazard, onClose, onSaved }: Props) {
  const [form] = Form.useForm<FormValues>()
  const { message } = App.useApp()

  useEffect(() => {
    if (!open || !hazard) return
    form.setFieldsValue({
      rectification_status: PROGRESS_EDITABLE_OPTIONS.some((o) => o.value === hazard.rectification_status)
        ? hazard.rectification_status
        : 'pending',
      rectification_progress_note: hazard.rectification_progress_note ?? undefined,
    })
  }, [open, hazard, form])

  const handleOk = async () => {
    if (!hazard) return
    try {
      const values = await form.validateFields()
      const response = await updateHazard(hazard.id, {
        rectification_status: values.rectification_status,
        // 传空串而非 null：后端 update 会过滤 None，空串才能清空说明
        rectification_progress_note: values.rectification_progress_note?.trim() || '',
      })
      if (response.code !== 200) {
        message.error(response.message || '保存失败')
        return
      }
      message.success('整改进度已更新')
      onSaved()
      onClose()
    } catch {
      // 校验失败由 Form 高亮提示
    }
  }

  return (
    <Modal
      open={open}
      title="编辑整改进度"
      okText="保存"
      cancelText="取消"
      onOk={handleOk}
      onCancel={onClose}
      destroyOnHidden
      width={520}
    >
      <Form form={form} layout="vertical" style={{ marginTop: 12 }}>
        <Form.Item name="rectification_status" label="整改进度" rules={[{ required: true, message: '请选择整改进度' }]}>
          <Select options={PROGRESS_EDITABLE_OPTIONS} />
        </Form.Item>
        <Form.Item
          name="rectification_progress_note"
          label="进度说明"
          extra="台账「整改进度」列会在状态标签下展示这段说明"
        >
          <TextArea rows={3} maxLength={500} showCount placeholder="如：已完成 3 台设备更换，剩余 1 台待配件到货" />
        </Form.Item>
      </Form>
    </Modal>
  )
}