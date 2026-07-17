'use client'

import { useEffect, useState } from 'react'
import {
  Table,
  Button,
  Space,
  Input,
  Select,
  Modal,
  Form,
  message,
  Tag,
  Card,
  Row,
  Col,
  DatePicker,
  Divider,
  Tooltip,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
  HistoryOutlined,
  CopyOutlined,
  SendOutlined,
  StopOutlined,
  DownloadOutlined,
} from '@ant-design/icons'
import { getStandards, createStandard, updateStandard, deleteStandard, submitStandardForApproval, copyStandard, obsoleteStandard } from '@/actions/quality'
import {
  InspectionStandard,
  InspectionStandardFormData,
  InspectionStandardItem,
  StandardStatus,
  MaterialCategory,
  Pharmacopeia,
  LimitType,
  ItemCategory,
} from '@/types/quality'
import {
  STANDARD_STATUS_OPTIONS,
  MATERIAL_CATEGORY_OPTIONS,
  PHARMACOPEIA_OPTIONS,
  LIMIT_TYPE_OPTIONS,
  ITEM_CATEGORY_OPTIONS,
} from '@/types/quality'

const getStatusColor = (status: StandardStatus) => {
  const option = STANDARD_STATUS_OPTIONS.find((o) => o.value === status)
  return option?.color || 'default'
}

const getStatusLabel = (status: StandardStatus) => {
  const option = STANDARD_STATUS_OPTIONS.find((o) => o.value === status)
  return option?.label || status
}

