'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import {
  Card,
  Tabs,
  Table,
  Button,
  Space,
  Input,
  Select,
  Form,
  Tag,
  message,
  Popconfirm,
  DatePicker,
  Upload,
  Modal,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { UploadProps } from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  ReloadOutlined,
  ExperimentOutlined,
  BuildOutlined,
  MedicineBoxOutlined,
  FileTextOutlined,
  AppstoreOutlined,
  UploadOutlined,
  DownloadOutlined,
} from '@ant-design/icons'
import { useRouter } from 'next/navigation'
import {
  StorageCondition,
  Unit,
  TestItem,
  Equipment,
  ChromColumn,
  Medium,
  Reagent,
  StandardMaterial,
  MaterialStandard,
  ProductStandard,
  HplcReference,
  ApiResponse,
  EQ_STATUS_OPTIONS,
  STANDARD_STATUS_OPTIONS,
  CHROM_COLUMN_STATUS_OPTIONS,
  HPLC_REF_STATUS_OPTIONS,
} from '@/types/static-data'
import {
  listStorageCondition,
  listUnit,
  listTestItem,
  listEquipment,
  listChromColumn,
  listMedium,
  listReagent,
  listStandardMaterial,
  listMaterialStandard,
  listProductStandard,
  deleteStorageCondition,
  deleteUnit,
  deleteTestItem,
  deleteEquipment,
  deleteChromColumn,
  deleteMedium,
  deleteReagent,
  deleteStandardMaterial,
  deleteMaterialStandard,
  deleteProductStandard,
  deleteHplcReference,
} from '@/actions/static-data'
import {
  listStorageCondition as clientListStorageCondition,
  listUnit as clientListUnit,
  listTestItem as clientListTestItem,
  listEquipment as clientListEquipment,
  listChromColumn as clientListChromColumn,
  listMedium as clientListMedium,
  listReagent as clientListReagent,
  listStandardMaterial as clientListStandardMaterial,
  listMaterialStandard as clientListMaterialStandard,
  listProductStandard as clientListProductStandard,
  listHplcReference as clientListHplcReference,
  downloadHplcReferenceTemplate,
  batchImportHplcReference,
} from '@/lib/static-data-api'

const { RangePicker } = DatePicker

// ============ 通用列表组件 ============

interface ListPageProps {
  tabKey: string
  columns: ColumnsType<any>
  rowKey: string
  // Write operations via Server Action
  deleteFn?: (id: number) => Promise<any>
  // List query via client direct call (bypass Server Action network isolation)
  clientListFn: (params: any) => Promise<any>
  searchForm?: React.ReactNode
  // Import/Template download
  onTemplateDownload?: () => Promise<void>
  onBatchImport?: (file: File) => Promise<any>
  importModule?: string
}

