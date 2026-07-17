'use client'

import { useState, useEffect } from 'react'
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
  Space,
  Spin,
} from 'antd'
import {
  ArrowLeftOutlined,
  SaveOutlined,
  LoadingOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { useRouter, useSearchParams } from 'next/navigation'
import {
  getInstrument,
  updateInstrument,
  getCalibrationRules,
  createCalibrationRule,
} from '@/actions/instrument'
import type {
  Instrument,
  InstrumentUpdate,
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

export default function EditInstrumentPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const instrumentId = searchParams.get('id')
  
  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [form] = Form.useForm()
  const [ruleForm] = Form.useForm()
  const [instrument, setInstrument] = useState<Instrument | null>(null)

  useEffect(() => {
    if (!instrumentId) {
      message.error('缺少仪器ID参数')
      router.push('/quality/instrument/list')
      return
    }
    loadData()
  }, [instrumentId])

  const loadData = async () => {
    if (!instrumentId) return
    
    setInitialLoading(true)
    try {
      const response = await getInstrument(instrumentId)
      setInstrument(response)
      form.setFieldsValue({
        ...response,
        manufacture_date: response.manufacture_date ? dayjs(response.manufacture_date) : null,
      })

      const rules = await getCalibrationRules(instrumentId)
      if (rules && rules.length > 0) {
        const rule = rules[0]
        ruleForm.setFieldsValue({
          calibration_method: rule.calibration_method,
          calibration_cycle: rule.calibration_cycle,
          calibration_unit: rule.calibration_unit,
          last_calibration_date: rule.last_calibration_date ? dayjs(rule.last_calibration_date) : null,
          next_calibration_date: rule.next_calibration_date ? dayjs(rule.next_calibration_date) : null,
          calibration_agency: rule.calibration_agency,
          internal_calibrator_name: rule.internal_calibrator_name,
          warning_days: rule.warning_days,
        })
      }
    } catch (error) {
      message.error('加载数据失败')
      router.push('/quality/instrument/list')
    } finally {
      setInitialLoading(false)
    }
  }

  const handleSubmit = async () => {
    if (!instrument) return
    
    try {
      const values = await form.validateFields()
      const ruleValues = await ruleForm.validateFields()

      const instrumentData: InstrumentUpdate = {
        instrument_name: values.instrument_name,
        model: values.model,
        serial_no: values.serial_no,
        manufacturer: values.manufacturer,
        location: values.location,
        category: values.category,
        manufacture_date: values.manufacture_date?.format('YYYY-MM-DD'),
        responsible_name: values.responsible_name,
        remark: values.remark,
      }

      setLoading(true)
      await updateInstrument(instrument.id, instrumentData)

      if (ruleValues.calibration_method) {
        const rules = await getCalibrationRules(instrument.id)
        const ruleData: CalibrationRuleCreate = {
          instrument_id: instrument.id,
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
        
        if (!rules || rules.length === 0) {
          await createCalibrationRule(ruleData)
        }
      }

      message.success('更新成功')
      router.push('/quality/instrument/list')
    } catch (error) {
      message.error('更新失败')
    } finally {
      setLoading(false)
    }
  }

  if (initialLoading) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <Spin indicator={<LoadingOutlined spin style={{ fontSize: 48 }} />} />
        <p style={{ marginTop: 16 }}>加载中...</p>
      </div>
    )
  }

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => router.back()}>
              返回
            </Button>
            <span>编辑仪器</span>
          </Space>
        }
        extra={
          <Space>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={loading}
              onClick={handleSubmit}
            >
              保存
            </Button>
          </Space>
        }
      >
        <Divider>基本信息</Divider>
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="仪器编号">
                <Input value={instrument?.instrument_no} disabled />
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
        <Form form={ruleForm} layout="vertical">
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
                <Input placeholder="请输入周期" />
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
                <Input placeholder="默认7天" />
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