// 导出CSV函数
const exportStandardsToCsv = (standards: InspectionStandard[]) => {
  const headers = ['标准编号', '物料编码', '物料名称', '物料分类', '药典', '版本', '状态', '生效日期', '创建时间']
  const rows = standards.map(s => [
    s.standard_no,
    s.material_code,
    s.material_name || '',
    MATERIAL_CATEGORY_OPTIONS.find(o => o.value === s.material_category)?.label || s.material_category,
    PHARMACOPEIA_OPTIONS.find(o => o.value === s.pharmacopeia)?.label || s.pharmacopeia || '',
    s.version,
    getStatusLabel(s.status),
    s.effective_date ? new Date(s.effective_date).toLocaleDateString('zh-CN') : '',
    s.created_at ? new Date(s.created_at).toLocaleString('zh-CN') : '',
  ])

  const csvContent = [headers, ...rows]
    .map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    .join('\n')

  const BOM = '\uFEFF'
  const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `检验标准列表_${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(link.href)
}

export default function InspectionStandardsPage() {
  const [form] = Form.useForm()
  const [editForm] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingStandard, setEditingStandard] = useState<InspectionStandard | null>(null)
  const [detailModalVisible, setDetailModalVisible] = useState(false)
  const [viewingStandard, setViewingStandard] = useState<InspectionStandard | null>(null)
  const [copyModalVisible, setCopyModalVisible] = useState(false)
  const [obsoleteModalVisible, setObsoleteModalVisible] = useState(false)
  const [obsoleteReason, setObsoleteReason] = useState('')
  const [exportLoading, setExportLoading] = useState(false)
  const [newVersion, setNewVersion] = useState('')

  // 筛选条件
  const [searchMaterialName, setSearchMaterialName] = useState('')
  const [materialCategoryFilter, setMaterialCategoryFilter] = useState<MaterialCategory | undefined>()
  const [pharmacopeiaFilter, setPharmacopeiaFilter] = useState<Pharmacopeia | undefined>()
  const [statusFilter, setStatusFilter] = useState<StandardStatus | undefined>()
  const [versionFilter, setVersionFilter] = useState('')

  // 分页
  const [standards, setStandards] = useState<InspectionStandard[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  // 子表编辑相关
  const [editingItems, setEditingItems] = useState<InspectionStandardItem[]>([])

  const loadStandards = async () => {
    setLoading(true)
    try {
      const response = await getStandards({
        page,
        page_size: pageSize,
        status: statusFilter,
        material_name: searchMaterialName || undefined,
        material_category: materialCategoryFilter,
        pharmacopeia: pharmacopeiaFilter,
        version: versionFilter || undefined,
      })
      if (response.code === 200) {
        setStandards(response.data)
        setTotal(response.meta?.total || 0)
      }
    } catch {
      message.error('加载检验标准列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadStandards()
  }, [page, pageSize, statusFilter, materialCategoryFilter, pharmacopeiaFilter])

  const handleSearch = () => {
    setPage(1)
    loadStandards()
  }

  const handleAdd = () => {
    setEditingStandard(null)
    setEditingItems([])
    form.resetFields()
    form.setFieldsValue({
      version: '1.0',
      material_category: MaterialCategory.RAW_MATERIAL,
    })
    setModalVisible(true)
  }

  const handleEdit = (record: InspectionStandard) => {
    setEditingStandard(record)
    setEditingItems(record.items || [])
    editForm.setFieldsValue({
      ...record,
      effective_date: record.effective_date ? new Date(record.effective_date) : undefined,
      obsolete_date: record.obsolete_date ? new Date(record.obsolete_date) : undefined,
    })
    setModalVisible(true)
  }

  const handleView = async (record: InspectionStandard) => {
    setViewingStandard(record)
    setDetailModalVisible(true)
  }

  const handleDelete = async (id: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个检验标准吗？',
      onOk: async () => {
        try {
          const response = await deleteStandard(id)
          if (response.code === 200) {
            message.success('删除成功')
            loadStandards()
          } else {
            message.error(response.message || '删除失败')
          }
        } catch {
          message.error('删除失败')
        }
      },
    })
  }

  const handleSubmitForApproval = async (id: string) => {
    try {
      const response = await submitStandardForApproval(id)
      if (response.code === 200) {
        message.success('已提交审批')
        loadStandards()
      } else {
        message.error(response.message || '提交失败')
      }
    } catch {
      message.error('提交失败')
    }
  }

  const handleCopy = async () => {
    if (!newVersion.trim()) {
      message.error('请输入新版本号')
      return
    }
    try {
      const response = await copyStandard({
        source_id: viewingStandard?.id || '',
        new_version: newVersion,
      })
      if (response.code === 200) {
        message.success('版本复制成功')
        setCopyModalVisible(false)
        setNewVersion('')
        loadStandards()
      } else {
        message.error(response.message || '复制失败')
      }
    } catch {
      message.error('复制失败')
    }
  }

  const handleObsolete = async () => {
    if (!obsoleteReason.trim()) {
      message.error('请输入作废原因')
      return
    }
    try {
      const response = await obsoleteStandard(viewingStandard?.id || '', { obsolete_reason: obsoleteReason })
      if (response.code === 200) {
        message.success('已提交作废申请')
        setObsoleteModalVisible(false)
        setObsoleteReason('')
        loadStandards()
      } else {
        message.error(response.message || '作废失败')
      }
    } catch {
      message.error('作废失败')
    }
  }

  const handleSubmit = async () => {
    try {
      const values = editingStandard ? await editForm.validateFields() : await form.validateFields()
      const formData: InspectionStandardFormData = {
        ...values,
        effective_date: values.effective_date?.toISOString(),
        obsolete_date: values.obsolete_date?.toISOString(),
        items: editingItems.map((item, index) => ({
          item_no: index + 1,
          item_name: item.item_name,
          test_method: item.test_method,
          instrument_code: item.instrument_code,
          reference_materials: item.reference_materials,
          limit_type: item.limit_type,
          limit_value: item.limit_value,
          item_category: item.item_category,
          is_critical: item.is_critical,
          notes: item.notes,
        })),
      }

      if (editingStandard) {
        const response = await updateStandard(editingStandard.id, formData)
        if (response.code === 200) {
          message.success('更新成功')
          setModalVisible(false)
          loadStandards()
        } else {
          message.error(response.message || '更新失败')
        }
      } else {
        const response = await createStandard(formData)
        if (response.code === 200) {
          message.success('创建成功')
          setModalVisible(false)
          loadStandards()
        } else {
          message.error(response.message || '创建失败')
        }
      }
    } catch (error) {
      console.error('表单验证失败:', error)
    }
  }

  const handleExport = async () => {
    setExportLoading(true)
    try {
      const response = await getStandards({ page: 1, page_size: 10000 })
      if (response.code === 200 && response.data.length > 0) {
        exportStandardsToCsv(response.data)
        message.success(`已导出 ${response.data.length} 条数据`)
      } else {
        message.warning('没有可导出的数据')
      }
    } catch {
      message.error('导出失败')
    } finally {
      setExportLoading(false)
    }
  }

  // 子表操作
  const handleAddItem = () => {
    setEditingItems([
      ...editingItems,
      {
        id: `temp_${Date.now()}`,
        standard_id: editingStandard?.id || '',
        item_no: editingItems.length + 1,
        item_name: '',
        limit_type: LimitType.UPPER_LIMIT,
        is_critical: false,
        created_at: '',
        updated_at: '',
      },
    ])
  }

  const handleRemoveItem = (index: number) => {
    setEditingItems(editingItems.filter((_, i) => i !== index))
  }

  const handleItemChange = (index: number, field: string, value: any) => {
    const newItems = [...editingItems]
    newItems[index] = { ...newItems[index], [field]: value }
    setEditingItems(newItems)
  }

  const columns: ColumnsType<InspectionStandard> = [
    {
      title: '标准编号',
      dataIndex: 'standard_no',
      key: 'standard_no',
      width: 150,
    },
    {
      title: '物料编码',
      dataIndex: 'material_code',
      key: 'material_code',
      width: 120,
    },
    {
      title: '物料名称',
      dataIndex: 'material_name',
      key: 'material_name',
      width: 180,
      ellipsis: true,
    },
    {
      title: '物料分类',
      dataIndex: 'material_category',
      key: 'material_category',
      width: 100,
      render: (val: MaterialCategory) =>
        MATERIAL_CATEGORY_OPTIONS.find(o => o.value === val)?.label || val,
    },
    {
      title: '药典',
      dataIndex: 'pharmacopeia',
      key: 'pharmacopeia',
      width: 100,
      render: (val: Pharmacopeia) =>
        PHARMACOPEIA_OPTIONS.find(o => o.value === val)?.label || val || '-',
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 80,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 110,
      render: (status: StandardStatus) => (
        <Tag color={getStatusColor(status)}>{getStatusLabel(status)}</Tag>
      ),
    },
    {
      title: '生效日期',
      dataIndex: 'effective_date',
      key: 'effective_date',
      width: 110,
      render: (date: string) => date ? new Date(date).toLocaleDateString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 260,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" icon={<HistoryOutlined />} onClick={() => handleView(record)}>
            查看
          </Button>
          {(record.status === StandardStatus.DRAFT || record.status === StandardStatus.REJECTED) && (
            <>
              <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
                编辑
              </Button>
              <Button type="link" size="small" icon={<SendOutlined />} onClick={() => handleSubmitForApproval(record.id)}>
                提交
              </Button>
            </>
          )}
          {record.status === StandardStatus.EFFECTIVE && (
            <Button type="link" size="small" icon={<CopyOutlined />} onClick={() => { setViewingStandard(record); setCopyModalVisible(true); }}>
              复制
            </Button>
          )}
          {record.status === StandardStatus.EFFECTIVE && (
            <Button type="link" size="small" danger icon={<StopOutlined />} onClick={() => { setViewingStandard(record); setObsoleteModalVisible(true); }}>
              作废
            </Button>
          )}
        </Space>
      ),
    },
  ]

  const isEditable = !editingStandard || editingStandard.status === StandardStatus.DRAFT || editingStandard.status === StandardStatus.REJECTED

  return (
    <div className="p-6">
      <Card
        title="检验标准维护"
        extra={
          <Space>
            <Tooltip title="导出当前筛选结果的检验标准数据">
              <Button icon={<DownloadOutlined />} onClick={handleExport} loading={exportLoading}>
                导出
              </Button>
            </Tooltip>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
              新建标准
            </Button>
          </Space>
        }
      >
        <Row gutter={16} className="mb-4">
          <Col span={5}>
            <Input
              placeholder="搜索物料名称"
              prefix={<SearchOutlined />}
              value={searchMaterialName}
              onChange={(e) => setSearchMaterialName(e.target.value)}
              onPressEnter={handleSearch}
            />
          </Col>
          <Col span={4}>
            <Select
              placeholder="物料分类"
              allowClear
              value={materialCategoryFilter}
              onChange={(value) => { setMaterialCategoryFilter(value); setPage(1); }}
              style={{ width: '100%' }}
              options={MATERIAL_CATEGORY_OPTIONS}
            />
          </Col>
          <Col span={4}>
            <Select
              placeholder="药典"
              allowClear
              value={pharmacopeiaFilter}
              onChange={(value) => { setPharmacopeiaFilter(value); setPage(1); }}
              style={{ width: '100%' }}
              options={PHARMACOPEIA_OPTIONS}
            />
          </Col>
          <Col span={3}>
            <Select
              placeholder="状态"
              allowClear
              value={statusFilter}
              onChange={(value) => { setStatusFilter(value); setPage(1); }}
              style={{ width: '100%' }}
              options={STANDARD_STATUS_OPTIONS}
            />
          </Col>
          <Col span={3}>
            <Input
              placeholder="版本号"
              value={versionFilter}
              onChange={(e) => setVersionFilter(e.target.value)}
            />
          </Col>
          <Col span={3}>
            <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
              查询
            </Button>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={standards}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1500 }}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (p, ps) => { setPage(p); setPageSize(ps); },
          }}
        />
      </Card>

      {/* 新建/编辑弹窗 */}
      <Modal
        title={editingStandard ? '编辑检验标准' : '新建检验标准'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={900}
        okText="确认"
        cancelText="取消"
      >
        <Form form={editingStandard ? editForm : form} layout="vertical" initialValues={editingStandard || undefined}>
          <Divider>基本信息</Divider>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="material_code"
                label="物料编码"
                rules={[{ required: true, message: '请输入物料编码' }]}
              >
                <Input placeholder="请输入物料编码" disabled={!!editingStandard} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="material_name" label="物料名称">
                <Input placeholder="请输入物料名称" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="cas_no" label="CAS号">
                <Input placeholder="请输入CAS号" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="material_category"
                label="物料分类"
                rules={[{ required: true, message: '请选择物料分类' }]}
              >
                <Select placeholder="请选择" options={MATERIAL_CATEGORY_OPTIONS} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="pharmacopeia" label="执行药典">
                <Select placeholder="请选择" allowClear options={PHARMACOPEIA_OPTIONS} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="version"
                label="版本号"
                rules={[{ required: true, message: '请输入版本号' }]}
              >
                <Input placeholder="如: 1.0" disabled={!!editingStandard} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="sop_no" label="SOP编号">
                <Input placeholder="请输入SOP编号" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="effective_date" label="生效日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} placeholder="请输入备注" />
          </Form.Item>

          <Divider>检验项目</Divider>
          <Button type="dashed" block icon={<PlusOutlined />} onClick={handleAddItem} disabled={!isEditable} className="mb-4">
            添加检验项目
          </Button>
          <Table
            dataSource={editingItems}
            rowKey={(record) => record.id}
            size="small"
            pagination={false}
            scroll={{ x: 1000 }}
            columns={[
              { title: '序号', dataIndex: 'item_no', width: 60, render: (_, __, index) => index + 1 },
              {
                title: '项目名称',
                dataIndex: 'item_name',
                width: 150,
                render: (val, _, index) => (
                  <Input value={val} onChange={(e) => handleItemChange(index, 'item_name', e.target.value)} disabled={!isEditable} />
                ),
              },
              {
                title: '检测方法',
                dataIndex: 'test_method',
                width: 150,
                render: (val, _, index) => (
                  <Input value={val} onChange={(e) => handleItemChange(index, 'test_method', e.target.value)} disabled={!isEditable} />
                ),
              },
              {
                title: '关联仪器',
                dataIndex: 'instrument_code',
                width: 120,
                render: (val, _, index) => (
                  <Input value={val} onChange={(e) => handleItemChange(index, 'instrument_code', e.target.value)} disabled={!isEditable} />
                ),
              },
              {
                title: '限度类型',
                dataIndex: 'limit_type',
                width: 100,
                render: (val, _, index) => (
                  <Select
                    value={val}
                    onChange={(value) => handleItemChange(index, 'limit_type', value)}
                    options={LIMIT_TYPE_OPTIONS}
                    disabled={!isEditable}
                  />
                ),
              },
              {
                title: '合格限值',
                dataIndex: 'limit_value',
                width: 120,
                render: (val, _, index) => (
                  <Input value={val} onChange={(e) => handleItemChange(index, 'limit_value', e.target.value)} disabled={!isEditable} />
                ),
              },
              {
                title: '项目分类',
                dataIndex: 'item_category',
                width: 100,
                render: (val, _, index) => (
                  <Select
                    value={val}
                    onChange={(value) => handleItemChange(index, 'item_category', value)}
                    options={ITEM_CATEGORY_OPTIONS}
                    allowClear
                    disabled={!isEditable}
                  />
                ),
              },
              {
                title: '关键',
                dataIndex: 'is_critical',
                width: 60,
                render: (val, _, index) => (
                  <input
                    type="checkbox"
                    checked={val}
                    onChange={(e) => handleItemChange(index, 'is_critical', e.target.checked)}
                    disabled={!isEditable}
                  />
                ),
              },
              {
                title: '操作',
                width: 60,
                render: (_, __, index) => (
                  isEditable ? (
                    <Button type="link" danger size="small" onClick={() => handleRemoveItem(index)}>删除</Button>
                  ) : null
                ),
              },
            ]}
          />
        </Form>
      </Modal>

      {/* 查看详情弹窗 */}
      <Modal
        title="检验标准详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>关闭</Button>,
        ]}
        width={900}
      >
        {viewingStandard && (
          <div>
            <Row gutter={16} className="mb-4">
              <Col span={8}><b>标准编号：</b>{viewingStandard.standard_no}</Col>
              <Col span={8}><b>物料编码：</b>{viewingStandard.material_code}</Col>
              <Col span={8}><b>物料名称：</b>{viewingStandard.material_name || '-'}</Col>
            </Row>
            <Row gutter={16} className="mb-4">
              <Col span={8}><b>CAS号：</b>{viewingStandard.cas_no || '-'}</Col>
              <Col span={8}><b>物料分类：</b>{MATERIAL_CATEGORY_OPTIONS.find(o => o.value === viewingStandard.material_category)?.label}</Col>
              <Col span={8}><b>药典：</b>{PHARMACOPEIA_OPTIONS.find(o => o.value === viewingStandard.pharmacopeia)?.label || '-'}</Col>
            </Row>
            <Row gutter={16} className="mb-4">
              <Col span={8}><b>版本：</b>{viewingStandard.version}</Col>
              <Col span={8}>
                <b>状态：</b>
                <Tag color={getStatusColor(viewingStandard.status)}>{getStatusLabel(viewingStandard.status)}</Tag>
              </Col>
              <Col span={8}><b>生效日期：</b>{viewingStandard.effective_date ? new Date(viewingStandard.effective_date).toLocaleDateString('zh-CN') : '-'}</Col>
            </Row>
            <Row gutter={16} className="mb-4">
              <Col span={12}><b>SOP编号：</b>{viewingStandard.sop_no || '-'}</Col>
            </Row>
            <Divider>检验项目</Divider>
            <Table
              dataSource={viewingStandard.items || []}
              rowKey="id"
              size="small"
              pagination={false}
              columns={[
                { title: '序号', dataIndex: 'item_no', width: 60 },
                { title: '项目名称', dataIndex: 'item_name' },
                { title: '检测方法', dataIndex: 'test_method' },
                { title: '关联仪器', dataIndex: 'instrument_code' },
                { title: '限度类型', dataIndex: 'limit_type', render: (val) => LIMIT_TYPE_OPTIONS.find(o => o.value === val)?.label },
                { title: '合格限值', dataIndex: 'limit_value' },
                { title: '项目分类', dataIndex: 'item_category', render: (val) => ITEM_CATEGORY_OPTIONS.find(o => o.value === val)?.label || '-' },
                { title: '关键', dataIndex: 'is_critical', render: (val) => val ? '是' : '否' },
              ]}
            />
          </div>
        )}
      </Modal>

      {/* 版本复制弹窗 */}
      <Modal
        title="版本复制"
        open={copyModalVisible}
        onCancel={() => { setCopyModalVisible(false); setNewVersion(''); }}
        footer={null}
      >
        <Form layout="vertical">
          <Form.Item label="新版本号" required rules={[{ required: true, message: '请输入新版本号' }]}>
            <Input
              placeholder="请输入新版本号，如: 2.0"
              value={newVersion}
              onChange={(e) => setNewVersion(e.target.value)}
            />
          </Form.Item>
        </Form>
        <div className="flex justify-end gap-2 mt-4">
          <Button onClick={() => { setCopyModalVisible(false); setNewVersion(''); }}>取消</Button>
          <Button type="primary" onClick={handleCopy}>确认复制</Button>
        </div>
      </Modal>

      {/* 作废弹窗 */}
      <Modal
        title="提交作废"
        open={obsoleteModalVisible}
        onOk={handleObsolete}
        onCancel={() => { setObsoleteModalVisible(false); setObsoleteReason(''); }}
      >
        <Form layout="vertical">
          <Form.Item label="作废原因" required rules={[{ required: true, message: '请输入作废原因' }]}>
            <Input.TextArea
              rows={4}
              value={obsoleteReason}
              onChange={(e) => setObsoleteReason(e.target.value)}
              placeholder="请输入作废原因"
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}