function ListPanel({ tabKey, columns, rowKey, deleteFn, clientListFn, searchForm, onTemplateDownload, onBatchImport, importModule }: ListPageProps) {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [searchValues, setSearchValues] = useState<Record<string, any>>({})
  const [form] = Form.useForm()
  const [importModalOpen, setImportModalOpen] = useState(false)
  const [importLoading, setImportLoading] = useState(false)
  const router = useRouter()
  // Stable reference, no rebuild on tab switch
  const fetchDataRef = useRef<() => void>(() => {})

  const fetchData = useCallback(async (overrides: Record<string, any> = {}) => {
    setLoading(true)
    try {
      const params = { page, page_size: pageSize, ...searchValues, ...overrides }
      const res = await clientListFn(params)
      setData((res?.data ?? res ?? []) as any[])
      const totalVal = res?.meta?.total ?? (Array.isArray(res) ? res.length : 0)
      setTotal(totalVal)
    } catch (e: any) {
      message.error(e.message || '加载失败')
      console.error('[ListPanel] fetchData error:', e)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, searchValues, clientListFn])

  // 更新 ref，让 RangePicker 等可以直接调用
  useEffect(() => {
    fetchDataRef.current = fetchData
  }, [fetchData])

  // 仅在 page / pageSize / searchValues / tabKey 变化时重新加载
  useEffect(() => {
    setPage(1)
    fetchData()
  }, [searchValues]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetchData()
  }, [page, pageSize]) // eslint-disable-line react-hooks/exhaustive-deps

  // 暴露表单和搜索值给 RangePicker 回调
  useEffect(() => {
    ;(window as any).__listPanelForm__ = form
    ;(window as any).__listPanelSearchValues__ = searchValues
    ;(window as any).__currentListTab__ = tabKey
  }, [form, searchValues, tabKey])

  const handleSearch = (vals: any) => {
    setSearchValues(vals)
    setPage(1)
  }

  const handleReset = () => {
    form.resetFields()
    setSearchValues({})
    setPage(1)
  }

  const handleDelete = async (id: number) => {
    if (!deleteFn) return
    try {
      await deleteFn(id)
      message.success('删除成功')
      fetchDataRef.current()
    } catch (e: any) {
      message.error(e.message || '删除失败')
    }
  }

  const cols: ColumnsType<any> = [
    ...columns,
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: any, record: any) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />}
            onClick={() => router.push(`/quality/static-data/${tabKey}/${record[rowKey]}`)}>
            编辑
          </Button>
          {deleteFn && (
            <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record[rowKey])}
              okText="确定" cancelText="取消">
              <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  const handleTemplateDownload = async () => {
    if (!onTemplateDownload) return
    try {
      await onTemplateDownload()
      message.success('模板下载成功')
    } catch (e: any) {
      message.error(e.message || '模板下载失败')
    }
  }

  const handleImport = async (file: File) => {
    if (!onBatchImport) return
    setImportLoading(true)
    try {
      const res = await onBatchImport(file)
      message.success(res.message || '导入成功')
      setImportModalOpen(false)
      fetchDataRef.current()
    } catch (e: any) {
      message.error(e.message || '导入失败')
    } finally {
      setImportLoading(false)
    }
  }

  const uploadProps: UploadProps = {
    accept: '.xlsx,.xls',
    showUploadList: false,
    beforeUpload: (file) => {
      handleImport(file)
      return false
    },
  }

  return (
    <div>
      {searchForm && (
        <Card size="small" style={{ marginBottom: 12 }}>
          <Form form={form} layout="inline" onFinish={handleSearch} size="small">
            {searchForm}
            <Form.Item>
              <Space>
                <Button type="primary" htmlType="submit" icon={<SearchOutlined />}>查询</Button>
                <Button onClick={handleReset} icon={<ReloadOutlined />}>重置</Button>
              </Space>
            </Form.Item>
          </Form>
        </Card>
      )}
      <div style={{ marginBottom: 12 }}>
        <Space>
          <Button type="primary" icon={<PlusOutlined />}
            onClick={() => router.push(`/quality/static-data/${tabKey}/new`)}>
            新建
          </Button>
          {onTemplateDownload && (
            <Button icon={<DownloadOutlined />} onClick={handleTemplateDownload}>
              模板下载
            </Button>
          )}
          {onBatchImport && (
            <Button icon={<UploadOutlined />} onClick={() => setImportModalOpen(true)}>
              批量导入
            </Button>
          )}
        </Space>
      </div>
      <Table
        columns={cols}
        dataSource={data}
        rowKey={rowKey}
        loading={loading}
        pagination={{
          current: page, pageSize, total,
          showSizeChanger: true, showQuickJumper: true,
          showTotal: t => `共 ${t} 条`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps) },
        }}
      />
      <Modal
        title="导入数据"
        open={importModalOpen}
        onCancel={() => setImportModalOpen(false)}
        footer={null}
      >
        <p style={{ marginBottom: 16 }}>请选择 Excel 文件 (.xlsx, .xls) 进行数据导入</p>
        <Upload.Dragger {...uploadProps}>
          <p className="ant-upload-drag-icon">
            <UploadOutlined style={{ fontSize: 40, color: '#999' }} />
          </p>
          <p className="ant-upload-text">点击或拖拽文件上传</p>
          <p className="ant-upload-hint">支持 .xlsx, .xls 格式</p>
        </Upload.Dragger>
        {importLoading && <p style={{ marginTop: 8, color: '#1890ff' }}>导入中...</p>}
      </Modal>
    </div>
  )
}

