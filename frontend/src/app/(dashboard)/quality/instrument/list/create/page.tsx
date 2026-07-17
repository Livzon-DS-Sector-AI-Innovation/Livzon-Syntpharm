'use client'

import { useState, useRef } from 'react'
import {
  Card,
  Form,
  Input,
  Select,
  DatePicker,
  Button,
  Row,
  Col,
  message,
  Divider,
  InputNumber,
  Space,
  Spin,
} from 'antd'
import {
  ArrowLeftOutlined,
  SaveOutlined,
  CameraOutlined,
  LoadingOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { useRouter } from 'next/navigation'
import {
  createInstrument,
  createCalibrationRule,
  recognizeInstrumentLabel,
  type AIRecognizedInstrumentInfo,
} from '@/actions/instrument'
import type {
  InstrumentCreate,
  CalibrationRuleCreate,
} from '@/types/instrument'

const categoryOptions = [
  { value: 'physicochemical', label: '理化' },
  { value: 'chromatography', label: '色谱' },
  { value: 'microbiology', label: '微生物' },
  { value: 'balance', label: '天平' },
  { value: 'oven', label: '烘箱' },
  { value: 'other', label: '其他' },
]

const methodOptions = [
  { value: 'external', label: '外委校准' },
  { value: 'internal', label: '内部校准' },
]

const unitOptions = [
  { value: 'month', label: '月' },
  { value: 'year', label: '年' },
]

export default function CreateInstrumentPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()
  const [ruleForm] = Form.useForm()
  const fileInputRef = useRef<HTMLInputElement>(null)

  // AI 识别状态
  const [uploading, setUploading] = useState(false)
  const [recognizing, setRecognizing] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [recognizedData, setRecognizedData] = useState<AIRecognizedInstrumentInfo | null>(null)
  const [recognitionError, setRecognitionError] = useState<string | null>(null)

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      message.error('请上传图片文件')
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      message.error('图片大小不能超过 10MB')
      return
    }

    setRecognitionError(null)
    setRecognizedData(null)

    const objectUrl = URL.createObjectURL(file)
    setPreviewUrl(objectUrl)

    setUploading(true)
    setRecognizing(true)

    try {
      const result = await recognizeInstrumentLabel(file)
      setRecognizedData(result)

      const formValues: Record<string, unknown> = {}
      const ruleValues: Record<string, unknown> = {}

      if (result.instrument_name) formValues.instrument_name = result.instrument_name
      if (result.model) formValues.model = result.model
      if (result.serial_no) formValues.serial_no = result.serial_no
      if (result.manufacturer) formValues.manufacturer = result.manufacturer
      if (result.last_calibration_date && dayjs(result.last_calibration_date).isValid()) {
        ruleValues.last_calibration_date = dayjs(result.last_calibration_date)
      }
      if (result.next_calibration_date && dayjs(result.next_calibration_date).isValid()) {
        ruleValues.next_calibration_date = dayjs(result.next_calibration_date)
      }
      if (result.calibration_agency) ruleValues.calibration_agency = result.calibration_agency

      if (Object.keys(formValues).length > 0) form.setFieldsValue(formValues)
      if (Object.keys(ruleValues).length > 0) ruleForm.setFieldsValue(ruleValues)

      message.success('识别完成，请核对结果')
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : '识别失败'
      setRecognitionError(errorMsg)
      message.error(errorMsg)
    } finally {
      setUploading(false)
      setRecognizing(false)
    }
  }

  const handleResetRecognition = () => {
    setPreviewUrl(null)
    setRecognizedData(null)
    setRecognitionError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      const ruleValues = await ruleForm.validateFields()

      const instrumentData: InstrumentCreate = {
        instrument_no: values.instrument_no,
        instrument_name: values.instrument_name,
        model: values.model,
        serial_no: values.serial_no,
        manufacturer: values.manufacturer,
        location: values.location,
        category: values.category,
        manufacture_date: values.manufacture_date?.format('YYYY-MM-DD'),
        responsible_name: values.responsible_name,
        is_active: true,
        remark: values.remark,
      }

      setLoading(true)

      const result = await createInstrument(instrumentData)

      if (ruleValues.calibration_method) {
        const ruleData: CalibrationRuleCreate = {
          instrument_id: result.id,
          calibration_method: ruleValues.calibration_method,
          calibration_cycle: ruleValues.calibration_cycle,
          calibration_unit: ruleValues.calibration_unit,
          last_calibration_date: ruleValues.last_calibration_date?.format('YYYY-MM-DD'),
          next_calibration_date: ruleValues.next_calibration_date?.format('YYYY-MM-DD'),
          calibration_agency: ruleValues.calibration_agency,
          internal_calibrator_name: ruleValues.internal_calibrator_name,
          warning_days: ruleValues.warning_days || 7,
          is_active: true,
        }
        await createCalibrationRule(ruleData)
      }

      message.success('创建成功')
      router.push('/quality/instrument/list')
    } catch (error) {
      message.error('创建失败')
    } finally {
      setLoading(false)
    }
  }

  const isLoading = uploading || recognizing

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => router.back()}>
              返回
            </Button>
            <span>新增仪器</span>
          </Space>
        }
        extra={
          <Button
            type="primary"
            icon={<SaveOutlined />}
            loading={loading}
            onClick={handleSubmit}
          >
            保存
          </Button>
        }
      >
        <Divider>AI 图片识别</Divider>
        <div style={{ marginBottom: 24 }}>
          {!previewUrl ? (
            <div
              style={{
                border: '2px dashed #d9d9d9',
                borderRadius: 8,
                padding: '40px 24px',
                textAlign: 'center',
                background: '#fafafa',
                cursor: 'pointer',
              }}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/jpg,image/webp"
                style={{ display: 'none' }}
                onChange={handleFileSelect}
              />
              <Spin spinning={isLoading} indicator={<LoadingOutlined spin />}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
                  <CameraOutlined style={{ fontSize: 48, color: '#999' }} />
                  <div>
                    <p style={{ margin: 0, color: '#666', fontSize: 14 }}>
                      点击上传设备标签照片，AI自动识别填写信息
                    </p>
                    <p style={{ margin: '8px 0 0', color: '#999', fontSize: 12 }}>
                      支持 JPG/PNG/WebP 格式，最大 10MB
                    </p>
                  </div>
                  <Button icon={<CameraOutlined />} style={{ marginTop: 8 }}>
                    选择文件
                  </Button>
                </div>
              </Spin>
            </div>
          ) : (
            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
              <div
                style={{
                  flex: '0 0 300px',
                  border: '1px solid #d9d9d9',
                  borderRadius: 8,
                  padding: 16,
                  background: '#fafafa',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                  <span style={{ fontWeight: 500 }}>已上传设备标签照片</span>
                  <Button type="link" size="small" onClick={handleResetRecognition}>
                    重新上传
                  </Button>
                </div>
                <img
                  src={previewUrl}
                  alt="设备标签预览"
                  style={{
                    maxWidth: '100%',
                    maxHeight: 200,
                    objectFit: 'contain',
                    display: 'block',
                    margin: '0 auto',
                  }}
                />
              </div>

              <div style={{ flex: 1, minWidth: 300 }}>
                <Spin spinning={recognizing} indicator={<LoadingOutlined spin />}>
                  {recognitionError && (
                    <div style={{ color: '#ff4d4f', marginBottom: 16 }}>{recognitionError}</div>
                  )}

                  {recognizedData && (
                    <div>
                      <h4 style={{ marginBottom: 12 }}>识别结果：</h4>
                      <Row gutter={[16, 8]}>
                        <Col span={12}>
                          <div style={{ color: '#999', fontSize: 12 }}>仪器名称</div>
                          <div>{recognizedData.instrument_name || <span style={{ color: '#ff4d4f' }}>未识别到</span>}</div>
                        </Col>
                        <Col span={12}>
                          <div style={{ color: '#999', fontSize: 12 }}>规格型号</div>
                          <div>{recognizedData.model || <span style={{ color: '#ff4d4f' }}>未识别到</span>}</div>
                        </Col>
                        <Col span={12}>
                          <div style={{ color: '#999', fontSize: 12 }}>出厂编号</div>
                          <div>{recognizedData.serial_no || <span style={{ color: '#ff4d4f' }}>未识别到</span>}</div>
                        </Col>
                        <Col span={12}>
                          <div style={{ color: '#999', fontSize: 12 }}>制造商</div>
                          <div>{recognizedData.manufacturer || <span style={{ color: '#ff4d4f' }}>未识别到</span>}</div>
                        </Col>
                      </Row>
                    </div>
                  )}
                </Spin>
              </div>
            </div>
          )}
        </div>

        <Divider>基本信息</Divider>
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="instrument_no" label="仪器编号" rules={[{ required: true }]}>
                <Input placeholder="请输入仪器编号" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="instrument_name" label="仪器名称" rules={[{ required: true }]}>
                <Input placeholder="请输入仪器名称" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="model" label="型号">
                <Input placeholder="请输入型号" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="serial_no" label="出厂编号">
                <Input placeholder="请输入出厂编号" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="manufacturer" label="制造商">
                <Input placeholder="请输入制造商" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="location" label="存放地点">
                <Input placeholder="请输入存放地点" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="category" label="仪器分类">
                <Select placeholder="请选择分类">
                  {categoryOptions.map((opt) => (
                    <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="responsible_name" label="使用负责人">
                <Input placeholder="请输入负责人" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="manufacture_date" label="出厂日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item name="remark" label="备注">
                <Input.TextArea rows={3} placeholder="请输入备注" />
              </Form.Item>
            </Col>
          </Row>
        </Form>

        <Divider>校准规则（可选）</Divider>
        <Form form={ruleForm} layout="vertical" initialValues={{ warning_days: 7 }}>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="calibration_method" label="校准方式">
                <Select placeholder="请选择" allowClear>
                  {methodOptions.map((opt) => (
                    <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="calibration_cycle" label="校准周期">
                <InputNumber style={{ width: '100%' }} min={0} placeholder="请输入周期" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="calibration_unit" label="周期单位">
                <Select placeholder="请选择" allowClear>
                  {unitOptions.map((opt) => (
                    <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="last_calibration_date" label="最近校准日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="next_calibration_date" label="下次校准日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="warning_days" label="提前预警天数">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="calibration_agency" label="校准机构">
                <Input placeholder="请输入校准机构" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="internal_calibrator_name" label="内校人员">
                <Input placeholder="请输入内校人员" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Card>
    </div>
  )
}