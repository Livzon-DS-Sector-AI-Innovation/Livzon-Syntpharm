'use client'

import { useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Alert,
  App,
  AutoComplete,
  Button,
  Card,
  Empty,
  Form,
  Grid,
  Modal,
  Space,
  Switch,
  Table,
  Tag,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons'
import {
  createDepartmentContact,
  deleteDepartmentContact,
  updateDepartmentContact,
} from '@/actions/quality'
import { RemoteUserSelect, type RemoteUserSelectOption } from '@/components/common/RemoteUserSelect'
import { PeopleNamesInline, PersonInline } from './deviation/PersonInline'
import { NotifySettingsCard } from '@/components/quality/deviation'
import type {
  DepartmentContact,
  DepartmentMemberOption,
  DeviationNotifySettings,
} from '@/types/quality'

interface DepartmentContactPageProps {
  contacts: DepartmentContact[]
  memberOptions: DepartmentMemberOption[]
  notifySettings: DeviationNotifySettings | null
  loadError?: string | null
  /** 部门名称建议值（组织部门，与台账部门名同源） */
  departmentSuggestions?: string[]
  /** 台账里已有、但尚无联系人配置的部门（这些单子节点负责人无法自动指派） */
  unconfiguredDepartments?: string[]
}

/** 质量保证部：质量负责人 / QA 负责人 两个节点的缺省配置来源 */
const QA_DEPARTMENT = '质量保证部'

/** 列宽单一来源：scroll.x 由列宽求和派生，避免表格与列宽再次漂移 */
const COLUMN_WIDTHS = {
  department: 170,
  person: 148,
  qa: 136,
  people: 160,
  action: 160,
} as const

const SCROLL_X = Object.values(COLUMN_WIDTHS).reduce((sum, width) => sum + width, 0)

interface ContactFormValues {
  department: string
  dept_head_id?: string
  production_head_id?: string
  quality_head_id?: string
  qa_reviewer_id?: string
  qa_head_id?: string
  gmp_staff_ids?: string[]
  additional_contacts?: string[]
  is_production_workshop?: boolean
}



/** 部门联系人配置：调查/审核环节的处理人来源，配错会直接影响流转指派 */
export function DepartmentContactPage({
  contacts,
  memberOptions,
  notifySettings,
  loadError = null,
  departmentSuggestions = [],
  unconfiguredDepartments = [],
}: DepartmentContactPageProps) {
  const router = useRouter()
  const { message, modal } = App.useApp()
  /** 窄屏收起次要列，避免固定操作列把可视区挤到只剩两列 */
  const screens = Grid.useBreakpoint()
  const [form] = Form.useForm<ContactFormValues>()
  const [editing, setEditing] = useState<DepartmentContact | null>(null)
  const [open, setOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  // 质量保证部是「质量负责人 / QA 负责人」的缺省来源：新增部门时默认带出，避免用户不知道要填谁
  const qaDepartment = useMemo(
    () => contacts.find((item) => item.department === QA_DEPARTMENT) ?? null,
    [contacts],
  )

  // 编辑回显：人员下拉展开时才远端取人，已保存（或默认带出）的值靠这些快照显示姓名/头像
  const editingFallback = useMemo<RemoteUserSelectOption[]>(() => {
    const rows: RemoteUserSelectOption[] = []
    const pushPerson = (id: string | null | undefined, name: string | null | undefined, avatar?: string | null) => {
      if (id && name) rows.push({ value: id, label: name, avatar })
    }
    if (!editing) {
      pushPerson(qaDepartment?.quality_head_id, qaDepartment?.quality_head_name, qaDepartment?.quality_head_avatar)
      pushPerson(qaDepartment?.qa_head_id, qaDepartment?.qa_head_name, qaDepartment?.qa_head_avatar)
      return rows
    }
    pushPerson(editing.dept_head_id, editing.dept_head_name, editing.dept_head_avatar)
    pushPerson(editing.production_head_id, editing.production_head_name, editing.production_head_avatar)
    pushPerson(editing.quality_head_id, editing.quality_head_name, editing.quality_head_avatar)
    pushPerson(editing.qa_reviewer_id, editing.qa_reviewer_name, editing.qa_reviewer_avatar)
    pushPerson(editing.qa_head_id, editing.qa_head_name, editing.qa_head_avatar)
    const pushList = (ids: string[] | undefined, names: string[] | undefined, avatars: (string | null)[] | undefined) => {
      ;(ids ?? []).forEach((id, index) => pushPerson(id, names?.[index], avatars?.[index]))
    }
    pushList(editing.gmp_staff_ids, editing.gmp_staff_names, editing.gmp_staff_avatars)
    pushList(editing.additional_contacts, editing.additional_contact_names, editing.additional_contact_avatars)
    return rows
  }, [editing, qaDepartment])

  // 部门名是关联键：优先从组织部门里选，避免手输出偏差导致节点负责人解析不到
  const departmentNameCandidates =
    departmentSuggestions.length > 0
      ? departmentSuggestions
      : memberOptions
          .map((item) => item.description?.trim())
          .filter((name): name is string => Boolean(name))
  const departmentOptions = [...new Set(departmentNameCandidates)]
    .sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'))
    .map((name) => ({ value: name }))

  const openModal = (contact?: DepartmentContact) => {
    if (contact) {
      setEditing(contact)
      form.setFieldsValue({
        department: contact.department,
        dept_head_id: contact.dept_head_id ?? undefined,
        production_head_id: contact.production_head_id ?? undefined,
        quality_head_id: contact.quality_head_id ?? undefined,
        qa_reviewer_id: contact.qa_reviewer_id ?? undefined,
        qa_head_id: contact.qa_head_id ?? undefined,
        gmp_staff_ids: contact.gmp_staff_ids ?? [],
        additional_contacts: contact.additional_contacts ?? [],
        is_production_workshop: contact.is_production_workshop,
      })
    } else {
      setEditing(null)
      form.resetFields()
      // 新增部门默认带出质量保证部现行的负责人（流程解析的缺省来源），用户可再改
      form.setFieldsValue({
        quality_head_id: qaDepartment?.quality_head_id ?? undefined,
        qa_head_id: qaDepartment?.qa_head_id ?? undefined,
      })
    }
    setOpen(true)
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    setSubmitting(true)
    try {
      if (editing) {
        await updateDepartmentContact(editing.id, {
          dept_head_id: values.dept_head_id ?? null,
          production_head_id: values.production_head_id ?? null,
          quality_head_id: values.quality_head_id ?? null,
          qa_reviewer_id: values.qa_reviewer_id ?? null,
          qa_head_id: values.qa_head_id ?? null,
          gmp_staff_ids: values.gmp_staff_ids ?? [],
          additional_contacts: values.additional_contacts ?? [],
          is_production_workshop: values.is_production_workshop ?? false,
        })
        message.success('部门联系人已更新')
      } else {
        await createDepartmentContact({
          department: values.department.trim(),
          dept_head_id: values.dept_head_id ?? null,
          production_head_id: values.production_head_id ?? null,
          quality_head_id: values.quality_head_id ?? null,
          qa_reviewer_id: values.qa_reviewer_id ?? null,
          qa_head_id: values.qa_head_id ?? null,
          gmp_staff_ids: values.gmp_staff_ids ?? [],
          additional_contacts: values.additional_contacts ?? [],
          is_production_workshop: values.is_production_workshop ?? false,
        })
        message.success('部门联系人已创建')
      }
      setOpen(false)
      router.refresh()
    } catch (error) {
      console.error('部门联系人保存失败', error)
      message.error(error instanceof Error ? error.message : '保存失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = (record: DepartmentContact) => {
    modal.confirm({
      title: '删除部门联系人',
      content: `确定删除「${record.department}」的联系人配置？删除后该部门偏差将无法自动指派处理人。`,
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteDepartmentContact(record.id)
          message.success('已删除')
          router.refresh()
        } catch (error) {
          console.error('部门联系人删除失败', error)
          message.error(error instanceof Error ? error.message : '删除失败')
        }
      },
    })
  }

  const columns: ColumnsType<DepartmentContact> = [
    {
      title: '部门',
      dataIndex: 'department',
      key: 'department',
      width: COLUMN_WIDTHS.department,
      ellipsis: { showTitle: true },
      render: (value: string, row) => (
        <span className="flex min-w-0 items-center gap-1">
          <span className="truncate text-[13px] text-[var(--color-ink)]" title={value}>
            {value}
          </span>
          {row.is_production_workshop && <Tag color="blue" className="shrink-0">生产车间</Tag>}
        </span>
      ),
    },
    {
      title: '部门负责人',
      dataIndex: 'dept_head_name',
      key: 'dept_head_name',
      width: COLUMN_WIDTHS.person,
      ellipsis: { showTitle: true },
      render: (value: string | null, row) => (
        <PersonInline person={{ name: value, avatar_url: row.dept_head_avatar }} avatarSize={22} />
      ),
    },
    {
      title: '生产负责人',
      dataIndex: 'production_head_name',
      key: 'production_head_name',
      width: COLUMN_WIDTHS.person,
      responsive: ['sm'],
      ellipsis: { showTitle: true },
      render: (value: string | null, row) => (
        <PersonInline person={{ name: value, avatar_url: row.production_head_avatar }} avatarSize={22} />
      ),
    },
    {
      title: '质量负责人',
      dataIndex: 'quality_head_name',
      key: 'quality_head_name',
      width: COLUMN_WIDTHS.person,
      responsive: ['sm'],
      ellipsis: { showTitle: true },
      render: (value: string | null, row) => (
        <PersonInline person={{ name: value, avatar_url: row.quality_head_avatar }} avatarSize={22} />
      ),
    },
    {
      title: '所属 QA',
      dataIndex: 'qa_reviewer_name',
      key: 'qa_reviewer_name',
      width: COLUMN_WIDTHS.qa,
      responsive: ['md'],
      ellipsis: { showTitle: true },
      render: (value: string | null, row) => (
        <PersonInline person={{ name: value, avatar_url: row.qa_reviewer_avatar }} avatarSize={22} />
      ),
    },
    {
      title: 'QA 负责人',
      dataIndex: 'qa_head_name',
      key: 'qa_head_name',
      width: COLUMN_WIDTHS.qa,
      responsive: ['md'],
      ellipsis: { showTitle: true },
      render: (value: string | null, row) => (
        <PersonInline person={{ name: value, avatar_url: row.qa_head_avatar }} avatarSize={22} />
      ),
    },
    {
      title: 'GMP 人员',
      dataIndex: 'gmp_staff_names',
      key: 'gmp_staff_names',
      width: COLUMN_WIDTHS.people,
      responsive: ['lg'],
      ellipsis: { showTitle: true },
      render: (value: string[] | undefined, row) => (
        <PeopleNamesInline names={value} avatars={row.gmp_staff_avatars} avatarSize={22} />
      ),
    },
    {
      title: '其他联系人',
      dataIndex: 'additional_contact_names',
      key: 'additional_contact_names',
      width: COLUMN_WIDTHS.people,
      responsive: ['lg'],
      ellipsis: { showTitle: true },
      render: (value: string[] | undefined, row) => (
        <PeopleNamesInline names={value} avatars={row.additional_contact_avatars} avatarSize={22} />
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: COLUMN_WIDTHS.action,
      /* 窄屏不固定操作列：固定列会盖住仅剩的内容列，改为随表格横向滚动 */
      fixed: screens.lg ? 'right' : undefined,
      render: (_: unknown, record) => (
        <Space size={4}>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openModal(record)}>
            编辑
          </Button>
          <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record)}>
            删除
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-[22px] font-semibold text-[var(--color-ink)]">部门联系人配置</h1>
          <p className="mt-1 text-[13px] text-[var(--color-slate)]">
            偏差流转按部门取处理人：部门负责人、生产负责人、质量负责人（本部门优先、缺省回退质量保证部），以及所属 QA、QA 负责人
          </p>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => openModal()} className="shrink-0 self-start sm:self-auto">
          添加部门
        </Button>
      </header>

      {loadError && <Alert type="warning" showIcon title="联系人数据加载失败" description={loadError} />}

      {unconfiguredDepartments.length > 0 && (
        <Alert
          type="warning"
          showIcon
          title="以下部门已有偏差，但尚未配置联系人"
          description={
            <span className="break-words">
              {unconfiguredDepartments.join('、')}
              （这些偏差的节点负责人无法自动指派，请按台账里的部门名新增联系人配置）
            </span>
          }
        />
      )}

      <Card size="small" className="shadow-sm" styles={{ body: { padding: 0 } }}>
        <Table<DepartmentContact>
          rowKey="id"
          size="middle"
          columns={columns}
          dataSource={contacts}
          scroll={{ x: SCROLL_X }}
          locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无部门联系人配置" /> }}
          pagination={false}
        />
      </Card>

      <NotifySettingsCard initialSettings={notifySettings} />

      <Modal
        title={editing ? `编辑：${editing.department}` : '添加部门联系人'}
        open={open}
        width={680}
        style={{ maxWidth: 'calc(100vw - 24px)' }}
        confirmLoading={submitting}
        okText="保存"
        cancelText="取消"
        onOk={handleSubmit}
        onCancel={() => setOpen(false)}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" initialValues={{ is_production_workshop: false }}>
          <Form.Item
            name="department"
            label="部门名称"
            rules={[{ required: true, message: '请输入部门名称' }]}
            extra="部门名称是唯一键，创建后不可修改；必须与偏差台账里的部门名完全一致，否则节点负责人无法自动指派"
          >
            <AutoComplete
              placeholder="如 101车间"
              disabled={Boolean(editing)}
              maxLength={255}
              options={departmentOptions}
              filterOption={(inputValue, option) =>
                (option?.value ?? '').toLowerCase().includes(inputValue.toLowerCase())
              }
            />
          </Form.Item>
          <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-3">
            <Form.Item
              name="dept_head_id"
              label="部门负责人"
              tooltip="本部门任何偏差都会指派给他审核"
            >
              <RemoteUserSelect placeholder="搜索姓名选择人员" fallbackOptions={editingFallback} />
            </Form.Item>
            <Form.Item
              name="production_head_id"
              label="生产负责人"
              tooltip="生产车间偏差提级审核时使用"
            >
              <RemoteUserSelect placeholder="搜索姓名选择人员" fallbackOptions={editingFallback} />
            </Form.Item>
            <Form.Item
              name="quality_head_id"
              label="质量负责人"
              tooltip="本部门已配置则优先，未配置回退质量保证部"
            >
              <RemoteUserSelect placeholder="搜索姓名选择人员" fallbackOptions={editingFallback} />
            </Form.Item>
          </div>
          <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
            <Form.Item
              name="qa_reviewer_id"
              label="所属 QA"
              tooltip="「所属QA审核」节点处理人，也是最终编号环节处理人"
            >
              <RemoteUserSelect placeholder="搜索姓名选择人员" fallbackOptions={editingFallback} />
            </Form.Item>
            <Form.Item
              name="qa_head_id"
              label="QA 负责人"
              tooltip="「QA负责人审核」节点处理人：本部门已配置则优先，未配置回退质量保证部"
            >
              <RemoteUserSelect placeholder="搜索姓名选择人员" fallbackOptions={editingFallback} />
            </Form.Item>
          </div>
          <Form.Item name="gmp_staff_ids" label="GMP 人员">
            <RemoteUserSelect mode="multiple" placeholder="搜索姓名选择人员，可多选" fallbackOptions={editingFallback} />
          </Form.Item>
          <Form.Item name="additional_contacts" label="其他联系人">
            <RemoteUserSelect mode="multiple" placeholder="搜索姓名选择人员，可多选" fallbackOptions={editingFallback} />
          </Form.Item>
          <Form.Item name="is_production_workshop" label="是否生产车间" valuePropName="checked">
            <Switch aria-label="是否生产车间" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}