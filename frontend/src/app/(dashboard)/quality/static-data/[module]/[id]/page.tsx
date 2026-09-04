'use client'

import {useState, useEffect} from 'react'
import { useParams } from 'next/navigation'
import {
  Card,
  Form,
  Input,
  Select,
  InputNumber,
  DatePicker,
  Button,
  Space,
  Switch,
  Row,
  Col,
  message,
  Divider,
  Spin,
  Table,
  Popconfirm,
  Upload,
  Typography,
} from 'antd'
import type { UploadFile, UploadProps } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useRouter } from 'next/navigation'
import { ArrowLeftOutlined, SaveOutlined, PlusOutlined, DeleteOutlined, PaperClipOutlined, DownloadOutlined } from '@ant-design/icons'
import {uploadFile as uploadFileApi} from '@/actions/static-data'
import dayjs from 'dayjs'
import {
  STANDARD_STATUS_OPTIONS,
  MATERIAL_TYPE_OPTIONS,
  STANDARD_SOURCE_OPTIONS,
  LIMIT_TYPE_OPTIONS,
  YES_NO_OPTIONS,
} from '@/types/static-data'
import {
  getStorageCondition,
  getUnit,
  getTestItem,
  getEquipment,
  getChromColumn,
  getMedium,
  getReagent,
  getMaterialStandard,
  getProductStandard,
  createStorageCondition,
  createUnit,
  createTestItem,
  createEquipment,
  createChromColumn,
  createMedium,
  createReagent,
  createMaterialStandard,
  createProductStandard,
  updateStorageCondition,
  updateUnit,
  updateTestItem,
  updateEquipment,
  updateChromColumn,
  updateMedium,
  updateReagent,
  updateMaterialStandard,
  updateProductStandard,
  getHplcReference,
  createHplcReference,
  updateHplcReference,
  listTestItem,
} from '@/actions/static-data'

const { TextArea } = Input
const { Text, Link } = Typography
const API_BASE = '/api/v1'
const PREFIX = '/quality/static-data'
const API = `${API_BASE}${PREFIX}`

interface DictItem {
  label: string
  value: string | number
  [key: string]: unknown
}

interface ItemRecord {
  key: number
  id?: number
  test_item_code?: string
  test_item_name?: string
  test_method?: string
  limit_type?: string
  limit_value?: string
  [key: string]: unknown
}



// 附件上传支持的模块
const UPLOAD_MODULES = ['equipment', 'chrom-column', 'medium', 'reagent', 'standard-material', 'material-standard', 'product-standard', 'hplc-reference']

const MODULE_LABELS: Record<string, string> = {
  'storage-condition': '贮存条件',
  'unit': '计量单位',
  'test-item': '检验项目',
  'equipment': '检测设备',
  'chrom-column': '色谱柱',
  'medium': '培养基',
  'reagent': '试剂',
  'standard-material': '标准物质',
  'material-standard': '物料质量标准',
  'product-standard': '产品质量标准',
  'hplc-reference': '液相色谱对照品',
}


interface DictItem {
  label: string
  value: string | number
  cond_name?: string
  cond_code?: string
  [key: string]: unknown
}

interface ItemRecord {
  key: number
  id?: number
  test_item_code?: string
  test_item_name?: string
  test_method?: string
  limit_type?: string
  limit_value?: string
  [key: string]: unknown
}

interface DetailPageProps {
  moduleType: string
  id: string | null
}