// ============ 列表列定义 ============

const storageConditionColumns: ColumnsType<StorageCondition> = [
  { title: '编码', dataIndex: 'cond_code', width: 120 },
  { title: '名称', dataIndex: 'cond_name', width: 150 },
  { title: '温度范围', key: 'temp_range', width: 150, render: (_, r) => r.temp_min != null && r.temp_max != null ? `${r.temp_min}℃ ~ ${r.temp_max}℃` : '-' },
  { title: '湿度要求', dataIndex: 'humidity', width: 120 },
  { title: '状态', dataIndex: 'status', width: 80, render: v => <Tag color={v === 0 ? 'green' : 'red'}>{v === 0 ? '启用' : '停用'}</Tag> },
  { title: '备注', dataIndex: 'remark', ellipsis: true },
  { title: '创建时间', dataIndex: 'create_time', width: 160 },
]

const unitColumns: ColumnsType<Unit> = [
  { title: '编码', dataIndex: 'unit_code', width: 100 },
  { title: '名称', dataIndex: 'unit_name', width: 100 },
  { title: '类别', dataIndex: 'unit_type', width: 100 },
  { title: '换算基准值', dataIndex: 'base_value', width: 120 },
  { title: '状态', dataIndex: 'status', width: 80, render: v => <Tag color={v === 0 ? 'green' : 'red'}>{v === 0 ? '启用' : '停用'}</Tag> },
  { title: '备注', dataIndex: 'remark', ellipsis: true },
  { title: '创建时间', dataIndex: 'create_time', width: 160 },
]

const testItemColumns: ColumnsType<TestItem> = [
  { title: '编码', dataIndex: 'item_code', width: 100 },
  { title: '名称', dataIndex: 'item_name', width: 150 },
  { title: '分类', dataIndex: 'item_category', width: 100 },
  { title: '默认单位', dataIndex: 'unit_code', width: 100 },
  { title: '检验方法', dataIndex: 'method_desc', ellipsis: true },
  { title: '排序号', dataIndex: 'sort_num', width: 80 },
  { title: '状态', dataIndex: 'status', width: 80, render: v => <Tag color={v === 0 ? 'green' : 'red'}>{v === 0 ? '启用' : '停用'}</Tag> },
]

const equipmentColumns: ColumnsType<Equipment> = [
  { title: '设备编号', dataIndex: 'eq_code', width: 120 },
  { title: '设备名称', dataIndex: 'eq_name', width: 150 },
  { title: '型号', dataIndex: 'model', width: 120 },
  { title: '分类', dataIndex: 'eq_category', width: 100 },
  { title: '校准周期', dataIndex: 'cal_cycle', width: 80, render: v => `${v}月` },
  { title: '上次校准', dataIndex: 'last_cal_date', width: 110 },
  { title: '下次校准', dataIndex: 'next_cal_date', width: 110 },
  { title: '验证状态', dataIndex: 'verify_status', width: 100, render: v => {
    const color = v === '已完成' ? 'green' : v === '待验证' ? 'orange' : 'red'
    return <Tag color={color}>{v}</Tag>
  }},
  { title: '设备状态', dataIndex: 'eq_status', width: 80, render: v => EQ_STATUS_OPTIONS.find(o => o.value === v)?.label ?? v },
  { title: '存放位置', dataIndex: 'location', width: 120, ellipsis: true },
]

