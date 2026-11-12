'use client'

import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { App, Form, Input, DatePicker, Select, Button, Space, Card, Typography, Row, Col, Divider } from 'antd'
import { CheckOutlined, SaveOutlined, SearchOutlined, PlusOutlined, SettingOutlined } from '@ant-design/icons'
import {
  HAZARD_CATEGORY_OPTIONS,
  HAZARD_LEVEL_FORM_OPTIONS,
  INSPECTION_CATEGORY_OPTIONS,
  INSPECTOR_DEPARTMENT_OPTIONS,
  DEPARTMENT_OPTIONS,
} from '@/types/safety'
import { getCurrentUser } from '@/actions/auth'
import { createHazardCategory } from '@/actions/safety'
import { fetchHazardCategories, invalidateHazardCategoryCache } from '@/lib/api/client/safety'
import { usePermission } from '@/hooks/usePermission'
import { PERM } from '@/lib/permissions/codes'
import HazardCategoryModal from '@/components/safety/HazardCategoryModal'
import PersonnelSelect, { PersonnelMultiSelect } from '@/components/safety/PersonnelSelect'
import dayjs, { type Dayjs } from 'dayjs'

const { TextArea } = Input
const { Text } = Typography

export interface InspectionFormValues {
  inspection_name?: string // 检查名称
  inspection_category?: string // 检查类别（单选：内部检查/政府检查）
  hazard_level?: string // 隐患等级（单选：一般隐患/重大隐患）
  hazard_category?: string // 隐患类别（字典表名称，可新增）
  discovered_by?: string // 审批人 user UUID
  discovered_by_name?: string // 审批人姓名快照
  inspector_department?: string | string[] // 审批人部门（不再展示，沿用登录人部门自动带入）
  department?: string // 责任部门
  discovered_at?: string | Dayjs // 检查日期
  deadline?: string | Dayjs // 目标完成日期
  description?: string // 缺陷项描述
  capa_measures?: string // 纠正预防措施
  rectification_responsible_person_ids?: string[] | string // 整改负责人 UUID 列表
  rectification_responsible_person_names?: string // 整改负责人姓名快照（逗号分隔）
}

interface Props {
  initialValues?: InspectionFormValues
  loading: boolean
  onSubmit: (values: Record<string, unknown>) => Promise<void>
  onSaveDraft: (values: Record<string, unknown>) => Promise<void>
}

