'use client'

import { Button, Form, Select, Tag } from 'antd'
import type { FormInstance } from 'antd'
import { CheckCircleOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import { RemoteUserSelect, type RemoteUserSelectOption } from '@/components/common/RemoteUserSelect'
import type { DeviationCrossDeptReviewer, DeviationLedgerOption } from '@/types/quality'

/** 跨部门行值：详情页回显时携带后端行审核状态字段，创建场景仅有编辑字段 */
export interface CrossDeptReviewerRowValue {
  department?: string
  investigator_ids?: string[]
  review_state?: string
  approved_name?: string | null
  opinion?: string | null
}

/**
 * 表单行 → 提交用行结构。行审核状态字段由服务端按部门名单归并保留，
 * 提交时统一携带默认值即可（生成类型为必填，后端校验会忽略传入的状态）。
 */
export function toCrossDeptRowsPayload(rows: CrossDeptReviewerRowValue[]): DeviationCrossDeptReviewer[] {
  return rows.map((row) => ({
    department: row.department?.trim() ?? '',
    investigator_ids: row.investigator_ids ?? [],
    investigator_names: [],
    reviewer_names: [],
    review_state: 'pending',
    approved_by: null,
    approved_name: null,
    approved_at: null,
    opinion: null,
    can_approve: false,
  }))
}

interface CrossDeptReviewerFieldsProps {
  /** 宿主表单实例（宿主须在 <Form form={form}> 内使用本组件） */
  form: FormInstance
  departmentOptions: DeviationLedgerOption[]
  /** RemoteUserSelect 已选人员回显快照 */
  fallbackOptions?: RemoteUserSelectOption[]
  /** 宿主 Form 处于全局 disabled 时，显式放开本区控件（详情页 pending_investigation 局部解锁用） */
  unlock?: boolean
}

/**
 * 跨部门会签名单编辑器：每行 = 部门 + 调查人（可留空，回退部门负责人审核）。
 * 新建表单（DeviationCreateForm）与详情基础信息卡（BasicInfoCard）共用。
 * 详情回显时若行已通过，展示绿色「已通过」状态，提示重提不会丢状态。
 */
export function CrossDeptReviewerFields({
  form,
  departmentOptions,
  fallbackOptions = [],
  unlock = false,
}: CrossDeptReviewerFieldsProps) {
  const editableProps = unlock ? { disabled: false } : {}

  return (
    <Form.List name="cross_dept_reviewers">
      {(fields, { add, remove }) => (
        <div className="mb-4 flex flex-col gap-2">
          {fields.map((field) => {
            // 行审核状态为服务端只读回显（用户编辑不会触碰），List 每次变更都会重渲染，直接取值即可
            const row = (form.getFieldValue(['cross_dept_reviewers', field.name]) ?? undefined) as
              | CrossDeptReviewerRowValue
              | undefined
            return (
              <div key={field.key} className="flex w-full flex-col gap-2 sm:flex-row sm:items-start">
                <Form.Item
                  name={[field.name, 'department']}
                  rules={[{ required: true, message: '请选择跨部门' }]}
                  className="!mb-0 w-full sm:w-[200px]"
                >
                  <Select
                    showSearch
                    optionFilterProp="label"
                    placeholder="跨部门"
                    options={departmentOptions.map((item) => ({ value: item.value, label: item.label }))}
                    {...editableProps}
                  />
                </Form.Item>
                <Form.Item name={[field.name, 'investigator_ids']} className="!mb-0 min-w-0 flex-1">
                  <RemoteUserSelect
                    mode="multiple"
                    placeholder="该部门参与调查人（可留空，由部门负责人审核）"
                    fallbackOptions={fallbackOptions}
                    {...editableProps}
                  />
                </Form.Item>
                {row?.review_state === 'approved' && (
                  <Tag color="success" icon={<CheckCircleOutlined />} className="!mt-1 shrink-0">
                    已通过{row.approved_name ? ` · ${row.approved_name}` : ''}
                  </Tag>
                )}
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => remove(field.name)}
                  aria-label="删除跨部门"
                  className="self-end sm:self-auto"
                  {...editableProps}
                />
              </div>
            )
          })}
          <Button
            type="dashed"
            icon={<PlusOutlined />}
            onClick={() => add({ department: '', investigator_ids: [] })}
            {...editableProps}
          >
            增加跨部门
          </Button>
        </div>
      )}
    </Form.List>
  )
}
