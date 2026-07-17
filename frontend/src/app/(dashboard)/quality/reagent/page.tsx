'use client'

import { useState, useCallback, useEffect } from 'react'
import {
  Table,
  Button,
  Space,
  Input,
  Select,
  Tag,
  Drawer,
  Modal,
  Form,
  InputNumber,
  message,
  Popconfirm,
  Card,
  Image,
  Upload,
  Divider,
  Row,
  Col,
  Empty,
  Spin,
  Segmented,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { UploadFile, RcFile } from 'antd/es/upload'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  RobotOutlined,
  PictureOutlined,
  DownloadOutlined,
  EyeOutlined,
  AppstoreOutlined,
  TableOutlined,
  SearchOutlined,
  ReloadOutlined,
  ExperimentOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import {
  Reagent,
  CreateReagentRequest,
  UpdateReagentRequest,
  REAGENT_STATUS_OPTIONS,
  REAGENT_CATEGORY_OPTIONS,
  UNIT_OPTIONS,
} from '@/types/reagent-quality'
import {
  getReagentList,
  getReagentDetail,
  createReagent,
  updateReagent,
  deleteReagent,
  recognizeReagentLabel,
  getNextIncomingLotNo,
  exportReagentsExcel,
} from '@/actions/quality-reagent'
import './reagent-page-style.css'

const { Dragger } = Upload

// 试剂名称到编号的映射（保持不变）
const REAGENT_NO_MAP: Record<string, string> = {
  '枸橼酸铋钾': 'A 001',
  '枸橼酸铋（柠檬酸铋）': 'A 002',
  '枸橼酸': 'A 003',
  '氢氧化钾': 'A 005',
  '纯化水': 'A 006',
  '枸橼酸铋钾标签': 'A 007',
  '药用低密度聚乙烯袋': 'A 008',
  '液体无水氨': 'A 009',
  '药用复合袋': 'A 010',
  '纸板包装桶': 'A 011',
  '产品内标签': 'A 012',
  '艾普拉唑': 'B 001',
  '艾普拉唑钠': 'C 001',
  '艾普拉唑中间体APLA': 'B 002',
  '艾普拉唑中间体APLB': 'B 003',
  '艾普拉唑中间体APLC': 'B 004',
  '艾普拉唑中间体APLD': 'B 005',
  '艾普拉唑中间体APLE': 'B 006',
  '4-硝基邻苯二胺': 'B 007',
  '2-氯甲基-3-甲基-4-甲氧基吡啶盐酸盐': 'B 008',
  '2,5-二甲氧基四氢呋喃': 'B 009',
  '氢氧化钾Ⅰ': 'B 010',
  '二硫化碳': 'B 011',
  '冰醋酸': 'B 012',
  '六水合三氯化铁': 'B 013',
  '工业水合肼（80%）': 'B 014',
  '无水醋酸钠': 'B 015',
  '间氯过氧苯甲酸': 'B 016',
  '无水硫酸镁': 'B 017',
  '氢氧化钠': 'B 018',
  '碳酸氢钠': 'B 019',
  '无水亚硫酸钠': 'B 020',
  '三乙胺': 'B 021',
  '无水乙醇': 'B 022',
  '甲醇': 'B 023',
  '二氯甲烷': 'B 024',
  '乙酸乙酯': 'B 025',
  '注射用水': 'B 026',
  '活性炭': 'B 027',
  '硅胶': 'B 028',
  '药用铝瓶': 'B 029',
  '包装泡沫': 'B 030',
  '中性纸箱': 'B 031',
  '低密度聚乙烯袋（黑色）': 'B 032',
  '药用溴化丁基橡胶密封圈': 'B 033',
  '中间产品标签': 'B 034',
  '艾普拉唑标签': 'B 035',
  '纸板包装桶（大）': 'B 036',
  '马来酸氟伏沙明': 'D 001',
  '马来酸氟伏沙粗品': 'D 002',
  '5-甲氧基-1-[4-（三氟甲基）苯基]-1-戊酮（氟伏沙明酮）': 'D 003',
  '马来酸': 'D 004',
  '2-氯乙胺盐酸盐': 'D 005',
  '盐酸羟胺': 'D 006',
  '药用乙醇': 'D 007',
  '乙腈': 'D 008',
  '马来酸氟伏沙明标签': 'D 010',
  '药用低密度聚乙烯袋Ⅰ': 'D 011',
}

// 状态颜色映射
const STATUS_COLORS: Record<string, string> = {
  available: 'green',
  low_stock: 'orange',
  expired: 'red',
  quarantine: 'blue',
  scrap: 'gray',
}

// 状态图标映射
const STATUS_ICONS: Record<string, React.ReactNode> = {
  available: <CheckCircleOutlined style={{ color: '#10b981' }} />,
  low_stock: <WarningOutlined style={{ color: '#f59e0b' }} />,
  expired: <ClockCircleOutlined style={{ color: '#ef4444' }} />,
  quarantine: <ExperimentOutlined style={{ color: '#3b82f6' }} />,
  scrap: <DeleteOutlined style={{ color: '#6b7280' }} />,
}

// 根据试剂名称查找编号（支持模糊匹配）
function findReagentNo(name: string): string | undefined {
  if (!name) return undefined
  if (REAGENT_NO_MAP[name]) return REAGENT_NO_MAP[name]
  const normalizedName = name.replace(/\s+/g, '')
  for (const key in REAGENT_NO_MAP) {
    if (key.replace(/\s+/g, '') === normalizedName) return REAGENT_NO_MAP[key]
  }
  const noParens = name.replace(/\([^)]*\)/g, '').replace(/\s+/g, '').trim()
  for (const key in REAGENT_NO_MAP) {
    const keyNoParens = key.replace(/\([^)]*\)/g, '').replace(/\s+/g, '').trim()
    if (keyNoParens === noParens) return REAGENT_NO_MAP[key]
  }
  for (const key in REAGENT_NO_MAP) {
    if (name.includes(key) || key.includes(name)) return REAGENT_NO_MAP[key]
  }
  const keywords = name.replace(/[（），。,\s\/\(\)]/g, '').trim()
  if (keywords.length >= 2) {
    for (const key in REAGENT_NO_MAP) {
      const keyClean = key.replace(/[（），。,\s\/\(\)]/g, '')
      if (keyClean.includes(keywords) || keywords.includes(keyClean)) return REAGENT_NO_MAP[key]
    }
  }
  return undefined
}