/** 逗号/数组两种历史格式统一成数组（草稿回填兼容） */
function toArray(raw?: string[] | string | null): string[] {
  if (!raw) return []
  if (Array.isArray(raw)) return raw.filter(Boolean)
  return raw
    .split(/[,，]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

/** 审批人字段：把选择结果同时写 id 与姓名快照（台账列表直接读快照，避免再查用户表） */
function InspectorField({
  value,
  onChange,
}: {
  value?: string
  onChange?: (next?: string) => void
}) {
  const form = Form.useFormInstance()
  const name = Form.useWatch('discovered_by_name', form) as string | undefined
  return (
    <PersonnelSelect
      value={value}
      label={name}
      placeholder="搜索姓名/账号选择审批人"
      onChange={(person) => {
        onChange?.(person?.id)
        form.setFieldValue('discovered_by_name', person?.name)
      }}
    />
  )
}

/** 整改负责人多选字段：id 列表进表单，姓名快照写隐藏字段 */
function ResponsiblesField({
  value,
  onChange,
}: {
  value?: string[]
  onChange?: (next?: string[]) => void
}) {
  const form = Form.useFormInstance()
  const names = Form.useWatch('rectification_responsible_person_names', form) as string | undefined
  return (
    <PersonnelMultiSelect
      value={value ?? []}
      labels={toArray(names)}
      onChange={(persons) => {
        onChange?.(persons.map((person) => person.id))
        form.setFieldValue('rectification_responsible_person_names', persons.map((person) => person.name).join(','))
      }}
    />
  )
}

export default function HazardInspectionForm({ initialValues, loading, onSubmit, onSaveDraft }: Props) {
  const [form] = Form.useForm<InspectionFormValues>()
  const { message } = App.useApp()

  // 组件卸载标记：异步回填不再 setState
  const mountedRef = useRef(true)
  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  // ── 隐患类别字典（内置 7 项 + 用户新增）──
  const { data: categoryData, refetch: refetchCategories } = useQuery({
    queryKey: ['safety', 'hazard-categories'],
    queryFn: () => fetchHazardCategories(),
    staleTime: 5 * 60 * 1000,
  })
  const [addingCategory, setAddingCategory] = useState(false)
  const [newCategoryName, setNewCategoryName] = useState('')
  const [savingCategory, setSavingCategory] = useState(false)
  const [categoryModalOpen, setCategoryModalOpen] = useState(false)

  // 类别字典全公司共享：只有持有 safety:hazard-category:manage（模块管理员）才能新增/改名/删除，
  // 普通用户只能在既有选项里选。前端隐藏只是体验优化，后端接口同样校验。
  const { can, loading: permissionLoading } = usePermission()
  const canManageCategory = !permissionLoading && can(PERM.hazardCategoryManage)

  const handleCategoryChanged = useCallback(async () => {
    invalidateHazardCategoryCache()
    await refetchCategories()
  }, [refetchCategories])

  const categoryOptions = useMemo(() => {
    const seen = new Set<string>()
    const options: { value: string; label: string }[] = []
    for (const item of categoryData ?? []) {
      if (!item.name || seen.has(item.name)) continue
      seen.add(item.name)
      options.push({ value: item.name, label: item.name })
    }
    // 字典接口不可用或尚未返回时用内置 7 项兜底
    for (const item of HAZARD_CATEGORY_OPTIONS) {
      if (seen.has(item.value)) continue
      seen.add(item.value)
      options.push({ value: item.value, label: item.label })
    }
    return options
  }, [categoryData])

  const handleAddCategory = useCallback(async () => {
    const name = newCategoryName.trim()
    if (!name) return
    if (categoryOptions.some((option) => option.value === name)) {
      form.setFieldValue('hazard_category', name)
      setAddingCategory(false)
      setNewCategoryName('')
      return
    }
    setSavingCategory(true)
    try {
      const response = await createHazardCategory(name)
      if (response.code !== 200) {
        message.error(response.message || '新增类别失败')
        return
      }
      invalidateHazardCategoryCache()
      await refetchCategories()
      form.setFieldValue('hazard_category', name)
      setAddingCategory(false)
      setNewCategoryName('')
      message.success(`已新增隐患类别「${name}」`)
    } catch {
      message.error('新增类别失败，请稍后重试')
    } finally {
      if (mountedRef.current) setSavingCategory(false)
    }
  }, [categoryOptions, form, message, newCategoryName, refetchCategories])

  // 回填草稿数据
  useEffect(() => {
    if (!initialValues) return
    form.setFieldsValue({
      inspection_name: initialValues.inspection_name,
      inspection_category: initialValues.inspection_category,
      hazard_level: initialValues.hazard_level,
      hazard_category: initialValues.hazard_category,
      discovered_by: initialValues.discovered_by || undefined,
      discovered_by_name: initialValues.discovered_by_name,
      department: initialValues.department,
      description: initialValues.description,
      capa_measures: initialValues.capa_measures,
    } as Record<string, unknown>)
    form.setFieldsValue({
      rectification_responsible_person_ids: toArray(initialValues.rectification_responsible_person_ids),
      rectification_responsible_person_names: initialValues.rectification_responsible_person_names,
    } as Record<string, unknown>)
  }, [initialValues, form])

  // 当前用户走 React Query：同一会话内复用缓存，避免每次挂载都打一次 server action
  const { data: currentUser } = useQuery({
    queryKey: ['identity', 'me'],
    queryFn: () => getCurrentUser(),
    enabled: !initialValues, // 有草稿数据时不覆盖
    staleTime: 5 * 60 * 1000,
  })

  // 从飞书登录信息自动填充审批人与审批人部门（仅新建表单，草稿不覆盖）
  useEffect(() => {
    if (initialValues || !currentUser) return
    const user = currentUser
    const patch: Record<string, unknown> = {}
    if (user.name && user.id) {
      patch.discovered_by = user.id
      patch.discovered_by_name = user.name
    }
    if (user.department) {
      // 表单不再展示该字段，但仍自动带入，保持通知/复核的下游行为不变
      const isKnownDept = INSPECTOR_DEPARTMENT_OPTIONS.some((o) => o.value === user.department)
      if (isKnownDept) {
        patch.inspector_department = [user.department]
      }
    }
    if (Object.keys(patch).length > 0) form.setFieldsValue(patch)
  }, [currentUser, initialValues, form])

  // 规范化表单值：DatePicker → YYYY-MM-DD，多值字段 → 逗号分隔字符串
  const normalizeValues = (values: Record<string, unknown>): Record<string, unknown> => {
    const formatDate = (value: unknown): string | undefined => {
      if (!value) return undefined
      return dayjs.isDayjs(value)
        ? (value as Dayjs).format('YYYY-MM-DD')
        : dayjs(value as string).format('YYYY-MM-DD')
    }
    const ids = toArray(values.rectification_responsible_person_ids as string[] | string | undefined)
    const names = toArray(values.rectification_responsible_person_names as string | string[] | undefined)
    return {
      ...values,
      discovered_by_name: (values.discovered_by_name as string) || undefined,
      inspection_category: (values.inspection_category as string) || undefined,
      hazard_level: (values.hazard_level as string) || undefined,
      hazard_category: (values.hazard_category as string) || undefined,
      capa_measures: (values.capa_measures as string) || undefined,
      discovered_at: formatDate(values.discovered_at),
      deadline: formatDate(values.deadline),
      rectification_responsible_person_ids: ids.length > 0 ? ids : undefined,
      rectification_responsible_person_names: names.length > 0 ? names.join(',') : undefined,
      inspector_department: Array.isArray(values.inspector_department)
        ? values.inspector_department.join(',')
        : values.inspector_department,
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      await onSubmit(normalizeValues(values as Record<string, unknown>))
    } catch {
      message.warning('请完整填写全部必填项后再提交')
    }
  }

  const handleSaveDraft = async () => {
    try {
      const values = await form.validateFields()
      await onSaveDraft(normalizeValues(values as Record<string, unknown>))
    } catch {
      // 草稿允许不完整，直接取 form 当前值
      await onSaveDraft(normalizeValues(form.getFieldsValue() as Record<string, unknown>))
    }
  }

  const required = (text: string) => [{ required: true, message: text }]

  return (
    <Card
      style={{
        borderRadius: 12,
        border: '1px solid #e5e3df',
        borderLeft: '4px solid #5645d4',
      }}
      styles={{ body: { padding: '20px 24px' } }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          marginBottom: 24,
          paddingBottom: 16,
          borderBottom: '1px solid #ede9e4',
        }}
      >
        <SearchOutlined style={{ color: '#5645d4', fontSize: 18 }} />
        <div>
          <span style={{ fontSize: 15, fontWeight: 600, color: '#1a1a1a' }}>登记隐患信息</span>
          <Text type="secondary" style={{ display: 'block', fontSize: 13, color: '#5d5b54' }}>
            带 * 的项目为必填；可先保存草稿，填写完整后再正式登记
          </Text>
        </div>
      </div>

      <Form
        form={form}
        layout="vertical"
        initialValues={{
          discovered_at: initialValues?.discovered_at ? dayjs(initialValues.discovered_at) : dayjs(),
          deadline: initialValues?.deadline ? dayjs(initialValues.deadline) : undefined,
          inspection_category: initialValues?.inspection_category,
          hazard_level: initialValues?.hazard_level,
          hazard_category: initialValues?.hazard_category,
        }}
      >
        {/* ── 基本信息 ── */}
        <SectionTitle title="基本信息" />
        <Row gutter={16}>
          <Col span={24}>
            <Form.Item name="inspection_name" label="检查名称" rules={required('请填写检查名称')}>
              <Input placeholder="如「2026 年 11 月合成车间月度安全检查」" maxLength={255} />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col xs={24} md={12}>
            <Form.Item name="inspection_category" label="检查类别" rules={required('请选择检查类别')}>
              <Select placeholder="请选择检查类别" options={INSPECTION_CATEGORY_OPTIONS} />
            </Form.Item>
          </Col>
          <Col xs={24} md={12}>
            <Form.Item name="hazard_level" label="隐患等级" rules={required('请选择隐患等级')}>
              <Select placeholder="请选择隐患等级" options={HAZARD_LEVEL_FORM_OPTIONS} />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={24}>
            <Form.Item name="hazard_category" label="隐患类别" rules={required('请选择隐患类别')}>
              <Select
                showSearch
                placeholder="请选择隐患类别，可下拉底部新增"
                options={categoryOptions}
                filterOption={(input, option) => (option?.label as string)?.includes(input)}
                popupRender={(menu) => (
                  <>
                    {menu}
                    {canManageCategory && (
                      <>
                        <Divider style={{ margin: '6px 0' }} />
                        {addingCategory ? (
                          <div style={{ padding: '4px 8px' }}>
                            <Space.Compact style={{ width: '100%' }}>
                              <Input
                                autoFocus
                                size="small"
                                maxLength={64}
                                placeholder="输入新类别名称"
                                value={newCategoryName}
                                onChange={(event) => setNewCategoryName(event.target.value)}
                                onPressEnter={handleAddCategory}
                              />
                              <Button size="small" type="primary" loading={savingCategory} onClick={handleAddCategory}>
                                确定
                              </Button>
                              <Button
                                size="small"
                                onClick={() => {
                                  setAddingCategory(false)
                                  setNewCategoryName('')
                                }}
                              >
                                取消
                              </Button>
                            </Space.Compact>
                          </div>
                        ) : (
                          <Space style={{ padding: '0 8px', width: '100%', justifyContent: 'space-between' }}>
                            <Button
                              type="link"
                              size="small"
                              icon={<PlusOutlined />}
                              onClick={() => setAddingCategory(true)}
                            >
                              新增类别
                            </Button>
                            <Button
                              type="link"
                              size="small"
                              icon={<SettingOutlined />}
                              onClick={() => setCategoryModalOpen(true)}
                            >
                              管理类别
                            </Button>
                          </Space>
                        )}
                      </>
                    )}
                  </>
                )}
              />
            </Form.Item>
          </Col>
        </Row>

        {/* ── 隐患描述与措施 ── */}
        <SectionTitle title="隐患描述与措施" />
        <Form.Item name="description" label="缺陷项描述" rules={required('请填写缺陷项描述')}>
          <TextArea rows={3} placeholder="填写缺陷项的具体描述（位置、现象、可能后果）" maxLength={2000} showCount />
        </Form.Item>
        <Form.Item name="capa_measures" label="纠正预防措施" rules={required('请填写纠正预防措施')}>
          <TextArea rows={3} placeholder="填写纠正与预防措施" maxLength={2000} showCount />
        </Form.Item>

        {/* ── 责任与时间 ── */}
        <SectionTitle title="责任与时间" />
        <Row gutter={16}>
          <Col xs={24} md={12}>
            <Form.Item name="department" label="责任部门" rules={required('请选择责任部门')}>
              <Select
                showSearch
                placeholder="请选择责任部门"
                options={DEPARTMENT_OPTIONS}
                filterOption={(input, option) => (option?.label as string)?.includes(input)}
              />
            </Form.Item>
          </Col>
          <Col xs={24} md={12}>
            <Form.Item
              name="rectification_responsible_person_ids"
              label="整改负责人"
              rules={[{ required: true, message: '请搜索并选择整改负责人（可多选）' }]}
            >
              <ResponsiblesField />
            </Form.Item>
            {/* 隐藏字段：整改负责人姓名快照 */}
            <Form.Item name="rectification_responsible_person_names" hidden>
              <Input />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col xs={24} md={12}>
            <Form.Item name="discovered_by" label="审批人" rules={required('请搜索并选择审批人')}>
              <InspectorField />
            </Form.Item>
            {/* 隐藏字段：审批人姓名快照 */}
            <Form.Item name="discovered_by_name" hidden>
              <Input />
            </Form.Item>
          </Col>
          <Col xs={24} md={12}>
            <Form.Item name="discovered_at" label="检查日期" rules={required('请选择检查日期')}>
              <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col xs={24} md={12}>
            <Form.Item
              name="deadline"
              label="目标完成日期"
              rules={[
                { required: true, message: '请选择目标完成日期' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    const start = getFieldValue('discovered_at')
                    if (!value || !start || !dayjs(value).isBefore(dayjs(start), 'day')) return Promise.resolve()
                    return Promise.reject(new Error('目标完成日期不能早于检查日期'))
                  },
                }),
              ]}
            >
              <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
            </Form.Item>
          </Col>
        </Row>

        <Divider />

        <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
          <Button icon={<SaveOutlined />} onClick={handleSaveDraft} disabled={loading}>
            保存草稿
          </Button>
          <Button type="primary" size="large" icon={<CheckOutlined />} onClick={handleSubmit} loading={loading}>
            正式登记
          </Button>
        </Space>
      </Form>

      {canManageCategory && (
        <HazardCategoryModal
          open={categoryModalOpen}
          onClose={() => setCategoryModalOpen(false)}
          onChanged={handleCategoryChanged}
        />
      )}
    </Card>
  )
}

function SectionTitle({ title }: { title: string }) {
  return (
    <div style={{ margin: '4px 0 12px' }}>
      <Text strong style={{ fontSize: 13, color: '#5645d4' }}>
        {title}
      </Text>
    </div>
  )
}