function StaticDataDetailPage({ moduleType, id }: DetailPageProps) {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(!!id && id !== 'new')
  const [saving, setSaving] = useState(false)
  const [_record, setRecord] = useState<Record<string, unknown> | null>(null)
  const [items, setItems] = useState<Record<string, unknown>[]>([])
  const [testItemOptions, setTestItemOptions] = useState<{ label: string; value: string }[]>([])
  const [attachFiles, setAttachFiles] = useState<UploadFile[]>([])
  const [uploadLoading, setUploadLoading] = useState(false)
  const router = useRouter()
  const isNew = !id || id === 'new'
  const isStdWithItems = moduleType === 'material-standard' || moduleType === 'product-standard'
  const supportsUpload = UPLOAD_MODULES.includes(moduleType)

  // 字典选项 state
  const [storageCondOptions, setStorageCondOptions] = useState<{ label: string; value: string }[]>([])
  const [equipmentCategoryOptions, setEquipmentCategoryOptions] = useState<{ label: string; value: string }[]>([])
  const [verifyStatusOptions, setVerifyStatusOptions] = useState<{ label: string; value: string }[]>([])
  const [labOptions, setLabOptions] = useState<{ label: string; value: string }[]>([])
  const [eqStatusOptions, setEqStatusOptions] = useState<{ label: string; value: string }[]>([])
  const [mediumTypeOptions, setMediumTypeOptions] = useState<{ label: string; value: string }[]>([])
  const [reagentPurityOptions, setReagentPurityOptions] = useState<{ label: string; value: string }[]>([])
  const [dangerTypeOptions, setDangerTypeOptions] = useState<{ label: string; value: string }[]>([])
  const [stdTypeOptions, setStdTypeOptions] = useState<{ label: string; value: string }[]>([])
  const [unitTypeOptions, setUnitTypeOptions] = useState<{ label: string; value: string }[]>([])
  const [testItemCategoryOptions, setTestItemCategoryOptions] = useState<{ label: string; value: string }[]>([])
  const [chromColumnStatusOptions, setChromColumnStatusOptions] = useState<{ label: string; value: string }[]>([])
  const [unitOptions, setUnitOptions] = useState<{ label: string; value: string }[]>([])
  // 设备管理员选项（待接入人员模块后替换为真实API）
  const [managerOptions, _setManagerOptions] = useState<{ label: string; value: string }[]>([
    { label: '张三', value: '1' },
    { label: '李四', value: '2' },
    { label: '王五', value: '3' },
  ])

  // 加载字典数据
  useEffect(() => {
    const loadDictData = async () => {
      try {
        const [sc, ec, vs, lab, eqs, mt, rp, dt, stt, utt, tic, ccs, uo] = await Promise.all([
          fetch(`${API}/storage-condition/options`).then(r => r.json()),
          fetch(`${API}/dict/equipment-category`).then(r => r.json()),
          fetch(`${API}/dict/verify-status`).then(r => r.json()),
          fetch(`${API}/dict/lab`).then(r => r.json()),
          fetch(`${API}/dict/equipment-status`).then(r => r.json()),
          fetch(`${API}/dict/medium-type`).then(r => r.json()),
          fetch(`${API}/dict/reagent-purity`).then(r => r.json()),
          fetch(`${API}/dict/danger-type`).then(r => r.json()),
          fetch(`${API}/dict/std-type`).then(r => r.json()),
          fetch(`${API}/dict/unit-type`).then(r => r.json()),
          fetch(`${API}/dict/test-item-category`).then(r => r.json()),
          fetch(`${API}/dict/chrom-column-status`).then(r => r.json()),
          fetch(`${API}/unit/options`).then(r => r.json()),
        ])
        if (sc.code === 200 || sc.code === 0) setStorageCondOptions(sc.data.map((x: Record<string, unknown>) => ({ label: x.label || x.cond_name, value: x.value || x.cond_code })))
        if (ec.code === 200 || ec.code === 0) setEquipmentCategoryOptions(ec.data.map((x: Record<string, unknown>) => ({ label: x.label, value: x.value })))
        if (vs.code === 200 || vs.code === 0) setVerifyStatusOptions(vs.data.map((x: Record<string, unknown>) => ({ label: x.label, value: x.value })))
        if (lab.code === 200 || lab.code === 0) setLabOptions(lab.data.map((x: Record<string, unknown>) => ({ label: x.label, value: String(x.value) })))
        if (eqs.code === 200 || eqs.code === 0) setEqStatusOptions(eqs.data.map((x: Record<string, unknown>) => ({ label: x.label, value: x.value })))
        if (mt.code === 200 || mt.code === 0) setMediumTypeOptions(mt.data.map((x: Record<string, unknown>) => ({ label: x.label, value: x.value })))
        if (rp.code === 200 || rp.code === 0) setReagentPurityOptions(rp.data.map((x: Record<string, unknown>) => ({ label: x.label, value: x.value })))
        if (dt.code === 200 || dt.code === 0) setDangerTypeOptions(dt.data.map((x: Record<string, unknown>) => ({ label: x.label, value: x.value })))
        if (stt.code === 200 || stt.code === 0) setStdTypeOptions(stt.data.map((x: Record<string, unknown>) => ({ label: x.label, value: x.value })))
        if (utt.code === 200 || utt.code === 0) setUnitTypeOptions(utt.data.map((x: Record<string, unknown>) => ({ label: x.label, value: x.value })))
        if (tic.code === 200 || tic.code === 0) setTestItemCategoryOptions(tic.data.map((x: Record<string, unknown>) => ({ label: x.label, value: x.value })))
        if (ccs.code === 200 || ccs.code === 0) setChromColumnStatusOptions(ccs.data.map((x: Record<string, unknown>) => ({ label: x.label, value: x.value })))
        if (uo.code === 200 || uo.code === 0) setUnitOptions(uo.data.map((x: Record<string, unknown>) => ({ label: x.label || x.unit_name, value: x.value || x.unit_code })))
      } catch (_e) {
        // ignore errors
      }
    }
    loadDictData()
  }, [moduleType])

  // 加载检验项目下拉选项（用于 items 子表）
  useEffect(() => {
    if (isStdWithItems) {
      listTestItem({ page: 1, page_size: 200 } as Record<string, unknown>)
        .then((res: { data?: DictItem[] }) => {
          const opts = (res.data ?? []).map((t: DictItem) => ({
            label: `${t.item_code} - ${t.item_name}`,
            value: t.item_code,
          }))
          setTestItemOptions(opts)
        })
        .catch(() => {})
    }
  }, [moduleType])

  useEffect(() => {
    if (!isNew) {
      loadRecord()
    }
  }, [id, moduleType, isNew, loadRecord])

  async function loadRecord() {
    if (!id) return
    setLoading(true)
    try {
      let res: Record<string, unknown> | null = null
      switch (moduleType) {
        case 'storage-condition': res = await getStorageCondition(Number(id)); break
        case 'unit': res = await getUnit(Number(id)); break
        case 'test-item': res = await getTestItem(Number(id)); break
        case 'equipment': res = await getEquipment(Number(id)); break
        case 'chrom-column': res = await getChromColumn(Number(id)); break
        case 'medium': res = await getMedium(Number(id)); break
        case 'reagent': res = await getReagent(Number(id)); break
        case 'standard-material': res = await getMaterialStandard(Number(id)); break
        case 'product-standard': res = await getProductStandard(Number(id)); break
        case 'hplc-reference': res = await getHplcReference(Number(id)); break
        default: return
      }
      const data = res.data
      setRecord(data)
      // 加载 items 子表
      if (isStdWithItems && data.items) {
        setItems(((res?.data as Record<string, unknown>)?.items as Array<Record<string, unknown>> ?? []).map((it: Record<string, unknown>, idx: number) => ({ ...it, key: (it.id as number) ?? Date.now() + idx })))
      }
      const dateFields = ['last_cal_date', 'next_cal_date', 'purchase_date', 'use_start_date',
        'expire_date', 'effect_date', 'invalid_date', 'arrival_date', 'produce_date', 'open_date']
      const fmt: Record<string, unknown> = {}
      dateFields.forEach(f => {
        if (data[f] && typeof data[f] === 'string') fmt[f] = dayjs(data[f])
      })
      form.setFieldsValue({ ...data, ...fmt })
      // 初始化附件列表
      if (supportsUpload && data.attach_file) {
        const names = data.attach_file.split(',').filter(Boolean)
        setAttachFiles(names.map((name: string, idx: number) => ({
          uid: String(-idx - 1),
          name,
          status: 'done',
          url: `${API}/download/${encodeURIComponent(name)}`,
        })))
      }
    } catch (e: unknown) {
      message.error((e instanceof Error ? e.message : '加载失败'))
    } finally {
      setLoading(false)
    }
  }

  async function handleSave(values: Record<string, unknown> & { report_date?: { format: (f: string) => string } }) {
    setSaving(true)
    try {
      const processed = { ...values }
      // 强制从 form 读取 attach_file（隐藏字段可能不提交）
      processed.attach_file = form.getFieldValue('attach_file') || values.attach_file || null
      const dateFields = ['last_cal_date', 'next_cal_date', 'purchase_date', 'use_start_date',
        'expire_date', 'effect_date', 'invalid_date', 'arrival_date', 'produce_date', 'open_date']
      dateFields.forEach(f => {
        if (processed[f] && typeof processed[f] === 'object' && processed[f].format) {
          processed[f] = processed[f].format('YYYY-MM-DD')
        }
      })
      processed.create_by = 1
      // 质量标准附带 items
      if (isStdWithItems) {
        processed.items = items.map(it => {
          const { key: _key, ...rest } = it
          return rest
        })
      }

      let fn: Function | null, updateFn: Function | null
      switch (moduleType) {
        case 'storage-condition': fn = createStorageCondition; updateFn = updateStorageCondition; break
        case 'unit': fn = createUnit; updateFn = updateUnit; break
        case 'test-item': fn = createTestItem; updateFn = updateTestItem; break
        case 'equipment': fn = createEquipment; updateFn = updateEquipment; break
        case 'chrom-column': fn = createChromColumn; updateFn = updateChromColumn; break
        case 'medium': fn = createMedium; updateFn = updateMedium; break
        case 'reagent': fn = createReagent; updateFn = updateReagent; break
        case 'standard-material': fn = createMaterialStandard; updateFn = updateMaterialStandard; break
        case 'product-standard': fn = createProductStandard; updateFn = updateProductStandard; break
        case 'hplc-reference': fn = createHplcReference; updateFn = updateHplcReference; break
        default: throw new Error('未知模块')
      }

      if (isNew) {
        await fn(processed)
        message.success('创建成功')
      } else {
        await updateFn(Number(id), processed)
        message.success('保存成功')
      }
      router.push('/quality/static-data')
    } catch (e: unknown) {
      message.error((e instanceof Error ? e.message : '保存失败'))
    } finally {
      setSaving(false)
    }
  }

  // ===== items 子表操作 =====
  function addItem() {
    setItems(prev => [
      ...prev,
      {
        key: Date.now(),
        item_code: '',
        test_method: null,
        limit_type: '上限',
        limit_min: null,
        limit_max: null,
        is_release_item: 0,
        sort_num: prev.length + 1,
      },
    ])
  }

  function removeItem(key: number) {
    setItems(prev => prev.filter(i => i.key !== key))
  }

  // ===== 附件上传处理 =====
  const handleUploadChange = async ({ file, fileList }: { file: UploadFile; fileList: UploadFile[] }) => {
    // 更新本地列表（显示用）
    setAttachFiles(fileList.filter(f => f.status !== 'error'))

    // 只在上传完成时处理
    if (file.status === 'done') {
      const res = file.response as { code?: number; data?: { stored_name?: string }; message?: string }
      if (res && (res.code === 200 || res.code === 0)) {
        const uploaded = res.data
        // 将文件名追加到 attach_file 字段
        const currentVal = form.getFieldValue('attach_file') || ''
        const newVal = currentVal ? `${currentVal},${uploaded.stored_name}` : uploaded.stored_name
        form.setFieldValue('attach_file', newVal)
        message.success(`${file.name} 上传成功`)
      } else {
        message.error((file.response as { message?: string })?.message || '上传失败')
      }
    } else if (file.status === 'error') {
      message.error(`${file.name} 上传失败`)
    }
  }

  const handleRemoveFile = (file: UploadFile) => {
    // 从 attach_file 字段移除
    const currentVal = form.getFieldValue('attach_file') || ''
    const storedName = file.response?.data?.stored_name || file.name
    const newVal = currentVal.split(',').filter((n: string) => n !== storedName).join(',')
    form.setFieldValue('attach_file', newVal)
    return true
  }

  const uploadProps: UploadProps = {
    name: 'file',
    action: `${API}/upload`,
    headers: { 'Authorization': 'Bearer dummy' },
    accept: '.pdf,.jpg,.jpeg,.png,.xlsx,.xls,.doc,.docx',
    maxCount: 5,
    multiple: true,
    onChange: handleUploadChange,
    onRemove: handleRemoveFile,
    customRequest: async (options) => {
      const { file, onSuccess, onError } = options
      setUploadLoading(true)
      try {
        const res = await uploadFileApi(file as File)
        if (res.code === 200 || res.code === 0) {
          onSuccess?.(res)
        } else {
          onError?.(new Error(res.message || `上传失败(code: ${res.code})`))
        }
      } catch (e: unknown) {
        onError?.(e)
      } finally {
        setUploadLoading(false)
      }
    },
  }

  function updateItem(key: number, field: string, value: unknown) {
    setItems(prev => prev.map(i => i.key === key ? { ...i, [field]: value } : i))
  }

  // 物料标准 items 列定义
  const matItemColumns: ColumnsType<ItemRecord> = [
    { title: '序号', width: 50, render: (_: unknown, __: unknown, idx: number) => idx + 1 },
    {
      title: '检验项目*', dataIndex: 'item_code', width: 200,
      render: (v: string, record: ItemRecord) => (
        <Select
          value={v} style={{ width: '100%' }}
          options={testItemOptions} showSearch allowClear
          placeholder="选择检验项目"
          onChange={val => updateItem(record.key, 'item_code', val)}
          filterOption={(input, opt) => (opt?.label ?? '').toLowerCase().includes(input.toLowerCase())}
        />
      ),
    },
    {
      title: '检验方法', dataIndex: 'test_method', width: 160,
      render: (v: string, record: ItemRecord) => (
        <Input value={v} placeholder="检验方法简述"
          onChange={e => updateItem(record.key, 'test_method', e.target.value)} />
      ),
    },
    {
      title: '限度类型*', dataIndex: 'limit_type', width: 100,
      render: (v: string, record: ItemRecord) => (
        <Select value={v} options={LIMIT_TYPE_OPTIONS}
          onChange={val => updateItem(record.key, 'limit_type', val)} />
      ),
    },
    {
      title: '下限', dataIndex: 'limit_min', width: 90,
      render: (v: number, record: ItemRecord) => (
        <InputNumber value={v} style={{ width: '100%' }} placeholder="下限"
          onChange={val => updateItem(record.key, 'limit_min', val)} />
      ),
    },
    {
      title: '上限', dataIndex: 'limit_max', width: 90,
      render: (v: number, record: ItemRecord) => (
        <InputNumber value={v} style={{ width: '100%' }} placeholder="上限"
          onChange={val => updateItem(record.key, 'limit_max', val)} />
      ),
    },
    {
      title: '放行必检', dataIndex: 'is_release_item', width: 90,
      render: (v: number, record: ItemRecord) => (
        <Select value={v} options={YES_NO_OPTIONS}
          onChange={val => updateItem(record.key, 'is_release_item', val)} />
      ),
    },
    {
      title: '操作', width: 70,
      render: (_: unknown, record: ItemRecord) => (
        <Popconfirm title="确定删除？" onConfirm={() => removeItem(record.key)} okText="确定" cancelText="取消">
          <Button type="link" danger size="small" icon={<DeleteOutlined />}>删除</Button>
        </Popconfirm>
      ),
    },
  ]

  // 产品标准 items 列定义（法定限度 + 内控限度）
  const prodItemColumns: ColumnsType<ItemRecord> = [
    { title: '序号', width: 50, render: (_: any, __: any, idx: number) => idx + 1 },
    {
      title: '检验项目*', dataIndex: 'item_code', width: 180,
      render: (v: string, record: ItemRecord) => (
        <Select
          value={v} style={{ width: '100%' }}
          options={testItemOptions} showSearch allowClear
          placeholder="选择检验项目"
          onChange={val => updateItem(record.key, 'item_code', val)}
          filterOption={(input, opt) => (opt?.label ?? '').toLowerCase().includes(input.toLowerCase())}
        />
      ),
    },
    {
      title: '检验方法', dataIndex: 'test_method', width: 130,
      render: (v: string, record: ItemRecord) => (
        <Input value={v} placeholder="检验方法简述"
          onChange={e => updateItem(record.key, 'test_method', e.target.value)} />
      ),
    },
    {
      title: '法定下限', dataIndex: 'legal_limit_min', width: 85,
      render: (v: number, record: ItemRecord) => (
        <InputNumber value={v} style={{ width: '100%' }} placeholder="法定下限"
          onChange={val => updateItem(record.key, 'legal_limit_min', val)} />
      ),
    },
    {
      title: '法定上限', dataIndex: 'legal_limit_max', width: 85,
      render: (v: number, record: ItemRecord) => (
        <InputNumber value={v} style={{ width: '100%' }} placeholder="法定上限"
          onChange={val => updateItem(record.key, 'legal_limit_max', val)} />
      ),
    },
    {
      title: '内控下限', dataIndex: 'inner_limit_min', width: 85,
      render: (v: number, record: ItemRecord) => (
        <InputNumber value={v} style={{ width: '100%' }} placeholder="内控下限"
          onChange={val => updateItem(record.key, 'inner_limit_min', val)} />
      ),
    },
    {
      title: '内控上限', dataIndex: 'inner_limit_max', width: 85,
      render: (v: number, record: ItemRecord) => (
        <InputNumber value={v} style={{ width: '100%' }} placeholder="内控上限"
          onChange={val => updateItem(record.key, 'inner_limit_max', val)} />
      ),
    },
    {
      title: '放行必检', dataIndex: 'is_release_item', width: 90,
      render: (v: number, record: ItemRecord) => (
        <Select value={v} options={YES_NO_OPTIONS}
          onChange={val => updateItem(record.key, 'is_release_item', val)} />
      ),
    },
    {
      title: '操作', width: 70,
      render: (_: unknown, record: ItemRecord) => (
        <Popconfirm title="确定删除？" onConfirm={() => removeItem(record.key)} okText="确定" cancelText="取消">
          <Button type="link" danger size="small" icon={<DeleteOutlined />}>删除</Button>
        </Popconfirm>
      ),
    },
  ]

  // ============ renderFormFields 作为组件内部方法 ============
  const renderFormFields = () => {
    switch (moduleType) {
      case 'storage-condition':
        return (
          <Row gutter={16}>
            <Col span={8}><Form.Item name="cond_code" label="贮存条件编码" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="cond_name" label="贮存条件名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="status" label="状态" initialValue={0}><Select options={[{ label: '启用', value: 0 }, { label: '停用', value: 1 }]} /></Form.Item></Col>
            <Col span={8}><Form.Item name="temp_min" label="温度下限(℃)"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="temp_max" label="温度上限(℃)"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="humidity" label="湿度要求"><Input /></Form.Item></Col>
            <Col span={24}><Form.Item name="remark" label="备注"><TextArea rows={2} /></Form.Item></Col>
          </Row>
        )

      case 'unit':
        return (
          <Row gutter={16}>
            <Col span={8}><Form.Item name="unit_code" label="单位编码" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="unit_name" label="单位名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="unit_type" label="单位类别" rules={[{ required: true }]}><Select options={unitTypeOptions} placeholder="请选择" /></Form.Item></Col>
            <Col span={8}><Form.Item name="base_value" label="换算基准值"><InputNumber style={{ width: '100%' }} precision={6} /></Form.Item></Col>
            <Col span={8}><Form.Item name="status" label="状态" initialValue={0}><Select options={[{ label: '启用', value: 0 }, { label: '停用', value: 1 }]} /></Form.Item></Col>
            <Col span={24}><Form.Item name="remark" label="备注"><TextArea rows={2} /></Form.Item></Col>
          </Row>
        )

      case 'test-item':
        return (
          <Row gutter={16}>
            <Col span={8}><Form.Item name="item_code" label="检验项目编码" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="item_name" label="检验项目名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="item_category" label="检验分类" rules={[{ required: true }]}><Select options={testItemCategoryOptions} placeholder="请选择" /></Form.Item></Col>
            <Col span={8}><Form.Item name="unit_code" label="默认计量单位" rules={[{ required: true }]}><Select options={unitOptions} placeholder="请选择" /></Form.Item></Col>
            <Col span={8}><Form.Item name="sort_num" label="排序号"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="status" label="状态" initialValue={0}><Select options={[{ label: '启用', value: 0 }, { label: '停用', value: 1 }]} /></Form.Item></Col>
            <Col span={24}><Form.Item name="method_desc" label="检验方法简述"><TextArea rows={2} /></Form.Item></Col>
          </Row>
        )

      case 'equipment':
        return (
          <Row gutter={16}>
            <Col span={8}><Form.Item name="eq_code" label="设备编号" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="eq_name" label="仪器名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="model" label="设备型号" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="serial_no" label="出厂序列号" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="manufacturer" label="生产厂家" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="spec" label="设备规格" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="eq_category" label="设备分类" rules={[{ required: true }]}><Select options={equipmentCategoryOptions} placeholder="请选择" /></Form.Item></Col>
            <Col span={8}><Form.Item name="location" label="存放位置" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="lab_id" label="所属实验室" rules={[{ required: true }]}><Select options={labOptions} placeholder="请选择" /></Form.Item></Col>
            <Col span={8}><Form.Item name="cal_cycle" label="校准周期(月)" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="last_cal_date" label="上次校准日期" rules={[{ required: true }]}><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="next_cal_date" label="下次校准日期" rules={[{ required: true }]}><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="verify_status" label="验证状态" rules={[{ required: true }]}><Select options={verifyStatusOptions} placeholder="请选择" /></Form.Item></Col>
            <Col span={8}><Form.Item name="eq_status" label="设备状态" initialValue={0}><Select options={eqStatusOptions} /></Form.Item></Col>
            <Col span={8}><Form.Item name="manager_id" label="设备管理员" rules={[{ required: true }]}><Select options={managerOptions} placeholder="请选择（待人员模块接入）" showSearch allowClear /></Form.Item></Col>
            <Col span={24}><Form.Item name="remark" label="备注"><TextArea rows={2} /></Form.Item></Col>
            {/* 设备管理员附件：SOP文件 / 校准证书 / 验证资料 */}
            <Col span={24}>
              <Divider orientation={"left" as const} style={{ marginTop: 8 }}>设备文件</Divider>
            </Col>
            <Col span={8}><Form.Item name="sop_file" label="SOP文件" help="操作规程PDF"><Input placeholder="附件上传区（待实现）" /></Form.Item></Col>
            <Col span={8}><Form.Item name="cal_cert" label="校准证书" help="最近一次校准证书PDF"><Input placeholder="附件上传区（待实现）" /></Form.Item></Col>
            <Col span={8}><Form.Item name="verify_docs" label="验证资料" help="IQ/OQ/PQ验证文档"><Input placeholder="附件上传区（待实现）" /></Form.Item></Col>
          </Row>
        )

      case 'chrom-column':
        return (
          <Row gutter={16}>
            <Col span={8}><Form.Item name="col_code" label="色谱柱内部编号" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="col_type" label="固定相类型" rules={[{ required: true }]}><Select options={[
              { label: 'C18', value: 'C18' },
              { label: 'C8', value: 'C8' },
              { label: 'NH2', value: 'NH2' },
              { label: 'Silica', value: 'Silica' },
              { label: '其他', value: '其他' },
            ]} placeholder="请选择" /></Form.Item></Col>
            <Col span={8}><Form.Item name="spec" label="规格参数" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="manufacturer" label="厂家" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="serial_no" label="原厂序列号" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="purchase_date" label="采购日期" rules={[{ required: true }]}><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="use_start_date" label="启用日期"><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="max_use_times" label="最大允许使用次数" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="used_times" label="已使用次数" initialValue={0}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="storage_cond_code" label="贮存条件" rules={[{ required: true }]}><Select options={storageCondOptions} placeholder="请选择" /></Form.Item></Col>
            <Col span={8}><Form.Item name="location" label="存放位置" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="col_status" label="状态" initialValue={0}><Select options={chromColumnStatusOptions} /></Form.Item></Col>
            <Col span={24}><Form.Item name="apply_method" label="适用检测方法"><TextArea rows={2} /></Form.Item></Col>
            <Col span={24}><Form.Item name="remark" label="备注"><TextArea rows={2} /></Form.Item></Col>
          </Row>
        )

      case 'medium':
        return (
          <Row gutter={16}>
            <Col span={8}><Form.Item name="medium_code" label="培养基编码" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="medium_name" label="培养基名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="medium_type" label="培养基类型" rules={[{ required: true }]}><Select options={mediumTypeOptions} placeholder="请选择" /></Form.Item></Col>
            <Col span={8}><Form.Item name="manufacturer" label="生产厂家" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="batch_no" label="厂家批号" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="spec" label="包装规格" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="storage_cond_code" label="贮存条件" rules={[{ required: true }]}><Select options={storageCondOptions} placeholder="请选择" /></Form.Item></Col>
            <Col span={8}><Form.Item name="expire_date" label="有效期至" rules={[{ required: true }]}><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="verify_status" label="适用性验证状态" rules={[{ required: true }]}><Select options={verifyStatusOptions} placeholder="请选择" /></Form.Item></Col>
            <Col span={8}><Form.Item name="stock_num" label="当前库存数量" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="unit_code" label="库存单位" rules={[{ required: true }]}><Select options={unitOptions} placeholder="请选择" /></Form.Item></Col>
            <Col span={8}><Form.Item name="min_stock" label="最低安全库存" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="status" label="状态" initialValue={0}><Select options={[{ label: '在用', value: 0 }, { label: '停用', value: 1 }]} /></Form.Item></Col>
            <Col span={24}><Form.Item name="config_method" label="配制方法/灭菌参数" help="详细填写培养基配制方法、灭菌温度、时间等参数">
              <TextArea rows={4} placeholder="如：称取培养基干粉 23.5g，加入纯化水 1000mL，加热溶解，121℃高压灭菌 15min" />
            </Form.Item></Col>
            <Col span={24}><Form.Item name="remark" label="备注"><TextArea rows={2} /></Form.Item></Col>
          </Row>
        )

      case 'reagent':
        return (
          <Row gutter={16}>
            <Col span={8}><Form.Item name="reagent_code" label="试剂编码" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="reagent_name" label="试剂名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="cas_no" label="CAS号" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="purity" label="纯度级别" rules={[{ required: true }]}><Select options={reagentPurityOptions} placeholder="请选择" /></Form.Item></Col>
            <Col span={8}><Form.Item name="manufacturer" label="厂家" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="batch_no" label="试剂批号" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="spec" label="包装规格" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="danger_type" label="危险分类" rules={[{ required: true }]}><Select options={dangerTypeOptions} placeholder="请选择" /></Form.Item></Col>
            <Col span={8}><Form.Item name="storage_cond_code" label="贮存条件" rules={[{ required: true }]}><Select options={storageCondOptions} placeholder="请选择" /></Form.Item></Col>
            <Col span={8}><Form.Item name="expire_date" label="有效期至" rules={[{ required: true }]}><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="stock_num" label="当前库存" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="unit_code" label="库存单位" rules={[{ required: true }]}><Select options={unitOptions} placeholder="请选择" /></Form.Item></Col>
            <Col span={8}><Form.Item name="min_stock" label="最低安全库存" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="store_location" label="存放库位" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="status" label="状态" initialValue={0}><Select options={[{ label: '启用', value: 0 }, { label: '停用', value: 1 }]} /></Form.Item></Col>
            <Col span={24}><Form.Item name="remark" label="备注"><TextArea rows={2} /></Form.Item></Col>
          </Row>
        )

      case 'standard-material':
        return (
          <Row gutter={16}>
            <Col span={8}><Form.Item name="std_code" label="标准品内部编码" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="std_name" label="标准品名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="cas_no" label="CAS号"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="manufacturer" label="厂家" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="batch_no" label="厂家批号" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="cert_no" label="溯源证书编号" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="purity" label="纯度含量" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} precision={6} /></Form.Item></Col>
            <Col span={8}><Form.Item name="init_stock" label="初始入库量" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="remain_stock" label="剩余库存" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="unit_code" label="库存单位编码" rules={[{ required: true }]}><Select options={unitOptions} placeholder="请选择" showSearch /></Form.Item></Col>
            <Col span={8}><Form.Item name="storage_cond_code" label="贮存条件" rules={[{ required: true }]}><Select options={storageCondOptions} placeholder="请选择" /></Form.Item></Col>
            <Col span={8}><Form.Item name="expire_date" label="有效期至" rules={[{ required: true }]}><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="store_location" label="存放位置" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="std_type" label="标准品类型" rules={[{ required: true }]}><Select options={stdTypeOptions} placeholder="请选择" /></Form.Item></Col>
            <Col span={8}><Form.Item name="recal_cycle" label="复标周期(月)"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="min_stock" label="最低安全库存"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="status" label="状态" initialValue={0}>
              <Select options={[
                { label: '在用', value: 0 },
                { label: '封存', value: 1 },
                { label: '报废', value: 2 },
              ]} />
            </Form.Item></Col>
            <Col span={24}><Form.Item name="remark" label="备注"><TextArea rows={2} /></Form.Item></Col>
          </Row>
        )

      case 'material-standard':
        return (
          <Row gutter={16}>
            <Col span={8}><Form.Item name="material_code" label="物料编码" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="material_name" label="物料名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="material_type" label="物料类别" rules={[{ required: true }]}><Select options={MATERIAL_TYPE_OPTIONS} /></Form.Item></Col>
            <Col span={8}><Form.Item name="spec" label="物料规格" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="supplier_id" label="供应商ID"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="standard_source" label="标准来源" rules={[{ required: true }]}><Select options={STANDARD_SOURCE_OPTIONS} /></Form.Item></Col>
            <Col span={8}><Form.Item name="standard_no" label="标准编号" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="version" label="版本号" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="storage_cond_code" label="贮存条件" rules={[{ required: true }]}><Select options={storageCondOptions} placeholder="请选择" /></Form.Item></Col>
            <Col span={8}><Form.Item name="status" label="状态" initialValue={0}><Select options={STANDARD_STATUS_OPTIONS} /></Form.Item></Col>
            <Col span={8}><Form.Item name="draft_user" label="起草人ID" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="audit_user" label="审核人ID"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="approve_user" label="批准人ID"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="effect_date" label="生效日期"><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="invalid_date" label="作废日期"><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={24}><Form.Item name="remark" label="备注"><TextArea rows={2} /></Form.Item></Col>
          </Row>
        )

      case 'product-standard':
        return (
          <Row gutter={16}>
            <Col span={8}><Form.Item name="product_code" label="产品编码" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="product_name" label="产品通用名" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="trade_name" label="商品名"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="spec" label="产品规格" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="dosage_form" label="剂型" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="reg_standard_no" label="注册标准号" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="inner_standard_no" label="内控标准编号" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="version" label="版本号" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="storage_cond_code" label="贮存条件" rules={[{ required: true }]}><Select options={storageCondOptions} placeholder="请选择" /></Form.Item></Col>
            <Col span={8}><Form.Item name="valid_period" label="产品有效期(月)" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="pack_spec" label="包装规格" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="status" label="状态" initialValue={0}><Select options={STANDARD_STATUS_OPTIONS} /></Form.Item></Col>
            <Col span={8}><Form.Item name="draft_user" label="起草人ID" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="audit_user" label="审核人ID"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="approve_user" label="批准人ID"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="effect_date" label="生效日期"><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="invalid_date" label="作废日期"><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={24}><Form.Item name="remark" label="备注"><TextArea rows={2} /></Form.Item></Col>
          </Row>
        )

      case 'hplc-reference':
        return (
          <Row gutter={16}>
            <Col span={8}><Form.Item name="ref_code" label="对照品编号" rules={[{ required: true }]}><Input placeholder="如：REF0001" /></Form.Item></Col>
            <Col span={8}><Form.Item name="ref_name" label="对照品名称" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="project_name" label="检测项目"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="internal_batch" label="厂内批号"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="cas_no" label="CAS号"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="cat_no" label="供应商货号"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="manufacturer_batch" label="厂家批号"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="manufacturer" label="供应商/来源"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="spec" label="规格/瓶"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="purity" label="纯度(%)"><InputNumber style={{ width: '100%' }} precision={4} /></Form.Item></Col>
            <Col span={8}><Form.Item name="content" label="含量(%)"><InputNumber style={{ width: '100%' }} precision={4} /></Form.Item></Col>
            <Col span={8}><Form.Item name="quantity" label="数量"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="stock_status" label="库存状态"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="arrival_date" label="到货日期"><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="produce_date" label="生产/标定日期"><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="expire_date" label="有效期至"><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="recal_cycle_days" label="复标周期(天)"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="open_date" label="开瓶日期"><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="open_expire_days" label="开瓶有效期(天)"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="storage_cond_code" label="贮存条件"><Select options={storageCondOptions} placeholder="请选择" allowClear /></Form.Item></Col>
            <Col span={8}><Form.Item name="location" label="存放位置"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="has_coa" label="是否有COA" valuePropName="checked" initialValue={false}><Switch /></Form.Item></Col>
            <Col span={8}><Form.Item name="handover_no" label="交接单号"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="ref_status" label="状态" initialValue={0}>
              <Select options={[{ label: '在用', value: 0 }, { label: '用完', value: 1 }, { label: '过期', value: 2 }, { label: '报废', value: 3 }]} />
            </Form.Item></Col>
            <Col span={24}><Form.Item name="remark" label="备注"><TextArea rows={2} /></Form.Item></Col>
          </Row>
        )

      default:
        return <div style={{ padding: 40, textAlign: 'center', color: '#999' }}>未知模块类型</div>
    }
  }

  if (loading) return <div style={{ textAlign: 'center', padding: 50 }}><Spin size="large" /></div>

  return (
    <div style={{ padding: '0 24px' }}>
      <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/quality/static-data')}>返回</Button>
        <h2 style={{ margin: 0 }}>{isNew ? '新建' : '编辑'} - {MODULE_LABELS[moduleType] || moduleType}</h2>
      </div>
      <Card>
        <Form form={form} layout="vertical" onFinish={handleSave}>
          {renderFormFields()}

          {/* 附件上传区域（仅支持的模块显示） */}
          {supportsUpload && (
            <>
              <Divider orientation={"left" as const}>
                <PaperClipOutlined /> 附件上传
              </Divider>
              <div style={{ marginBottom: 16 }}>
                <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
                  支持 PDF、Word、Excel、图片格式，单文件不超过 50MB，最多上传 5 个文件
                </Text>
                <Form.Item name="attach_file" style={{ marginBottom: 8 }}>
                  <Input.TextArea rows={1} placeholder="已保存的文件名（系统自动维护）" readOnly style={{ display: 'none' }} />
                </Form.Item>
                <Upload
                  {...uploadProps}
                  fileList={attachFiles}
                  style={{ width: '100%' }}
                >
                  <Button icon={<PaperClipOutlined />} loading={uploadLoading}>
                    选择文件
                  </Button>
                </Upload>
                {attachFiles.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    {attachFiles.map((file) => (
                      <div key={file.uid} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                        <PaperClipOutlined />
                        <Text>{file.name}</Text>
                        {file.status === 'done' && (
                          <Link href={`${API}/download/${encodeURIComponent(file.response?.data?.stored_name || file.name)}`} target="_blank">
                            <DownloadOutlined /> 下载
                          </Link>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}

          {/* 质量标准检验项目明细子表 */}
          {isStdWithItems && (
            <>
              <Divider orientation={"left" as const}>
                检验项目明细
                <Button type="link" size="small" icon={<PlusOutlined />} onClick={addItem} style={{ marginLeft: 8 }}>
                  新增项目
                </Button>
              </Divider>
              <Table
                columns={moduleType === 'material-standard' ? matItemColumns : prodItemColumns}
                dataSource={items as ItemRecord[]}
                rowKey="key"
                pagination={false}
                size="small"
                scroll={{ x: moduleType === 'product-standard' ? 1100 : 900 }}
                locale={{ emptyText: '暂无检验项目，请点击"新增项目"添加' }}
              />
            </>
          )}

          <Divider />
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={saving}>
                {isNew ? '创建' : '保存'}
              </Button>
              <Button onClick={() => router.push('/quality/static-data')}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

function DetailPageContent() {
  const params = useParams()
  const moduleType = (params.module || '') as string
  const id = (params.id || '') as string
  
  // Wait for params to be available
  if (!params.module || !params.id) {
    return <div style={{ padding: 50, textAlign: 'center' }}>Loading...</div>
  }
  
  return <StaticDataDetailPage moduleType={moduleType} id={id} />
}

export default function DetailPage() {
  return <DetailPageContent />
}