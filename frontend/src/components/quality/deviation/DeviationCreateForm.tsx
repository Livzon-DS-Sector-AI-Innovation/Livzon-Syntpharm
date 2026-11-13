'use client'

import { useState, useTransition } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  Breadcrumb,
  Button,
  Col,
  DatePicker,
  Form,
  Input,
  Row,
  Select,
  Switch,
  TimePicker,
  message,
} from 'antd'
import type { Dayjs } from 'dayjs'
import { createDeviationLedger } from '@/actions/quality'
import type {
  DeviationLedgerCreateInput,
  DeviationLedgerOption,
} from '@/types/quality'
import { RemoteUserMultiSelect, RemoteUserSelect } from '@/components/common/RemoteUserSelect'
import { toPersonId, toPersonIds } from '@/lib/utils/form-person'
import {
  CrossDeptReviewerFields,
  toCrossDeptRowsPayload,
  type CrossDeptReviewerRowValue,
} from './CrossDeptReviewerFields'
import { DEVIATION_LEDGER_PATH } from './constants'

interface DeviationCreateFormProps {
  departmentOptions: DeviationLedgerOption[]
  /** 发现人默认为当前登录人，可改选实际发现人 */
  currentUserId: string
  currentUserName: string
}

interface FormValues {
  title: string
  department: string
  discovery_date: Dayjs
  discovery_time: Dayjs
  discovery_location: string
  discoverer_id?: string
  affected_items: string
  batch_number: string
  handler_ids: string[]
  needs_cross_dept_review?: boolean
  cross_dept_reviewers?: CrossDeptReviewerRowValue[]
  description: string
}

