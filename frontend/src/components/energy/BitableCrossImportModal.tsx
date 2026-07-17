'use client'

import { useState } from 'react'
import { Modal, Form, Input, InputNumber, Select, Button, Steps, Result, Space, App, Alert, Typography } from 'antd'
import { importFromBitable } from '@/actions/energy'

const { Text } = Typography

interface BitableCrossImportModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

type ImportStep = 'input' | 'result'

interface ImportResult {
  status: string
  year?: number
  months_imported?: number
  total_created?: number
  total_updated?: number
  total_errors?: number
  details?: Array<{
    table: string
    total_created: number
    total_updated: number
    total_parsed: number
  }>
}

export function BitableCrossImportModal({ open, onClose, onSuccess }: BitableCrossImportModalProps) {
  const { message } = App.useApp()
  const [form] = Form.useForm()
  const [step, setStep] = useState<ImportStep>('input')
  const [loading, setLoading] = useState(false)
  const [importMode, setImportMode] = useState<'year' | 'month'>('year')
  const [result, setResult] = useState<ImportResult | null>(null)

  const handleClose = () => {
    setStep('input')
    setResult(null)
    form.resetFields()
    onClose()
  }

  const handleImport = async () => {
    try {
      const values = await form.validateFields()
      setLoading(true)
      
      const data = importMode === 'year' 
        ? { year: values.year }
        : { month: values.month }
      
      const importResult = await importFromBitable(data)
      setResult(importResult)
      setStep('result')
    } catch (error: any) {
      if (error?.errorFields) return
      message.error('导入失败：' + (error?.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  const currentStep = step === 'input' ? 0 : 1

  return (
    <Modal
      title="从飞书多维表格导入能耗数据"
      open={open}
      onCancel={handleClose}
      width={600}
      footer={
        step === 'input' ? (
          <Space>
            <Button onClick={handleClose}>取消</Button>
            <Button type="primary" onClick={handleImport} loading={loading}>
              开始导入
            </Button>
          </Space>
        ) : (
          <Button type="primary" onClick={() => { handleClose(); onSuccess() }}>
            完成
          </Button>
        )
      }
    >
      <Steps
        current={currentStep}
        size="small"
        style={{ marginBottom: 24 }}
        items={[
          { title: '配置' },
          { title: '结果' },
        ]}
      />

      {step === 'input' && (
        <Form form={form} layout="vertical" initialValues={{ year: 2026 }}>
          <Form.Item
            label="导入模式"
            required
          >
            <Select value={importMode} onChange={setImportMode}>
              <Select.Option value="year">按年份导入</Select.Option>
              <Select.Option value="month">按月份导入</Select.Option>
            </Select>
          </Form.Item>

          {importMode === 'year' ? (
            <Form.Item
              name="year"
              label="年份"
              rules={[{ required: true, message: '请输入年份' }]}
              extra="导入该年份所有月份的数据（如 2026）"
            >
              <InputNumber 
                min={2020} 
                max={2030} 
                style={{ width: '100%' }}
                placeholder="如 2026"
              />
            </Form.Item>
          ) : (
            <Form.Item
              name="month"
              label="月份"
              rules={[{ required: true, message: '请输入月份' }]}
              extra="导入指定月份的数据（如 2026-06）"
            >
              <Input
                style={{ width: '100%' }}
                placeholder="如 2026-06"
              />
            </Form.Item>
          )}

          <Alert
            type="info"
            showIcon
            message="导入说明"
            description={
              <div style={{ fontSize: 12, marginTop: 4 }}>
                <div>• 从飞书多维表格的交叉表格式导入能耗数据</div>
                <div>• 支持电力、蒸汽、自来水三种能源类型</div>
                <div>• 自动创建不存在的车间</div>
                <div>• 已存在的记录会更新数值</div>
              </div>
            }
            style={{ marginTop: 8 }}
          />
        </Form>
      )}

      {step === 'result' && result && (
        <Result
          status={result.total_errors && result.total_errors > 0 ? 'warning' : 'success'}
          title={result.total_errors && result.total_errors > 0 ? '导入完成（有错误）' : '导入成功'}
          subTitle={
            <div>
              {result.year && <div>年份：{result.year}</div>}
              {result.months_imported !== undefined && (
                <div>导入月份数：{result.months_imported} 个月</div>
              )}
              <div>新建记录：<Text strong>{result.total_created}</Text> 条</div>
              <div>更新记录：<Text strong>{result.total_updated}</Text> 条</div>
              {result.total_errors !== undefined && result.total_errors > 0 && (
                <div>错误数：<Text type="danger">{result.total_errors}</Text></div>
              )}
            </div>
          }
        >
          {result.details && result.details.length > 0 && (
            <div style={{ textAlign: 'left', marginTop: 16 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>各月份详情：</Text>
              <div style={{ marginTop: 8, fontSize: 13 }}>
                {result.details.map((detail, i) => (
                  <div key={i} style={{ marginBottom: 4 }}>
                    <Text>{detail.table}：</Text>
                    <Text type="success">新建 {detail.total_created}</Text>
                    {' / '}
                    <Text type="warning">更新 {detail.total_updated}</Text>
                    {' / '}
                    <Text type="secondary">解析 {detail.total_parsed}</Text>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Result>
      )}
    </Modal>
  )
}