const chromColumnColumns: ColumnsType<ChromColumn> = [
  { title: '色谱柱编号', dataIndex: 'col_code', width: 130 },
  { title: '固定相类型', dataIndex: 'col_type', width: 100 },
  { title: '规格', dataIndex: 'spec', width: 120 },
  { title: '厂家', dataIndex: 'manufacturer', width: 120, ellipsis: true },
  { title: '已用次数', key: 'used', width: 90, render: (_, r) => `${r.used_times} / ${r.max_use_times}` },
  { title: '启用日期', dataIndex: 'use_start_date', width: 110 },
  { title: '状态', dataIndex: 'col_status', width: 80, render: v => CHROM_COLUMN_STATUS_OPTIONS.find(o => o.value === v)?.label ?? v },
  { title: '存放位置', dataIndex: 'location', width: 120, ellipsis: true },
]

const mediumColumns: ColumnsType<Medium> = [
  { title: '培养基编码', dataIndex: 'medium_code', width: 130 },
  { title: '培养基名称', dataIndex: 'medium_name', width: 150 },
  { title: '类型', dataIndex: 'medium_type', width: 100 },
  { title: '厂家批号', dataIndex: 'batch_no', width: 120 },
  { title: '有效期至', dataIndex: 'expire_date', width: 110 },
  { title: '库存', dataIndex: 'stock_num', width: 80 },
  { title: '最低库存', dataIndex: 'min_stock', width: 90 },
  { title: '验证状态', dataIndex: 'verify_status', width: 100 },
  { title: '状态', dataIndex: 'status', width: 80, render: v => <Tag color={v === 0 ? 'green' : 'red'}>{v === 0 ? '在用' : '停用'}</Tag> },
]

const reagentColumns: ColumnsType<Reagent> = [
  { title: '试剂编码', dataIndex: 'reagent_code', width: 130 },
  { title: '试剂名称', dataIndex: 'reagent_name', width: 150 },
  { title: 'CAS号', dataIndex: 'cas_no', width: 120 },
  { title: '纯度', dataIndex: 'purity', width: 80 },
  { title: '厂家', dataIndex: 'manufacturer', width: 120, ellipsis: true },
  { title: '有效期至', dataIndex: 'expire_date', width: 110 },
  { title: '库存', dataIndex: 'stock_num', width: 80 },
  { title: '存放库位', dataIndex: 'store_location', width: 100 },
  { title: '危险分类', dataIndex: 'danger_type', width: 100 },
  { title: '状态', dataIndex: 'status', width: 80, render: v => <Tag color={v === 0 ? 'green' : 'red'}>{v === 0 ? '启用' : '停用'}</Tag> },
]

const stdMatColumns: ColumnsType<StandardMaterial> = [
  { title: '标准品编码', dataIndex: 'std_code', width: 130 },
  { title: '标准品名称', dataIndex: 'std_name', width: 150 },
  { title: '类型', dataIndex: 'std_type', width: 80 },
  { title: '批号', dataIndex: 'batch_no', width: 120 },
  { title: '证书编号', dataIndex: 'cert_no', width: 140, ellipsis: true },
  { title: '有效期至', dataIndex: 'expire_date', width: 110 },
  { title: '剩余库存', dataIndex: 'remain_stock', width: 90 },
  { title: '最低库存', dataIndex: 'min_stock', width: 90 },
  { title: '状态', dataIndex: 'status', width: 80, render: v => ['在用', '封存', '报废'][v] ?? v },
]

const matStdColumns: ColumnsType<MaterialStandard> = [
  { title: '物料编码', dataIndex: 'material_code', width: 120 },
  { title: '物料名称', dataIndex: 'material_name', width: 150 },
  { title: '物料类别', dataIndex: 'material_type', width: 90 },
  { title: '规格', dataIndex: 'spec', width: 100 },
  { title: '标准来源', dataIndex: 'standard_source', width: 100 },
  { title: '标准编号', dataIndex: 'standard_no', width: 120 },
  { title: '版本', dataIndex: 'version', width: 70 },
  { title: '状态', dataIndex: 'status', width: 80, render: v => {
    const labels = ['草稿', '待审核', '已生效', '已作废']
    return <Tag color={v === 2 ? 'green' : v === 3 ? 'red' : 'default'}>{labels[v] ?? v}</Tag>
  }},
  { title: '生效日期', dataIndex: 'effect_date', width: 110 },
]