export function DeviationCreateForm({
  departmentOptions,
  currentUserId,
  currentUserName,
}: DeviationCreateFormProps) {
  const router = useRouter()
  const [form] = Form.useForm<FormValues>()
  const [submitting, setSubmitting] = useState(false)
  const [, startTransition] = useTransition()
  const crossReview = Form.useWatch('needs_cross_dept_review', form)
  const discovererId = Form.useWatch('discoverer_id', form)
  // 发现人默认是当前登录人：仅在选中人仍是登录人时传姓名快照，改选他人后交给下拉自身快照回显，避免姓名错位
  const discovererLabel = discovererId && discovererId === currentUserId ? currentUserName : undefined

  const handleFinish = async (values: FormValues) => {
    const crossDeptRows = values.needs_cross_dept_review
      ? toCrossDeptRowsPayload(values.cross_dept_reviewers ?? [])
      : []
    if (values.needs_cross_dept_review && crossDeptRows.length === 0) {
      message.warning('开启跨部门审核后至少需要一行跨部门（部门与部门负责人必选）')
      return
    }
    setSubmitting(true)
    const payload: DeviationLedgerCreateInput = {
      title: values.title.trim(),
      department: values.department,
      discovery_date: values.discovery_date.format('YYYY-MM-DD'),
      discovery_time: values.discovery_time.format('HH:mm'),
      discovery_location: values.discovery_location.trim(),
      discoverer_id: values.discoverer_id || currentUserId || undefined,
      affected_items: values.affected_items.trim(),
      batch_number: values.batch_number.trim(),
      handler_ids: values.handler_ids,
      needs_cross_dept_review: Boolean(values.needs_cross_dept_review),
      cross_dept_reviewers: crossDeptRows,
      description: values.description.trim(),
    }

    const result = await createDeviationLedger(payload)
    if (result.code >= 200 && result.code < 300) {
      message.success(`偏差已创建：${result.data?.display_code ?? ''}`)
      startTransition(() => {
        router.push(DEVIATION_LEDGER_PATH)
      })
      return
    }

    message.error(result.message || '偏差创建失败，请稍后重试')
    setSubmitting(false)
  }

  const handleCancel = () => {
    router.push(DEVIATION_LEDGER_PATH)
  }

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <Breadcrumb
            className="mb-1"
            items={[
              { title: <Link href="/quality">质量管理</Link> },
              { title: <Link href="/quality/deviation">偏差管理</Link> },
              { title: <Link href={DEVIATION_LEDGER_PATH}>偏差台账</Link> },
              { title: '新建偏差' },
            ]}
          />
          <h1 className="text-[22px] font-semibold text-[var(--color-ink)]">新建偏差</h1>
          <p className="mt-1 text-[13px] text-[var(--color-slate)]">
            提交后偏差自动进入 AI 分析环节，编号按「PC+日期+序号」自动生成
          </p>
        </div>
        <Button className="self-start sm:self-auto" onClick={handleCancel}>
          返回台账
        </Button>
      </header>

      <section className="rounded-xl border border-[var(--color-hairline)] bg-[var(--color-canvas)] p-4 shadow-sm sm:p-6">
        <Form<FormValues>
          form={form}
          layout="vertical"
          requiredMark
          initialValues={{
            needs_cross_dept_review: false,
            discoverer_id: currentUserId || undefined,
          }}
          onFinish={handleFinish}
          scrollToFirstError
        >
          <Row gutter={20}>
            <Col xs={24} md={12}>
              <Form.Item
                name="title"
                label="偏差标题"
                rules={[{ required: true, whitespace: true, message: '请填写偏差标题' }]}
              >
                <Input placeholder="用一句话描述偏差，例如：包装间温湿度超出规定范围" maxLength={255} />
              </Form.Item>
            </Col>

            <Col xs={24} md={12}>
              <Form.Item
                name="department"
                label="所属部门"
                rules={[{ required: true, message: '请选择所属部门' }]}
                tooltip="候选来自部门联系人配置，未配置联系人的部门不可选（避免节点负责人无法指派）"
              >
                <Select
                  showSearch
                  optionFilterProp="label"
                  placeholder="请选择所属部门"
                  notFoundContent="暂无已配置联系人的部门，请先到「部门联系人配置」补充"
                  options={departmentOptions.map((item) => ({ value: item.value, label: item.label }))}
                />
              </Form.Item>
            </Col>

            <Col xs={24} md={12}>
              <Form.Item name="discovery_date" label="发现日期" rules={[{ required: true, message: '请选择发现日期' }]}>
                <DatePicker style={{ width: '100%' }} placeholder="请选择发现日期" />
              </Form.Item>
            </Col>

            <Col xs={24} md={12}>
              <Form.Item name="discovery_time" label="发现时间" rules={[{ required: true, message: '请选择发现时间' }]}>
                {/* needConfirm=false：时、分选完即生效，不再弹出「确定」按钮 */}
                <TimePicker
                  style={{ width: '100%' }}
                  format="HH:mm"
                  minuteStep={1}
                  needConfirm={false}
                  placeholder="请选择发现时间"
                />
              </Form.Item>
            </Col>

            <Col xs={24} md={12}>
              <Form.Item
                name="discovery_location"
                label="发现地点"
                rules={[{ required: true, whitespace: true, message: '请填写发现地点' }]}
              >
                <Input placeholder="例如：固体制剂车间包装间" maxLength={255} />
              </Form.Item>
            </Col>

            <Col xs={24} md={12}>
              <Form.Item
                name="discoverer_id"
                label="发现人"
                tooltip="默认填当前登录人，可改选实际发现人"
                rules={[{ required: true, message: '请选择发现人' }]}
                normalize={toPersonId}
              >
                <RemoteUserSelect
                  placeholder={currentUserName || '搜索姓名选择发现人'}
                  label={discovererLabel}
                  feishuBoundOnly={false}
                />
              </Form.Item>
            </Col>

            <Col xs={24} md={12}>
              <Form.Item
                name="affected_items"
                label="受影响的产品 / 物料 / 设备 / 仪器"
                rules={[{ required: true, whitespace: true, message: '请填写受影响的对象' }]}
              >
                <Input placeholder="例如：阿莫西林胶囊 0.25g、沸腾干燥机" />
              </Form.Item>
            </Col>

            <Col xs={24} md={12}>
              <Form.Item
                name="batch_number"
                label="批号 / 位号 / 编号"
                rules={[{ required: true, whitespace: true, message: '请填写批号 / 位号 / 编号' }]}
              >
                <Input placeholder="例如：20260901 / BX-03 / EQ-0125" maxLength={255} />
              </Form.Item>
            </Col>

            <Col xs={24} md={12}>
              <Form.Item
                name="handler_ids"
                label="调查人"
                tooltip="可多选，提交后由所选调查人负责后续调查"
                rules={[{ required: true, message: '请至少选择一名调查人' }]}
                normalize={toPersonIds}
              >
                <RemoteUserMultiSelect placeholder="搜索姓名选择调查人，可多选" feishuBoundOnly={false} />
              </Form.Item>
            </Col>

            <Col xs={24} md={12}>
              <Form.Item
                name="needs_cross_dept_review"
                label="是否需要跨部门审核"
                valuePropName="checked"
                tooltip="开启后偏差会流转至跨部门负责人审核环节；仅影响本部门之外责任的偏差才需要开启"
              >
                {/* 只留滑块：文字会撑高行并用颜色暗示状态，与「已开启/未开启」重复 */}
                <Switch aria-label="是否需要跨部门审核" />
              </Form.Item>
            </Col>

            {crossReview && (
              <Col span={24}>
                <div className="-mt-2 rounded-lg border border-[var(--color-hairline)] bg-[var(--color-surface-soft)] p-3">
                  <p className="mb-2 text-xs text-[var(--color-slate)]">
                    每个跨部门 = 一行两节点：该部门调查人提交调查记录 → 该部门负责人审核。调查人可留空（由负责人直接审核）；
                    全部行通过后才会进入所属QA审核。
                  </p>
                  <CrossDeptReviewerFields form={form} departmentOptions={departmentOptions} />
                </div>
              </Col>
            )}

            <Col span={24}>
              <Form.Item
                name="description"
                label="偏差描述"
                rules={[{ required: true, whitespace: true, message: '请填写偏差描述' }]}
              >
                <Input.TextArea
                  rows={5}
                  placeholder="说明偏差发生的经过、当时的参数或现象、已采取的临时措施等"
                  maxLength={2000}
                  showCount
                />
              </Form.Item>
            </Col>
          </Row>

          <div className="mt-2 flex justify-end gap-2 border-t border-[var(--color-hairline-soft)] pt-4">
            <Button onClick={handleCancel} disabled={submitting}>
              取消
            </Button>
            <Button type="primary" htmlType="submit" loading={submitting}>
              提交
            </Button>
          </div>
        </Form>
      </section>
    </div>
  )
}