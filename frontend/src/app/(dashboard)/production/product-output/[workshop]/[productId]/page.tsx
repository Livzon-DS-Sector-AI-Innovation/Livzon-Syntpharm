'use client'

import { useEffect, useState, useRef } from 'react'
import {
  Table,
  Button,
  Space,
  Input,
  Modal,
  Form,
  InputNumber,
  Card,
  DatePicker,
  Typography,
  Upload,
  App,
  Row,
  Col,
  Statistic,
  Tag,
  Breadcrumb,
  Dropdown,
  Alert,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
  UploadOutlined,
  CloudSyncOutlined,
  DownloadOutlined,
  FileExcelOutlined,
  HomeOutlined,
  UndoOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import {
  getProductOutputs,
  createProductOutput,
  updateProductOutput,
  deleteProductOutput,
  importProductOutputs,
  previewImport,
  undoImport,
  importFromBitable,
  batchDeleteProductOutputs,
  getSummary,
  pushToFeishu,
  pullFromFeishu,
} from '@/actions/product-output'
import { getProduct } from '@/actions/product'
import type { ProductOutput, ProductOutputFormData } from '@/types/product-output'
import ProductSyncConfig from '@/components/production/product/ProductSyncConfig'
import type { Product } from '@/types/product'
import dayjs from 'dayjs'

const { Title, Text } = Typography

export default function ProductOutputRecordsPage() {
  const router = useRouter()
  const params = useParams()
  const workshop = decodeURIComponent(params.workshop as string)
  const productId = params.productId as string
  const { message } = App.useApp()

  const [product, setProduct] = useState<Product | null>(null)
  const [records, setRecords] = useState<ProductOutput[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [loading, setLoading] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null)

  const [modalVisible, setModalVisible] = useState(false)
  const [editingRecord, setEditingRecord] = useState<ProductOutput | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [form] = Form.useForm()

  const [importModalVisible, setImportModalVisible] = useState(false)
  const [previewData, setPreviewData] = useState<any>(null)
  const [lastBatchId, setLastBatchId] = useState<string | null>(null)
  const [importing, setImporting] = useState(false)
  const [importFile, setImportFile] = useState<File | null>(null)
  const [bitableModalVisible, setBitableModalVisible] = useState(false)
  const [bitableUrl, setBitableUrl] = useState('')
  const [bitableImporting, setBitableImporting] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [lastSyncAt, setLastSyncAt] = useState<string | null>(null)
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [sortInfo, setSortInfo] = useState<{ field: string; order: 'asc' | 'desc' } | null>(null)

  const [summary, setSummary] = useState<{
    daily: number
    monthly: number
    yearly: number
  }>({ daily: 0, monthly: 0, yearly: 0 })

  const loadProduct = async () => {
    try {
      const response = await getProduct(productId)
      if (response.code === 200) {
        setProduct(response.data)
      }
    } catch {
      message.error('加载产品信息失败')
    }
  }

  const loadRecords = async () => {
    setLoading(true)
    try {
      const params: any = {
        page,
        page_size: pageSize,
        product_id: productId,
      }
      if (sortInfo) {
        params.sort_by = sortInfo.field
        params.sort_order = sortInfo.order
      }
      if (searchText) params.batch_no = searchText
      if (dateRange?.[0]) params.start_date = dateRange[0].format('YYYY-MM-DD')
      if (dateRange?.[1]) params.end_date = dateRange[1].format('YYYY-MM-DD')

      const response = await getProductOutputs(params)
      if (response.code === 200) {
        setRecords(response.data || [])
        setTotal(response.meta?.total || 0)
      }
    } catch {
      message.error('加载数据失败')
    } finally {
      setLoading(false)
    }
  }

  const loadSummary = async () => {
    try {
      const today = dayjs().format('YYYY-MM-DD')
      const month = dayjs().format('YYYY-MM')
      const year = dayjs().year()

      const [dailyRes, monthlyRes, yearlyRes] = await Promise.all([
        getSummary({ target_date: today, product_id: productId }),
        getSummary({ month, product_id: productId }),
        getSummary({ year, product_id: productId }),
      ])

      setSummary({
        daily: dailyRes.data?.grand_total || 0,
        monthly: monthlyRes.data?.grand_total || 0,
        yearly: yearlyRes.data?.grand_total || 0,
      })
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    loadProduct()
  }, [productId])

  useEffect(() => {
    loadRecords()
  }, [page, pageSize, productId, sortInfo])

  useEffect(() => {
    loadSummary()
  }, [productId])

  const handleSearch = () => {
    setPage(1)
    loadRecords()
  }

  const handleAdd = () => {
    setEditingRecord(null)
    form.resetFields()
    form.setFieldsValue({
      production_date: dayjs(),
      unit: 'kg',
      notes: '生产中',
    })
    setModalVisible(true)
  }

  const handleEdit = (record: ProductOutput) => {
    setEditingRecord(record)
    form.setFieldsValue({
      ...record,
      production_date: dayjs(record.production_date),
      end_date: record.end_date ? dayjs(record.end_date) : undefined,
    })
    setModalVisible(true)
  }

  const handleDelete = (id: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这条记录吗？',
      onOk: async () => {
        try {
          const response = await deleteProductOutput(id)
          if (response.code === 200) {
            message.success('删除成功')
            loadRecords()
            loadSummary()
          } else {
            message.error(response.message || '删除失败')
          }
        } catch {
          message.error('删除失败')
        }
      },
    })
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      const data: ProductOutputFormData = {
        product_id: productId,
        workshop: workshop,
        product_name: product?.name || '',
        batch_no: values.batch_no,
        production_date: values.production_date.format('YYYY-MM-DD'),
        end_date: values.end_date?.format('YYYY-MM-DD') || undefined,
        weight: values.weight || 0,
        unit: values.unit || 'kg',
        notes: values.notes,
      }

      setSubmitting(true)
      let response
      if (editingRecord) {
        response = await updateProductOutput(editingRecord.id, data)
      } else {
        response = await createProductOutput(data)
      }

      if (response.code === 200) {
        message.success(editingRecord ? '更新成功' : '创建成功')
        setModalVisible(false)
        loadRecords()
        loadSummary()
      } else {
        message.error(response.message || '操作失败')
      }
    } catch {
      message.error('操作失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleImport = async (file: File) => {
    setImportFile(file)
    const formData = new FormData()
    formData.append('file', file)
    try {
      const response = await previewImport(formData)
      if (response.code === 200) {
        setPreviewData(response.data)
        message.info(`预览完成：共 ${response.data.total_rows} 行，可导入 ${response.data.new_records} 行`)
      } else {
        message.error(response.message || '预览失败')
      }
    } catch {
      message.error('预览失败')
    }
    return false
  }

  const handleConfirmImport = async () => {
    if (!previewData || !importFile) return
    setImporting(true)
    try {
      const formData = new FormData()
      formData.append('file', importFile)
      const response = await importProductOutputs(formData)
      if (response.code === 200) {
        message.success(response.message || '导入成功')
        setLastBatchId(response.data?.batch_id)
        setImportModalVisible(false)
        setPreviewData(null)
        setImportFile(null)
        loadRecords()
        loadSummary()
      } else {
        message.error(response.message || '导入失败')
      }
    } catch {
      message.error('导入失败')
    } finally {
      setImporting(false)
    }
  }

  const handleUndoImport = async () => {
    if (!lastBatchId) {
      message.warning('没有可撤销的导入记录')
      return
    }
    Modal.confirm({
      title: '确认撤销',
      content: `确定要撤销批次 ${lastBatchId} 的导入记录吗？`,
      okText: '撤销',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await undoImport(lastBatchId)
          if (response.code === 200) {
            message.success(response.message || '撤销成功')
            setLastBatchId(null)
            loadRecords()
            loadSummary()
          } else {
            message.error(response.message || '撤销失败')
          }
        } catch {
          message.error('撤销失败')
        }
      },
    })
  }

  const handleBatchDelete = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请选择要删除的记录')
      return
    }
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除选中的 ${selectedRowKeys.length} 条记录吗？`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await batchDeleteProductOutputs(selectedRowKeys.map(String))
          if (response.code === 200) {
            message.success(response.message || '批量删除成功')
            setSelectedRowKeys([])
            loadRecords()
            loadSummary()
          } else {
            message.error(response.message || '批量删除失败')
          }
        } catch {
          message.error('批量删除失败')
        }
      },
    })
  }

  const handlePushToFeishu = async () => {
    setSyncing(true)
    try {
      const res = await pushToFeishu(productId)
      if (res.code === 200) {
        message.success(res.data?.message || '推送成功')
        loadRecords()
      } else {
        message.error(res.message || '推送失败')
      }
    } catch {
      message.error('推送失败')
    } finally {
      setSyncing(false)
    }
  }

  const handlePullFromFeishu = async () => {
    setSyncing(true)
    try {
      const res = await pullFromFeishu(productId)
      if (res.code === 200) {
        message.success(res.data?.message || '拉取成功')
        loadRecords()
      } else {
        message.error(res.message || '拉取失败')
      }
    } catch {
      message.error('拉取失败')
    } finally {
      setSyncing(false)
    }
  }


  const handlePreviewPush = async () => {
    try {
      const res = await fetch(`/api/v1/production/product-sync-config/${productId}/preview-push`, {
        method: 'POST',
      })
      const data = await res.json()
      if (data.code === 200) {
        Modal.info({
          title: '推送预览',
          content: (
            <div>
              <p>新增：{data.data.to_create} 条</p>
              <p>更新：{data.data.to_update} 条</p>
              <p>跳过：{data.data.to_skip} 条</p>
            </div>
          ),
          onOk: () => handlePushToFeishu(),
        })
      } else {
        message.error(data.message || '预览失败')
      }
    } catch {
      message.error('预览失败')
    }
  }

  const handlePreviewPull = async () => {
    try {
      const res = await fetch(`/api/v1/production/product-sync-config/${productId}/preview-pull`, {
        method: 'POST',
      })
      const data = await res.json()
      if (data.code === 200) {
        Modal.info({
          title: '拉取预览',
          content: (
            <div>
              <p>新增：{data.data.to_create} 条</p>
              <p>更新：{data.data.to_update} 条</p>
            </div>
          ),
          onOk: () => handlePullFromFeishu(),
        })
      } else {
        message.error(data.message || '预览失败')
      }
    } catch {
      message.error('预览失败')
    }
  }

  const handleUndoLastSync = async () => {
    Modal.confirm({
      title: '确认撤销',
      content: '确定要撤销上次同步操作吗？此操作不可恢复。',
      onOk: async () => {
        try {
          const res = await fetch(`/api/v1/production/product-sync-config/${productId}/undo-last-sync`, {
            method: 'POST',
          })
          const data = await res.json()
          if (data.code === 200) {
            message.success(data.message || '撤销成功')
            loadRecords()
          } else {
            message.error(data.message || '撤销失败')
          }
        } catch {
          message.error('撤销失败')
        }
      },
    })
  }

  const handleImportFromBitable = async () => {
    // 解析飞书多维表格链接
    let appToken = ''
    let tableId = ''
    
    try {
      // 尝试从 URL 解析
      const url = new URL(bitableUrl)
      const pathParts = url.pathname.split('/')
      
      // 飞书多维表格 URL 格式：/base/{app_token}?table={table_id}
      const baseIndex = pathParts.indexOf('base')
      if (baseIndex >= 0 && pathParts[baseIndex + 1]) {
        appToken = pathParts[baseIndex + 1]
      }
      
      // 从 query 参数获取 table_id
      const tableParam = url.searchParams.get('table')
      if (tableParam) {
        tableId = tableParam
      }
      
      // 如果 URL 解析失败，尝试直接输入 app_token 和 table_id
      if (!appToken || !tableId) {
        // 尝试从输入中解析（用户可能直接粘贴了 app_token 和 table_id）
        const parts = bitableUrl.trim().split(/[\s,]+/)
        if (parts.length >= 2) {
          appToken = parts[0]
          tableId = parts[1]
        }
      }
    } catch {
      // URL 解析失败，尝试直接分割
      const parts = bitableUrl.trim().split(/[\s,]+/)
      if (parts.length >= 2) {
        appToken = parts[0]
        tableId = parts[1]
      }
    }
    
    if (!appToken) {
      message.error('请输入有效的飞书多维表格链接或 app_token')
      return
    }
    
    setBitableImporting(true)
    try {
      const response = await importFromBitable(appToken, tableId)
      if (response.code === 200) {
        message.success(response.message || '从飞书导入成功')
        setBitableModalVisible(false)
        setBitableUrl('')
        loadRecords()
        loadSummary()
      } else {
        message.error(response.message || '从飞书导入失败')
      }
    } catch {
      message.error('从飞书导入失败')
    } finally {
      setBitableImporting(false)
    }
  }

  const handleExport = () => {
    const params = new URLSearchParams()
    params.set('product_id', productId)
    if (searchText) params.set('batch_no', searchText)
    if (dateRange?.[0]) params.set('start_date', dateRange[0].format('YYYY-MM-DD'))
    if (dateRange?.[1]) params.set('end_date', dateRange[1].format('YYYY-MM-DD'))
    window.open(`/api/v1/production/product-output/export?${params.toString()}`)
  }

  // 表单值变化监听：当结束日期被清空时，自动设置备注为"生产中"
  const handleFormValuesChange = (changedValues: any, allValues: any) => {
    if ('end_date' in changedValues) {
      if (!changedValues.end_date && allValues.production_date) {
        // 结束日期被清空，且有生产日期，自动设置备注为"生产中"
        form.setFieldsValue({ notes: '生产中' })
      } else if (changedValues.end_date) {
        // 填写了结束日期，清空备注（如果当前是"生产中"）
        if (allValues.notes === '生产中') {
          form.setFieldsValue({ notes: undefined })
        }
      }
    }
  }

  const columns: ColumnsType<ProductOutput> = [
    {
      title: '批号',
      dataIndex: 'batch_no',
      key: 'batch_no',
      width: 150,
      sorter: true,
    },
    {
      title: '生产日期',
      dataIndex: 'production_date',
      key: 'production_date',
      width: 120,
      sorter: true,
      defaultSortOrder: 'descend',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD'),
    },
    {
      title: '结束日期',
      dataIndex: 'end_date',
      key: 'end_date',
      width: 120,
      sorter: true,
      render: (date: string | null) => date ? dayjs(date).format('YYYY-MM-DD') : '-',
    },
    {
      title: '重量',
      dataIndex: 'weight',
      key: 'weight',
      width: 100,
      align: 'right',
      sorter: true,
      render: (weight: number, record) => `${weight} ${record.unit}`,
    },
    {
      title: '备注',
      dataIndex: 'notes',
      key: 'notes',
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      fixed: 'right' as const,
      render: (_, record) => (
        <Space size={4}>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)}>
            删除
          </Button>
        </Space>
      ),
    },
  ]

  const handleTableChange = (_pagination: any, _filters: any, sorter: any) => {
    console.log('handleTableChange called', { sorter, sorterField: sorter?.field, sorterOrder: sorter?.order })
    if (sorter && sorter.order) {
      const fieldMap: Record<string, string> = {
        batch_no: 'batch_no',
        production_date: 'production_date',
        end_date: 'end_date',
        weight: 'weight',
      }
      const field = fieldMap[sorter.field]
      console.log('Mapped field:', field, 'from sorter.field:', sorter.field)
      if (field) {
        const newSortInfo: { field: string; order: 'asc' | 'desc' } = { field, order: sorter.order === 'ascend' ? 'asc' : 'desc' }
        setSortInfo(newSortInfo)
        setPage(1)
        // Directly call loadRecords with new sort info
        setLoading(true)
        const params: any = {
          page: 1,
          page_size: pageSize,
          product_id: productId,
          sort_by: newSortInfo.field,
          sort_order: newSortInfo.order,
        }
        if (searchText) params.batch_no = searchText
        if (dateRange?.[0]) params.start_date = dateRange[0].format('YYYY-MM-DD')
        if (dateRange?.[1]) params.end_date = dateRange[1].format('YYYY-MM-DD')
        console.log('Calling API with params:', params)
        getProductOutputs(params).then((response) => {
          console.log('API response:', response)
          if (response.code === 200) {
            setRecords(response.data || [])
            setTotal(response.meta?.total || 0)
          }
          setLoading(false)
        }).catch((error) => {
          console.error('API error:', error)
          message.error('加载数据失败')
          setLoading(false)
        })
      }
    } else {
      setSortInfo(null)
      setPage(1)
      // Reload without sorting
      setLoading(true)
      const params: any = {
        page: 1,
        page_size: pageSize,
        product_id: productId,
      }
      if (searchText) params.batch_no = searchText
      if (dateRange?.[0]) params.start_date = dateRange[0].format('YYYY-MM-DD')
      if (dateRange?.[1]) params.end_date = dateRange[1].format('YYYY-MM-DD')
      getProductOutputs(params).then((response) => {
        if (response.code === 200) {
          setRecords(response.data || [])
          setTotal(response.meta?.total || 0)
        }
        setLoading(false)
      }).catch(() => {
        message.error('加载数据失败')
        setLoading(false)
      })
    }
  }

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => setSelectedRowKeys(keys),
  }

  return (
    <div className="p-6">
      <Breadcrumb className="mb-4" items={[
        { title: <Link href="/production/product-output"><HomeOutlined /><span style={{ marginLeft: 4 }}>产品管理</span></Link> },
        { title: <Link href={`/production/product-output/${encodeURIComponent(workshop)}`}>{workshop}</Link> },
        { title: product?.name },
      ]} />

      <div className="mb-6">
        <Title level={4}>{product?.name} - 产量记录</Title>
        <Text type="secondary">{workshop}</Text>
      </div>

      <Row gutter={16} className="mb-6">
        <Col span={8}>
          <Card>
            <Statistic title="今日产量" value={summary.daily} suffix="kg" />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="本月产量" value={summary.monthly} suffix="kg" />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="本年产量" value={summary.yearly} suffix="kg" />
          </Card>
        </Col>
      </Row>

      <Card className="mb-4">
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space wrap>
              <Input
                placeholder="搜索批号"
                prefix={<SearchOutlined />}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                onPressEnter={handleSearch}
                style={{ width: 200 }}
              />
              <DatePicker.RangePicker
                value={dateRange}
                onChange={(dates) => setDateRange(dates as [dayjs.Dayjs | null, dayjs.Dayjs | null] | null)}
              />
              <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
                查询
              </Button>
            </Space>
          </Col>
          <Col>
            <Space>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
                新建
              </Button>
              <Button icon={<UploadOutlined />} onClick={() => setImportModalVisible(true)}>
                导入
              </Button>
              <Dropdown
                menu={{
                  items: [
                    {
                      key: 'preview_push',
                      label: '预览推送',
                      onClick: handlePreviewPush,
                    },
                    {
                      key: 'push',
                      label: '仅推送（平台 → 飞书）',
                      onClick: handlePushToFeishu,
                    },
                    {
                      type: 'divider',
                    },
                    {
                      key: 'preview_pull',
                      label: '预览拉取',
                      onClick: handlePreviewPull,
                    },
                    {
                      key: 'pull',
                      label: '仅拉取（飞书 → 平台）',
                      onClick: handlePullFromFeishu,
                    },
                    {
                      type: 'divider',
                    },
                    {
                      key: 'undo',
                      label: '撤销上次同步',
                      onClick: handleUndoLastSync,
                      danger: true,
                    },
                  ],
                }}
              >
                <Button icon={<CloudSyncOutlined />} loading={syncing}>
                  飞书同步
                </Button>
              </Dropdown>
              <Button icon={<DownloadOutlined />} onClick={handleExport}>
                导出
              </Button>
              <Button 
                icon={<UndoOutlined />} 
                onClick={handleUndoImport}
                disabled={!lastBatchId}
              >
                撤销导入
              </Button>
              <ProductSyncConfig productId={productId} onSynced={loadRecords} />
              {selectedRowKeys.length > 0 && (
                <Button danger icon={<DeleteOutlined />} onClick={handleBatchDelete}>
                  批量删除 ({selectedRowKeys.length})
                </Button>
              )}
            </Space>
          </Col>
        </Row>
      </Card>

      {lastBatchId && (
        <Alert
          message={
            <div className="flex items-center justify-between">
              <div>
                <CheckCircleOutlined className="text-green-500 mr-2" />
                <span className="font-medium">导入成功</span>
                <span className="ml-4 text-gray-600">批次 ID: {lastBatchId}</span>
              </div>
              <Space>
                <Button 
                  size="small" 
                  danger 
                  icon={<UndoOutlined />}
                  onClick={handleUndoImport}
                >
                  撤销本次导入
                </Button>
                <Button 
                  size="small" 
                  type="text" 
                  onClick={() => setLastBatchId(null)}
                >
                  关闭
                </Button>
              </Space>
            </div>
          }
          type="success"
          closable
          onClose={() => setLastBatchId(null)}
          className="mb-4"
        />
      )}

      <Card>
        <Table
          rowSelection={rowSelection}
          rowKey="id"
          columns={columns}
          dataSource={records}
          onChange={handleTableChange}
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (page, pageSize) => {
              setPage(page)
              setPageSize(pageSize)
            },
          }}
        />
      </Card>

      <Modal
        title={editingRecord ? '编辑产量记录' : '新建产量记录'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        confirmLoading={submitting}
      >
        <Form form={form} layout="vertical" onValuesChange={handleFormValuesChange}>
          <Form.Item
            name="batch_no"
            label="批号"
            rules={[{ required: true, message: '请输入批号' }]}
          >
            <Input placeholder="请输入批号" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="production_date"
                label="生产日期"
                rules={[{ required: true, message: '请选择生产日期' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="end_date" label="结束日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="weight" label="重量">
                <InputNumber min={0} style={{ width: '100%' }} placeholder="请输入重量" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="unit" label="单位">
                <Input placeholder="kg" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={3} placeholder="请输入备注" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="导入产量记录"
        open={importModalVisible}
        onCancel={() => {
          setImportModalVisible(false)
          setPreviewData(null)
        }}
        footer={
          previewData ? (
            <div className="flex justify-between">
              <Button onClick={() => setPreviewData(null)}>重新选择文件</Button>
              <div>
                <Button onClick={handleConfirmImport} type="primary" loading={importing}>
                  确认导入 {previewData.new_records} 条
                </Button>
              </div>
            </div>
          ) : null
        }
      >
        <div className="space-y-4">
          <div className="p-4 bg-gray-50 rounded">
            <Text strong>支持格式：CSV 或 XLSX</Text>
            <div className="mt-2 text-xs">
              <Text strong>列顺序：</Text>车间, 产品名称, 批号, 生产日期, 结束日期, 重量, 单位, 备注
            </div>
            <Text type="secondary" className="text-xs block mt-1">
              示例：{workshop}, {product?.name}, AM20260601, 2026-06-01, 2026-06-02, 150.5, kg, 第一批
            </Text>
          </div>
          <Upload
            accept=".csv,.xlsx"
            showUploadList={false}
            beforeUpload={handleImport}
          >
            <Button icon={<FileExcelOutlined />} block>
              选择文件导入（CSV 或 XLSX）
            </Button>
          </Upload>
          {previewData && (
            <div className="border rounded p-4">
              <div className="flex justify-between items-center mb-3">
                <Text strong>预览结果</Text>
                <Space>
                  <Tag color="green">可导入 {previewData.new_records} 条</Tag>
                  {previewData.duplicate_records > 0 && (
                    <Tag color="orange">重复 {previewData.duplicate_records} 条</Tag>
                  )}
                  {previewData.not_found_product > 0 && (
                    <Tag color="red">未匹配产品 {previewData.not_found_product} 条</Tag>
                  )}
                </Space>
              </div>
              <Table
                size="small"
                dataSource={previewData.records}
                rowKey="row_num"
                pagination={false}
                scroll={{ y: 350 }}
                rowClassName={(record: any) => {
                  if (record.is_duplicate) return 'bg-orange-50';
                  if (!record.product_found) return 'bg-red-50';
                  return '';
                }}
                columns={[
                  { 
                    title: '状态', 
                    width: 80, 
                    align: 'center',
                    render: (_: any, r: any) => {
                      if (r.is_duplicate) return <Tag color="orange">⚠️ 重复</Tag>;
                      if (!r.product_found) return <Tag color="red">❌ 未匹配</Tag>;
                      return <Tag color="green">✅ 可导入</Tag>;
                    }
                  },
                  { title: '行号', dataIndex: 'row_num', width: 60, align: 'center' },
                  { title: '车间', dataIndex: 'workshop', width: 90 },
                  { title: '产品名称', dataIndex: 'product_name', width: 140, ellipsis: true },
                  { title: '批号', dataIndex: 'batch_no', width: 160, ellipsis: true },
                  { title: '生产日期', dataIndex: 'production_date', width: 110 },
                  { title: '重量', dataIndex: 'weight', width: 90, render: (val: number, r: any) => `${val} ${r.unit || 'kg'}` },
                  { 
                    title: '产品匹配', 
                    width: 90, 
                    align: 'center',
                    render: (_: any, r: any) => r.product_found ? (
                      <span className="text-green-600 font-bold">✓</span>
                    ) : (
                      <span className="text-red-600 font-bold">✗</span>
                    )
                  },
                ]}
              />
              {previewData.invalid_details && previewData.invalid_details.length > 0 && (
                <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded">
                  <Text strong type="danger">无效记录 ({previewData.invalid_details.length} 条):</Text>
                  <ul className="mt-2 text-sm text-red-600 list-disc list-inside max-h-32 overflow-y-auto">
                    {previewData.invalid_details.map((item: any, idx: number) => (
                      <li key={idx}>第 {item.row} 行: {item.error}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </Modal>

      {/* 从飞书导入弹窗 */}
      <Modal
        title="从飞书多维表格导入"
        open={bitableModalVisible}
        onCancel={() => {
          setBitableModalVisible(false)
          setBitableUrl('')
        }}
        onOk={async () => {
          await handleImportFromBitable()
        }}
        confirmLoading={bitableImporting}
        okText="导入"
        cancelText="取消"
      >
        <div className="space-y-4">
          <div className="p-4 bg-blue-50 rounded">
            <Text strong>使用说明：</Text>
            <ul className="mt-2 text-sm text-gray-600 list-disc list-inside">
              <li>打开飞书多维表格，复制浏览器地址栏的链接</li>
              <li>链接格式：https://xxx.feishu.cn/base/xxxxx?table=yyyyy</li>
              <li>也可以直接输入 app_token 和 table_id，用空格或逗号分隔</li>
            </ul>
          </div>
          <Input
            placeholder="请粘贴飞书多维表格链接，或输入 app_token 和 table_id"
            value={bitableUrl}
            onChange={(e) => setBitableUrl(e.target.value)}
            allowClear
          />
        </div>
      </Modal>
    </div>
  )
}