const prodStdColumns: ColumnsType<ProductStandard> = [
  { title: '产品编码', dataIndex: 'product_code', width: 120 },
  { title: '产品名称', dataIndex: 'product_name', width: 150 },
  { title: '商品名', dataIndex: 'trade_name', width: 120 },
  { title: '剂型', dataIndex: 'dosage_form', width: 80 },
  { title: '有效期', dataIndex: 'valid_period', width: 80, render: v => `${v}月` },
  { title: '注册标准号', dataIndex: 'reg_standard_no', width: 130, ellipsis: true },
  { title: '版本', dataIndex: 'version', width: 70 },
  { title: '状态', dataIndex: 'status', width: 80, render: v => {
    const labels = ['草稿', '待审核', '已生效', '已作废']
    return <Tag color={v === 2 ? 'green' : v === 3 ? 'red' : 'default'}>{labels[v] ?? v}</Tag>
  }},
]

const hplcRefColumns: ColumnsType<HplcReference> = [
  { title: '对照品编号', dataIndex: 'ref_code', width: 110, fixed: 'left' },
  { title: '对照品名称', dataIndex: 'ref_name', width: 180, ellipsis: true },
  { title: 'CAS号', dataIndex: 'cas_no', width: 110 },
  { title: '规格', dataIndex: 'spec', width: 70 },
  { title: '纯度(%)', dataIndex: 'purity', width: 80, render: v => v ? `${Number(v).toFixed(2)}%` : '-' },
  { title: '数量', dataIndex: 'quantity', width: 60, render: v => v ?? '-' },
  { title: '库存状态', dataIndex: 'stock_status', width: 90, ellipsis: true },
  { title: '开瓶日期', dataIndex: 'open_date', width: 100 },
  { title: '有效期至', dataIndex: 'expire_date', width: 100, render: v => v || '-' },
  { title: '存放位置', dataIndex: 'location', width: 90, ellipsis: true },
  { title: 'COA', dataIndex: 'has_coa', width: 60, render: v => v ? '✓' : '-' },
  { title: '状态', dataIndex: 'ref_status', width: 80, render: v => HPLC_REF_STATUS_OPTIONS.find(o => o.value === v)?.label ?? v },
]

// ============ 主页面 ============