const initialFilters = {
  keyword: '',
  category: undefined as string | undefined,
  status: undefined as string | undefined,
}

export default function QualityReagentPage() {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<Reagent[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [filters, setFilters] = useState(initialFilters)
  const [viewMode, setViewMode] = useState<'card' | 'table'>('table')
  const [isMobile, setIsMobile] = useState(false)

  const [createForm] = Form.useForm()
  const [editForm] = Form.useForm()

  const [createDrawerVisible, setCreateDrawerVisible] = useState(false)
  const [editDrawerVisible, setEditDrawerVisible] = useState(false)
  const [viewDrawerVisible, setViewDrawerVisible] = useState(false)
  const [editRecord, setEditRecord] = useState<Reagent | null>(null)
  const [viewRecord, setViewRecord] = useState<Reagent | null>(null)

  const [createFileList, setCreateFileList] = useState<UploadFile[]>([])
  const [editFileList, setEditFileList] = useState<UploadFile[]>([])
  const [uploadedUrls, setUploadedUrls] = useState<string[]>([])

  const [aiLoading, setAiLoading] = useState(false)
  const [submitLoading, setSubmitLoading] = useState(false)

  // 检测移动端
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)')
    const update = () => {
      setIsMobile(mq.matches)
      setViewMode(mq.matches ? 'card' : 'table')
    }
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const response = await getReagentList({
        keyword: filters.keyword || undefined,
        category: filters.category,
        status: filters.status,
        page,
        page_size: pageSize,
      })
      if (response.code === 200) {
        setData(response.data.items || [])
        setTotal(response.data.total || 0)
      } else {
        message.error(response.message || '加载失败')
      }
    } catch (error) {
      message.error('加载数据失败')
    } finally {
      setLoading(false)
    }
  }, [filters, page, pageSize])

  useEffect(() => {
    loadData()
  }, [loadData])

  // 统计数据
  const stats = {
    total,
    available: data.filter(i => i.status === 'available').length,
    lowStock: data.filter(i => i.status === 'low_stock').length,
    expired: data.filter(i => i.status === 'expired').length,
  }

  const handleSearch = () => {
    setPage(1)
    loadData()
  }

  const handleReset = () => {
    setFilters(initialFilters)
    setPage(1)
    loadData()
  }

  const handleExport = async () => {
    try {
      message.loading('正在导出...')
      await exportReagentsExcel({
        keyword: filters.keyword || undefined,
        category: filters.category,
        status: filters.status,
      })
      message.success('导出成功')
    } catch (error) {
      message.error('导出失败')
    }
  }

  const handleCreate = async () => {
    createForm.resetFields()
    let incomingLotNo = ''
    try {
      const response = await getNextIncomingLotNo()
      if (response.code === 200 && response.data) {
        incomingLotNo = response.data.incoming_lot_no
      }
    } catch (e) {
      console.error('获取入场批号失败:', e)
    }
    createForm.setFieldsValue({
      arrival_date: dayjs(),
      category: '/',
      unit: 'g',
      incoming_lot_no: incomingLotNo,
    })
    setCreateFileList([])
    setUploadedUrls([])
    setCreateDrawerVisible(true)
  }

  const handleEdit = async (record: Reagent) => {
    try {
      const response = await getReagentDetail(record.id)
      if (response.code === 200 && response.data) {
        setEditRecord(response.data)
        editForm.setFieldsValue({
          ...response.data,
          arrival_date: response.data.arrival_date ? dayjs(response.data.arrival_date) : null,
          production_date: response.data.production_date ? dayjs(response.data.production_date) : null,
          expiration_date: response.data.expiration_date ? dayjs(response.data.expiration_date) : null,
        })
        const existingFiles = (response.data.reagent_label_urls || []).map((url, index) => ({
          uid: String(-index - 1),
          name: `image-${index}`,
          status: 'done' as const,
          url: url,
        }))
        setEditFileList(existingFiles)
        setUploadedUrls(response.data.reagent_label_urls || [])
        setEditDrawerVisible(true)
      } else {
        message.error(response.message || '获取数据失败')
      }
    } catch (error) {
      message.error('获取数据失败')
    }
  }

  const handleView = async (record: Reagent) => {
    try {
      const response = await getReagentDetail(record.id)
      if (response.code === 200 && response.data) {
        setViewRecord(response.data)
        setViewDrawerVisible(true)
      } else {
        message.error(response.message || '获取数据失败')
      }
    } catch (error) {
      message.error('获取数据失败')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      const response = await deleteReagent(id)
      if (response.code === 200) {
        message.success('删除成功')
        loadData()
      } else {
        message.error(response.message || '删除失败')
      }
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleAiRecognize = async (form: 'create' | 'edit') => {
    const fileList = form === 'create' ? createFileList : editFileList
    const files = fileList.filter((f) => f.originFileObj).map((f) => f.originFileObj as RcFile)
    if (files.length === 0) {
      message.warning('请先上传至少一张试剂标签图片')
      return
    }
    setAiLoading(true)
    try {
      const response = await recognizeReagentLabel(files)
      if (response.code === 200 && response.data) {
        const formInstance = form === 'create' ? createForm : editForm
        const data = response.data
        if (data.reagent_name) {
          formInstance.setFieldValue('reagent_name', data.reagent_name)
          const reagentNo = findReagentNo(data.reagent_name)
          if (reagentNo) formInstance.setFieldValue('reagent_no', reagentNo)
        }
        if (data.lot_no) formInstance.setFieldValue('lot_no', data.lot_no)
        if (data.manufacturer) formInstance.setFieldValue('manufacturer', data.manufacturer)
        if (data.content) formInstance.setFieldValue('content', data.content)
        if (data.production_date) {
          formInstance.setFieldValue('production_date', dayjs(data.production_date))
          if (data.expiration_date) {
            formInstance.setFieldValue('expiration_date', dayjs(data.expiration_date))
          } else {
            formInstance.setFieldValue('expiration_date', dayjs(data.production_date).add(3, 'year'))
          }
        } else if (data.expiration_date) {
          formInstance.setFieldValue('expiration_date', dayjs(data.expiration_date))
        }
        if (data.specification) {
          formInstance.setFieldValue('specification', data.specification)
          const specMatch = data.specification.match(/^(\d+(?:\.\d+)?)\s*(g|kg|ml|l|litre|liter|mg)$/i)
          if (specMatch) {
            const value = parseFloat(specMatch[1])
            const unitLower = specMatch[2].toLowerCase()
            formInstance.setFieldValue('quantity', value)
            const unitMap: Record<string, string> = {
              'g': 'g', 'kg': 'kg', 'mg': 'mg',
              'ml': 'ml', 'l': 'L', 'litre': 'L', 'liter': 'L'
            }
            formInstance.setFieldValue('unit', unitMap[unitLower] || unitLower.toUpperCase())
          }
        }
        message.success(`AI识别完成，置信度: ${(data.confidence * 100).toFixed(0)}%`)
      } else {
        message.error(response.message || 'AI识别失败')
      }
    } catch (error) {
      message.error('AI识别失败，请重试')
    } finally {
      setAiLoading(false)
    }
  }

  const handleCreateSubmit = async () => {
    try {
      const values = await createForm.validateFields()
      const submitData: CreateReagentRequest = {
        reagent_label_urls: uploadedUrls,
        reagent_name: values.reagent_name,
        arrival_date: values.arrival_date.format('YYYY-MM-DD'),
        production_date: values.production_date?.format('YYYY-MM-DD'),
        lot_no: values.lot_no,
        incoming_lot_no: values.incoming_lot_no,
        expiration_date: values.expiration_date.format('YYYY-MM-DD'),
        specification: values.specification,
        category: values.category,
        reagent_no: values.reagent_no,
        content: values.content,
        manufacturer: values.manufacturer,
        unit: values.unit,
      }
      setSubmitLoading(true)
      const response = await createReagent(submitData)
      if (response.code === 200) {
        message.success('创建成功')
        setCreateDrawerVisible(false)
        loadData()
      } else {
        message.error(response.message || '创建失败')
      }
    } catch (error: unknown) {
      if ((error as { errorFields?: unknown }).errorFields) return
      message.error((error as Error).message || '操作失败')
    } finally {
      setSubmitLoading(false)
    }
  }

  const handleEditSubmit = async () => {
    try {
      const values = await editForm.validateFields()
      const submitData: UpdateReagentRequest = {
        reagent_label_urls: uploadedUrls,
        reagent_name: values.reagent_name,
        arrival_date: values.arrival_date?.format('YYYY-MM-DD'),
        production_date: values.production_date?.format('YYYY-MM-DD'),
        lot_no: values.lot_no,
        incoming_lot_no: values.incoming_lot_no,
        expiration_date: values.expiration_date?.format('YYYY-MM-DD'),
        specification: values.specification,
        category: values.category,
        reagent_no: values.reagent_no,
        content: values.content,
        manufacturer: values.manufacturer,
        unit: values.unit,
        status: values.status,
      }
      setSubmitLoading(true)
      const response = await updateReagent(editRecord!.id, submitData)
      if (response.code === 200) {
        message.success('更新成功')
        setEditDrawerVisible(false)
        loadData()
      } else {
        message.error(response.message || '更新失败')
      }
    } catch (error: unknown) {
      if ((error as { errorFields?: unknown }).errorFields) return
      message.error((error as Error).message || '操作失败')
    } finally {
      setSubmitLoading(false)
    }
  }

  const handlePreview = async (file: UploadFile) => {
    let url = file.url
    if (!url && file.originFileObj) url = URL.createObjectURL(file.originFileObj)
    if (url) window.open(url, '_blank')
  }

  // 表格列定义
  const columns: ColumnsType<Reagent> = [
    {
      title: '试剂标签',
      dataIndex: 'reagent_label_urls',
      key: 'reagent_label_urls',
      width: 100,
      render: (urls: string[] | null) => {
        if (!urls || urls.length === 0) return <div className="reagent-card-image"><PictureOutlined style={{ fontSize: 24, color: '#9ca3af' }} /></div>
        return (
          <Image.PreviewGroup items={urls}>
            <Image src={urls[0]} width={60} height={60} style={{ objectFit: 'cover', borderRadius: 8 }} placeholder={<PictureOutlined style={{ fontSize: 24 }} />} />
          </Image.PreviewGroup>
        )
      },
    },
    { title: '试剂名称', dataIndex: 'reagent_name', key: 'reagent_name', width: 150, ellipsis: true },
    { title: '批号', dataIndex: 'lot_no', key: 'lot_no', width: 120 },
    { title: '入场批号', dataIndex: 'incoming_lot_no', key: 'incoming_lot_no', width: 120 },
    { title: '有效期', dataIndex: 'expiration_date', key: 'expiration_date', width: 110, render: (v) => v ? dayjs(v).format('YYYY-MM-DD') : '-' },
    { title: '规格', dataIndex: 'specification', key: 'specification', width: 100 },
    { title: '分类', dataIndex: 'category', key: 'category', width: 80, render: (v) => REAGENT_CATEGORY_OPTIONS.find(o => o.value === v)?.label || v },
    { title: '生产厂家', dataIndex: 'manufacturer', key: 'manufacturer', width: 150, ellipsis: true },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 90,
      render: (v) => <Tag color={STATUS_COLORS[v] || 'default'}>{REAGENT_STATUS_OPTIONS.find(o => o.value === v)?.label || v}</Tag>,
    },
    {
      title: '操作', key: 'action', width: 150, fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleView(record)}>查看</Button>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>编辑</Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)} okText="确定" cancelText="取消">
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // 卡片渲染
  const renderCard = (item: Reagent) => (
    <div key={item.id} className="reagent-card" onClick={() => handleView(item)}>
      <div className="reagent-card-header">
        <div className="reagent-card-image">
          {item.reagent_label_urls && item.reagent_label_urls.length > 0
            ? <Image src={item.reagent_label_urls[0]} width={60} height={60} style={{ objectFit: 'cover', borderRadius: 8 }} preview={false} />
            : <PictureOutlined style={{ fontSize: 24, color: '#9ca3af' }} />
          }
        </div>
        <div className="reagent-card-title-area">
          <div className="reagent-card-name">{item.reagent_name}</div>
          <div className="reagent-card-lot">批号: {item.lot_no} | 入场: {item.incoming_lot_no}</div>
        </div>
        <div className="reagent-card-status">
          <Tag color={STATUS_COLORS[item.status] || 'default'} icon={STATUS_ICONS[item.status]}>
            {REAGENT_STATUS_OPTIONS.find(o => o.value === item.status)?.label || item.status}
          </Tag>
        </div>
      </div>
      <div className="reagent-card-info">
        <div className="reagent-card-info-item">
          <div className="reagent-card-info-label">分类</div>
          <div className="reagent-card-info-value">{REAGENT_CATEGORY_OPTIONS.find(o => o.value === item.category)?.label || item.category || '-'}</div>
        </div>
        <div className="reagent-card-info-item">
          <div className="reagent-card-info-label">规格</div>
          <div className="reagent-card-info-value">{item.specification || '-'}</div>
        </div>
        <div className="reagent-card-info-item">
          <div className="reagent-card-info-label">厂家</div>
          <div className="reagent-card-info-value">{item.manufacturer || '-'}</div>
        </div>
        <div className="reagent-card-info-item">
          <div className="reagent-card-info-label">有效期</div>
          <div className="reagent-card-info-value">{item.expiration_date ? dayjs(item.expiration_date).format('YYYY-MM-DD') : '-'}</div>
        </div>
      </div>
      <div className="reagent-card-footer">
        <div className="reagent-card-date">到货: {item.arrival_date ? dayjs(item.arrival_date).format('YYYY-MM-DD') : '-'}</div>
        <div className="reagent-card-actions">
          <Button size="small" icon={<EditOutlined />} onClick={(e) => { e.stopPropagation(); handleEdit(item); }}>编辑</Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(item.id)} okText="确定" cancelText="取消">
            <Button size="small" danger icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()}>删除</Button>
          </Popconfirm>
        </div>
      </div>
    </div>
  )

  // 表单内容（新建/编辑共用）
  const renderFormContent = (formType: 'create' | 'edit') => {
    const formInstance = formType === 'create' ? createForm : editForm
    const fileList = formType === 'create' ? createFileList : editFileList
    const handleFileChange = formType === 'create' ? handleCreateFileChange : handleEditFileChange

    return (
      <>
        <Divider>试剂标签图片</Divider>
        <div className="upload-area-mobile">
          <Dragger
            fileList={fileList}
            onChange={handleFileChange}
            beforeUpload={() => false}
            multiple
            maxCount={5}
            onPreview={handlePreview}
            listType="picture-card"
          >
            <p className="ant-upload-drag-icon"><PictureOutlined /></p>
            <p className="ant-upload-text">点击或拖拽上传试剂标签图片</p>
            <p className="ant-upload-hint">支持多张，AI将自动识别</p>
          </Dragger>
        </div>
        <Button type="primary" icon={<RobotOutlined />} loading={aiLoading} onClick={() => handleAiRecognize(formType)} disabled={fileList.length === 0} className="ai-btn-mobile">
          AI识别标签
        </Button>

        <Divider>基本信息</Divider>
        <Row gutter={[12, 0]}>
          <Col xs={24} sm={12}>
            <Form.Item name="reagent_name" label="试剂名称" rules={[{ required: true }]}>
              <Input placeholder="请输入试剂名称" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="lot_no" label="批号" rules={[{ required: true }]}>
              <Input placeholder="请输入批号" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={[12, 0]}>
          <Col xs={24} sm={12}>
            <Form.Item name="category" label="分类" rules={[{ required: true }]}>
              <Select placeholder="请选择分类">
                {REAGENT_CATEGORY_OPTIONS.map(o => <Select.Option key={o.value} value={o.value}>{o.label}</Select.Option>)}
              </Select>
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="specification" label="规格">
              <Input placeholder="请输入规格" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={[12, 0]}>
          <Col xs={24} sm={12}>
            <Form.Item name="manufacturer" label="生产厂家">
              <Input placeholder="请输入生产厂家" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="content" label="含量">
              <Input placeholder="如：98%、AR级等" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={[12, 0]}>
          <Col xs={24} sm={8}>
            <Form.Item name="arrival_date" label="到货日期" rules={[{ required: true }]}>
              <Input style={{ width: '100%' }} type="date" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={8}>
            <Form.Item name="production_date" label="生产日期">
              <Input style={{ width: '100%' }} type="date" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={8}>
            <Form.Item name="expiration_date" label="有效期" rules={[{ required: true }]}>
              <Input style={{ width: '100%' }} type="date" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={[12, 0]}>
          <Col xs={24} sm={12}>
            <Form.Item name="reagent_no" label="编号">
              <Input placeholder="试剂编号" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="incoming_lot_no" label="入场批号">
              <Input placeholder="入场批号" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={[12, 0]}>
          <Col xs={24} sm={12}>
            <Form.Item name="unit" label="单位" rules={[{ required: true }]}>
              <Select placeholder="请选择单位">
                {UNIT_OPTIONS.map(o => <Select.Option key={o.value} value={o.value}>{o.label}</Select.Option>)}
              </Select>
            </Form.Item>
          </Col>
          {formType === 'edit' && (
            <Col xs={24} sm={12}>
              <Form.Item name="status" label="状态">
                <Select placeholder="请选择状态">
                  {REAGENT_STATUS_OPTIONS.map(o => <Select.Option key={o.value} value={o.value}>{o.label}</Select.Option>)}
                </Select>
              </Form.Item>
            </Col>
          )}
        </Row>
      </>
    )
  }

  const handleCreateFileChange = ({ fileList: newFileList }: { fileList: UploadFile[] }) => setCreateFileList(newFileList)
  const handleEditFileChange = ({ fileList: newFileList }: { fileList: UploadFile[] }) => setEditFileList(newFileList)

  return (
    <div className="reagent-page">
      {/* 工具栏 */}
      <div className="reagent-toolbar">
        <div className="reagent-search-area">
          <Input placeholder="关键词搜索" prefix={<SearchOutlined />} value={filters.keyword} onChange={(e) => setFilters({ ...filters, keyword: e.target.value })} allowClear onPressEnter={handleSearch} />
          <Select placeholder="分类" value={filters.category} onChange={(v) => setFilters({ ...filters, category: v })} allowClear style={{ width: isMobile ? '100%' : 120 }}>
            {REAGENT_CATEGORY_OPTIONS.map(o => <Select.Option key={o.value} value={o.value}>{o.label}</Select.Option>)}
          </Select>
          <Select placeholder="状态" value={filters.status} onChange={(v) => setFilters({ ...filters, status: v })} allowClear style={{ width: isMobile ? '100%' : 120 }}>
            {REAGENT_STATUS_OPTIONS.map(o => <Select.Option key={o.value} value={o.value}>{o.label}</Select.Option>)}
          </Select>
        </div>
        <div className="reagent-action-area">
          {!isMobile && (
            <Segmented
              value={viewMode}
              onChange={(v) => setViewMode(v as 'card' | 'table')}
              options={[
                { value: 'table', icon: <TableOutlined />, label: '表格' },
                { value: 'card', icon: <AppstoreOutlined />, label: '卡片' },
              ]}
            />
          )}
          <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>刷新</Button>
          <Button icon={<DownloadOutlined />} onClick={handleExport}>导出</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>新建试剂</Button>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="reagent-stats">
        <div className="stat-card stat-card-blue">
          <ExperimentOutlined className="stat-icon" />
          <div className="stat-content">
            <div className="stat-num">{stats.total}</div>
            <div className="stat-label">试剂总数</div>
          </div>
        </div>
        <div className="stat-card stat-card-green">
          <CheckCircleOutlined className="stat-icon" />
          <div className="stat-content">
            <div className="stat-num">{stats.available}</div>
            <div className="stat-label">可用</div>
          </div>
        </div>
        <div className="stat-card stat-card-orange">
          <WarningOutlined className="stat-icon" />
          <div className="stat-content">
            <div className="stat-num">{stats.lowStock}</div>
            <div className="stat-label">库存不足</div>
          </div>
        </div>
        <div className="stat-card stat-card-red">
          <ClockCircleOutlined className="stat-icon" />
          <div className="stat-content">
            <div className="stat-num">{stats.expired}</div>
            <div className="stat-label">已过期</div>
          </div>
        </div>
      </div>

      {/* 内容区 */}
      <Spin spinning={loading}>
        {viewMode === 'table' ? (
          <Card style={{ borderRadius: 12, border: '1px solid #e5e7eb' }}>
            <Table
              columns={columns}
              dataSource={data}
              rowKey="id"
              loading={loading}
              scroll={{ x: 1400 }}
              pagination={{
                current: page, pageSize, total,
                showSizeChanger: !isMobile,
                showQuickJumper: !isMobile,
                showTotal: (t) => `共 ${t} 条`,
                onChange: (p, ps) => { setPage(p); setPageSize(ps) },
                simple: isMobile,
              }}
            />
          </Card>
        ) : (
          <>
            <div className="reagent-card-grid">
              {data.length > 0 ? data.map(renderCard) : (
                <div className="empty-state"><Empty description="暂无试剂数据" /></div>
              )}
            </div>
            <div className="pagination-mobile">
              <span style={{ color: '#6b7280', fontSize: 13 }}>共 {total} 条</span>
              <Space>
                <Button disabled={page === 1} onClick={() => setPage(page - 1)}>上一页</Button>
                <span style={{ color: '#1f2937', fontWeight: 500 }}>{page}</span>
                <Button disabled={page * pageSize >= total} onClick={() => setPage(page + 1)}>下一页</Button>
              </Space>
            </div>
          </>
        )}
      </Spin>

      {/* 新建 Drawer */}
      <Drawer
        title="新建试剂/标准品"
        open={createDrawerVisible}
        onClose={() => setCreateDrawerVisible(false)}
        width={isMobile ? '100%' : 600}
        className="form-drawer"
        styles={{ body: { paddingBottom: 80 } }}
      >
        <Form form={createForm} layout="vertical">{renderFormContent('create')}</Form>
        <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: 16, background: '#fff', borderTop: '1px solid #e5e7eb' }}>
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={() => setCreateDrawerVisible(false)}>取消</Button>
            <Button type="primary" onClick={handleCreateSubmit} loading={submitLoading}>创建</Button>
          </Space>
        </div>
      </Drawer>

      {/* 编辑 Drawer */}
      <Drawer
        title="编辑试剂/标准品"
        open={editDrawerVisible}
        onClose={() => setEditDrawerVisible(false)}
        width={isMobile ? '100%' : 600}
        className="form-drawer"
        styles={{ body: { paddingBottom: 80 } }}
      >
        <Form form={editForm} layout="vertical">{renderFormContent('edit')}</Form>
        <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: 16, background: '#fff', borderTop: '1px solid #e5e7eb' }}>
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={() => setEditDrawerVisible(false)}>取消</Button>
            <Button type="primary" onClick={handleEditSubmit} loading={submitLoading}>保存</Button>
          </Space>
        </div>
      </Drawer>

      {/* 查看 Drawer */}
      <Drawer
        title="试剂/标准品详情"
        open={viewDrawerVisible}
        onClose={() => setViewDrawerVisible(false)}
        width={isMobile ? '100%' : 600}
        className="reagent-drawer"
      >
        {viewRecord && (
          <>
            <div className="reagent-drawer-header">
              <div className="reagent-drawer-image">
                {viewRecord.reagent_label_urls && viewRecord.reagent_label_urls.length > 0
                  ? <Image.PreviewGroup items={viewRecord.reagent_label_urls}>
                      <Image src={viewRecord.reagent_label_urls[0]} width={100} height={100} style={{ objectFit: 'cover', borderRadius: 12 }} />
                    </Image.PreviewGroup>
                  : <PictureOutlined style={{ fontSize: 40, color: '#9ca3af' }} />
                }
              </div>
              <div className="reagent-drawer-title-area">
                <div className="reagent-drawer-name">{viewRecord.reagent_name}</div>
                <Space>
                  <Tag color={STATUS_COLORS[viewRecord.status]} icon={STATUS_ICONS[viewRecord.status]}>
                    {REAGENT_STATUS_OPTIONS.find(o => o.value === viewRecord.status)?.label}
                  </Tag>
                  <span style={{ color: '#6b7280', fontSize: 13 }}>批号: {viewRecord.lot_no}</span>
                </Space>
              </div>
            </div>
            <div className="reagent-drawer-info-grid">
              <div className="reagent-drawer-info-item">
                <div className="reagent-drawer-info-label">入场批号</div>
                <div className="reagent-drawer-info-value">{viewRecord.incoming_lot_no || '-'}</div>
              </div>
              <div className="reagent-drawer-info-item">
                <div className="reagent-drawer-info-label">分类</div>
                <div className="reagent-drawer-info-value">{REAGENT_CATEGORY_OPTIONS.find(o => o.value === viewRecord.category)?.label || '-'}</div>
              </div>
              <div className="reagent-drawer-info-item">
                <div className="reagent-drawer-info-label">规格</div>
                <div className="reagent-drawer-info-value">{viewRecord.specification || '-'}</div>
              </div>
              <div className="reagent-drawer-info-item">
                <div className="reagent-drawer-info-label">含量</div>
                <div className="reagent-drawer-info-value">{viewRecord.content || '-'}</div>
              </div>
              <div className="reagent-drawer-info-item">
                <div className="reagent-drawer-info-label">生产厂家</div>
                <div className="reagent-drawer-info-value">{viewRecord.manufacturer || '-'}</div>
              </div>
              <div className="reagent-drawer-info-item">
                <div className="reagent-drawer-info-label">编号</div>
                <div className="reagent-drawer-info-value">{viewRecord.reagent_no || '-'}</div>
              </div>
              <div className="reagent-drawer-info-item">
                <div className="reagent-drawer-info-label">到货日期</div>
                <div className="reagent-drawer-info-value">{viewRecord.arrival_date ? dayjs(viewRecord.arrival_date).format('YYYY-MM-DD') : '-'}</div>
              </div>
              <div className="reagent-drawer-info-item">
                <div className="reagent-drawer-info-label">生产日期</div>
                <div className="reagent-drawer-info-value">{viewRecord.production_date ? dayjs(viewRecord.production_date).format('YYYY-MM-DD') : '-'}</div>
              </div>
              <div className="reagent-drawer-info-item">
                <div className="reagent-drawer-info-label">有效期</div>
                <div className="reagent-drawer-info-value">{viewRecord.expiration_date ? dayjs(viewRecord.expiration_date).format('YYYY-MM-DD') : '-'}</div>
              </div>
              <div className="reagent-drawer-info-item">
                <div className="reagent-drawer-info-label">单位</div>
                <div className="reagent-drawer-info-value">{viewRecord.unit || '-'}</div>
              </div>
              <div className="reagent-drawer-info-item">
                <div className="reagent-drawer-info-label">创建人</div>
                <div className="reagent-drawer-info-value">{viewRecord.created_by || '-'}</div>
              </div>
              <div className="reagent-drawer-info-item">
                <div className="reagent-drawer-info-label">创建时间</div>
                <div className="reagent-drawer-info-value">{viewRecord.created_at ? dayjs(viewRecord.created_at).format('YYYY-MM-DD HH:mm') : '-'}</div>
              </div>
            </div>
            <div style={{ marginTop: 20 }}>
              <Space>
                <Button icon={<EditOutlined />} onClick={() => { setViewDrawerVisible(false); handleEdit(viewRecord); }}>编辑</Button>
                <Popconfirm title="确定删除？" onConfirm={() => { setViewDrawerVisible(false); handleDelete(viewRecord.id); }} okText="确定" cancelText="取消">
                  <Button danger icon={<DeleteOutlined />}>删除</Button>
                </Popconfirm>
              </Space>
            </div>
          </>
        )}
      </Drawer>
    </div>
  )
}