export default function StaticDataPage() {
  const [activeTab, setActiveTab] = useState('hplc-reference')

  const tabs = [
    { key: 'hplc-reference', label: '液相对照品', icon: <ExperimentOutlined /> },
    { key: 'storage-condition', label: '贮存条件', icon: <AppstoreOutlined /> },
    { key: 'unit', label: '计量单位', icon: <AppstoreOutlined /> },
    { key: 'test-item', label: '检验项目', icon: <ExperimentOutlined /> },
    { key: 'equipment', label: '检测设备', icon: <BuildOutlined /> },
    { key: 'chrom-column', label: '色谱柱', icon: <ExperimentOutlined /> },
    { key: 'medium', label: '培养基', icon: <MedicineBoxOutlined /> },
    { key: 'reagent', label: '试剂', icon: <MedicineBoxOutlined /> },
    { key: 'standard-material', label: '标准物质', icon: <MedicineBoxOutlined /> },
    { key: 'material-standard', label: '物料质量标准', icon: <FileTextOutlined /> },
    { key: 'product-standard', label: '产品质量标准', icon: <FileTextOutlined /> },
  ]

  const renderTab = (key: string) => {
    switch (key) {
      case 'storage-condition':
        return (
          <ListPanel tabKey={key} columns={storageConditionColumns} rowKey="id"
            clientListFn={clientListStorageCondition}
            deleteFn={deleteStorageCondition}
            searchForm={<>
              <Form.Item name="cond_code" label="编码"><Input placeholder="编码" style={{ width: 120 }} /></Form.Item>
              <Form.Item name="cond_name" label="名称"><Input placeholder="名称" style={{ width: 120 }} /></Form.Item>
              <Form.Item name="status" label="状态">
                <Select placeholder="状态" allowClear style={{ width: 100 }}>
                  <Select.Option value={0}>启用</Select.Option>
                  <Select.Option value={1}>停用</Select.Option>
                </Select>
              </Form.Item>
            </>}
          />
        )
      case 'unit':
        return (
          <ListPanel tabKey={key} columns={unitColumns} rowKey="id"
            clientListFn={clientListUnit}
            deleteFn={deleteUnit}
            searchForm={<>
              <Form.Item name="unit_code" label="编码"><Input placeholder="编码" style={{ width: 120 }} /></Form.Item>
              <Form.Item name="unit_name" label="名称"><Input placeholder="名称" style={{ width: 120 }} /></Form.Item>
              <Form.Item name="unit_type" label="类别">
                <Select placeholder="类别" allowClear style={{ width: 120 }}>
                  {['质量', '体积', '浓度', '微生物', '比率'].map(v => <Select.Option key={v} value={v}>{v}</Select.Option>)}
                </Select>
              </Form.Item>
            </>}
          />
        )
      case 'test-item':
        return (
          <ListPanel tabKey={key} columns={testItemColumns} rowKey="id"
            clientListFn={clientListTestItem}
            deleteFn={deleteTestItem}
            searchForm={<>
              <Form.Item name="item_code" label="编码"><Input placeholder="编码" style={{ width: 120 }} /></Form.Item>
              <Form.Item name="item_name" label="名称"><Input placeholder="名称" style={{ width: 120 }} /></Form.Item>
              <Form.Item name="item_category" label="分类">
                <Select placeholder="分类" allowClear style={{ width: 110 }}>
                  {['理化', '仪器分析', '微生物'].map(v => <Select.Option key={v} value={v}>{v}</Select.Option>)}
                </Select>
              </Form.Item>
            </>}
          />
        )
      case 'equipment':
        return (
          <ListPanel tabKey={key} columns={equipmentColumns} rowKey="id"
            clientListFn={clientListEquipment}
            deleteFn={deleteEquipment}
            searchForm={<>
              <Form.Item name="eq_code" label="设备编号"><Input placeholder="设备编号" style={{ width: 120 }} /></Form.Item>
              <Form.Item name="eq_name" label="设备名称"><Input placeholder="设备名称" style={{ width: 120 }} /></Form.Item>
              <Form.Item name="eq_category" label="分类">
                <Select placeholder="分类" allowClear style={{ width: 110 }}>
                  {['色谱类', '称量类', '灭菌类', '微生物类'].map(v => <Select.Option key={v} value={v}>{v}</Select.Option>)}
                </Select>
              </Form.Item>
              <Form.Item name="start_date" label="下次校准日期" hidden><Input /></Form.Item>
              <Form.Item name="end_date" label=" " colon={false}><RangePicker format="YYYY-MM-DD" style={{ width: 240 }} onChange={(_, dateStrings) => {
                const form = (window as any).__listPanelForm__
                if (form) {
                  form.setFieldsValue({ start_date: dateStrings[0] || undefined, end_date: dateStrings[1] || undefined })
                }
              }} /></Form.Item>
            </>}
          />
        )
      case 'chrom-column':
        return (
          <ListPanel tabKey={key} columns={chromColumnColumns} rowKey="id"
            clientListFn={clientListChromColumn}
            deleteFn={deleteChromColumn}
            searchForm={<>
              <Form.Item name="col_code" label="色谱柱编号"><Input placeholder="编号" style={{ width: 130 }} /></Form.Item>
              <Form.Item name="col_type" label="固定相类型"><Input placeholder="如C18" style={{ width: 100 }} /></Form.Item>
              <Form.Item name="col_status" label="状态">
                <Select placeholder="状态" allowClear style={{ width: 100 }}>
                  {CHROM_COLUMN_STATUS_OPTIONS.map(o => <Select.Option key={o.value} value={o.value}>{o.label}</Select.Option>)}
                </Select>
              </Form.Item>
            </>}
          />
        )
      case 'medium':
        return (
          <ListPanel tabKey={key} columns={mediumColumns} rowKey="id"
            clientListFn={clientListMedium}
            deleteFn={deleteMedium}
            searchForm={<>
              <Form.Item name="medium_code" label="培养基编码"><Input placeholder="编码" style={{ width: 130 }} /></Form.Item>
              <Form.Item name="medium_name" label="培养基名称"><Input placeholder="名称" style={{ width: 130 }} /></Form.Item>
              <Form.Item name="status" label="状态">
                <Select placeholder="状态" allowClear style={{ width: 100 }}>
                  <Select.Option value={0}>在用</Select.Option>
                  <Select.Option value={1}>停用</Select.Option>
                </Select>
              </Form.Item>
              <Form.Item name="expire_start" label="有效期至" hidden><Input /></Form.Item>
              <Form.Item name="expire_end" label=" " colon={false}><RangePicker format="YYYY-MM-DD" style={{ width: 240 }} onChange={(_, dateStrings) => {
                const form = (window as any).__listPanelForm__
                if (form) {
                  form.setFieldsValue({ expire_start: dateStrings[0] || undefined, expire_end: dateStrings[1] || undefined })
                }
              }} /></Form.Item>
            </>}
          />
        )
      case 'reagent':
        return (
          <ListPanel tabKey={key} columns={reagentColumns} rowKey="id"
            clientListFn={clientListReagent}
            deleteFn={deleteReagent}
            searchForm={<>
              <Form.Item name="reagent_code" label="试剂编码"><Input placeholder="编码" style={{ width: 130 }} /></Form.Item>
              <Form.Item name="reagent_name" label="试剂名称"><Input placeholder="名称" style={{ width: 130 }} /></Form.Item>
              <Form.Item name="danger_type" label="危险分类">
                <Select placeholder="危险分类" allowClear style={{ width: 110 }}>
                  {['易燃', '易爆', '有毒', '腐蚀', '氧化'].map(v => <Select.Option key={v} value={v}>{v}</Select.Option>)}
                </Select>
              </Form.Item>
              <Form.Item name="expire_start" label="有效期至" hidden><Input /></Form.Item>
              <Form.Item name="expire_end" label=" " colon={false}><RangePicker format="YYYY-MM-DD" style={{ width: 240 }} onChange={(_, dateStrings) => {
                const form = (window as any).__listPanelForm__
                if (form) {
                  form.setFieldsValue({ expire_start: dateStrings[0] || undefined, expire_end: dateStrings[1] || undefined })
                }
              }} /></Form.Item>
            </>}
          />
        )
      case 'standard-material':
        return (
          <ListPanel tabKey={key} columns={stdMatColumns} rowKey="id"
            clientListFn={clientListStandardMaterial}
            deleteFn={deleteStandardMaterial}
            searchForm={<>
              <Form.Item name="std_code" label="标准品编码"><Input placeholder="编码" style={{ width: 130 }} /></Form.Item>
              <Form.Item name="std_name" label="标准品名称"><Input placeholder="名称" style={{ width: 130 }} /></Form.Item>
              <Form.Item name="std_type" label="类型">
                <Select placeholder="类型" allowClear style={{ width: 100 }}>
                  {['法定', '工作', '自制'].map(v => <Select.Option key={v} value={v}>{v}</Select.Option>)}
                </Select>
              </Form.Item>
              <Form.Item name="expire_start" label="有效期至" hidden><Input /></Form.Item>
              <Form.Item name="expire_end" label=" " colon={false}><RangePicker format="YYYY-MM-DD" style={{ width: 240 }} onChange={(_, dateStrings) => {
                const form = (window as any).__listPanelForm__
                if (form) {
                  form.setFieldsValue({ expire_start: dateStrings[0] || undefined, expire_end: dateStrings[1] || undefined })
                }
              }} /></Form.Item>
            </>}
          />
        )
      case 'material-standard':
        return (
          <ListPanel tabKey={key} columns={matStdColumns} rowKey="id"
            clientListFn={clientListMaterialStandard}
            deleteFn={deleteMaterialStandard}
            searchForm={<>
              <Form.Item name="material_code" label="物料编码"><Input placeholder="编码" style={{ width: 120 }} /></Form.Item>
              <Form.Item name="material_name" label="物料名称"><Input placeholder="名称" style={{ width: 130 }} /></Form.Item>
              <Form.Item name="material_type" label="物料类别">
                <Select placeholder="类别" allowClear style={{ width: 100 }}>
                  {['原料', '辅料', '包材', '中间体'].map(v => <Select.Option key={v} value={v}>{v}</Select.Option>)}
                </Select>
              </Form.Item>
            </>}
          />
        )
      case 'product-standard':
        return (
          <ListPanel tabKey={key} columns={prodStdColumns} rowKey="id"
            clientListFn={clientListProductStandard}
            deleteFn={deleteProductStandard}
            searchForm={<>
              <Form.Item name="product_code" label="产品编码"><Input placeholder="编码" style={{ width: 120 }} /></Form.Item>
              <Form.Item name="product_name" label="产品名称"><Input placeholder="名称" style={{ width: 130 }} /></Form.Item>
              <Form.Item name="status" label="状态">
                <Select placeholder="状态" allowClear style={{ width: 100 }}>
                  {STANDARD_STATUS_OPTIONS.map(o => <Select.Option key={o.value} value={o.value}>{o.label}</Select.Option>)}
                </Select>
              </Form.Item>
            </>}
          />
        )
      case 'hplc-reference':
        return (
          <ListPanel tabKey={key} columns={hplcRefColumns} rowKey="id"
            clientListFn={clientListHplcReference}
            deleteFn={deleteHplcReference}
            onTemplateDownload={downloadHplcReferenceTemplate}
            onBatchImport={batchImportHplcReference}
            importModule="hplc-reference"
            searchForm={<>
              <Form.Item name="ref_code" label="对照品编号"><Input placeholder="编号" style={{ width: 110 }} /></Form.Item>
              <Form.Item name="ref_name" label="对照品名称"><Input placeholder="名称" style={{ width: 130 }} /></Form.Item>
              <Form.Item name="cas_no" label="CAS号"><Input placeholder="CAS号" style={{ width: 110 }} /></Form.Item>
              <Form.Item name="ref_status" label="状态">
                <Select placeholder="状态" allowClear style={{ width: 90 }}>
                  {HPLC_REF_STATUS_OPTIONS.map(o => <Select.Option key={o.value} value={o.value}>{o.label}</Select.Option>)}
                </Select>
              </Form.Item>
              <Form.Item name="has_coa" label="COA">
                <Select placeholder="COA" allowClear style={{ width: 70 }}>
                  <Select.Option value={true}>有</Select.Option>
                  <Select.Option value={false}>无</Select.Option>
                </Select>
              </Form.Item>
              <Form.Item name="expire_start" label="有效期" hidden><Input /></Form.Item>
              <Form.Item name="expire_end" label=" " colon={false}><RangePicker format="YYYY-MM-DD" style={{ width: 220 }} placeholder={['有效期起','有效期止']} onChange={(_, dateStrings) => {
                const form = (window as any).__listPanelForm__
                if (form) {
                  form.setFieldsValue({ expire_start: dateStrings[0] || undefined, expire_end: dateStrings[1] || undefined })
                }
              }} /></Form.Item>
            </>}
          />
        )
      default:
        return <div style={{ padding: 40, textAlign: 'center', color: '#999' }}>建设中...</div>
    }
  }

  return (
    <div style={{ padding: '0 24px' }}>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>业务静态数据</h2>
      </div>
      <Card styles={{ body: { padding: 0 } }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          tabPlacement={"left" as any}
          style={{ minHeight: 500 }}
          tabBarStyle={{ width: 170, borderRight: '1px solid #f0f0f0', margin: 0 }}
          items={tabs.map(t => ({
            key: t.key,
            label: <span>{t.icon} {t.label}</span>,
            children: <div style={{ padding: '16px 20px' }}>{renderTab(t.key)}</div>,
          }))}
        />
      </Card>
    </div>
  )
}