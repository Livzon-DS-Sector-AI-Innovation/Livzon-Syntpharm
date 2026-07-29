'use client'

import { useState } from 'react'
import { Modal, Form, Input, Switch, Button, Steps, Result, Space, App, Alert, Typography } from 'antd'
import { importFromFeishuAction } from '@/actions/energy'
import type { FeishuImportResult } from '@/types/energy'

const { Text } = Typography

interface FeishuImportModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

type ImportStep = 'input' | 'preview' | 'result'

export function FeishuImportModal({ open, onClose, onSuccess }: FeishuImportModalProps) {
  const { message } = App.useApp()
  const [form] = Form.useForm()
  const [step, setStep] = useState<ImportStep>('input')
  const [loading, setLoading] = useState(false)
  const [dryRunResult, setDryRunResult] = useState<FeishuImportResult | null>(null)
  const [finalResult, setFinalResult] = useState<FeishuImportResult | null>(null)

  const handleClose = () => {
    setStep('input')
    setDryRunResult(null)
    setFinalResult(null)
    form.resetFields()
    onClose()
  }

  const handleDryRun = async () => {
    try {
      const values = await form.validateFields()
      setLoading(true)
      const result = await importFromFeishuAction({
        spreadsheet_token: values.spreadsheet_token,
        sheet_id: values.sheet_id || undefined,
        source: 'feishu_bitable',
        dry_run: true,
      })
      setDryRunResult(result)
      setStep('preview')
    } catch (error: any) {
      if (error?.errorFields) return
      message.error('预览失败：' + (error?.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  const handleImport = async () => {
    try {
      const values = form.getFieldsValue()
      setLoading(true)
      const result = await importFromFeishuAction({
        spreadsheet_token: values.spreadsheet_token,
        sheet_id: values.sheet_id || undefined,
        source: 'feishu',
        dry_run: false,
      })
      setFinalResult(result)
      setStep('result')
    } catch (error: any) {
      message.error('导入失败：' + (error?.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  const currentStep = step === 'input' ? 0 : step === 'preview' ? 1 : 2

  return (
    <Modal
      title="从飞书表格导入能耗数据"
      open={open}
      onCancel={handleClose}
      width={600}
      footer={
        step === 'input' ? (
          <Space>
            <Button onClick={handleClose}>取消</Button>
            <Button type="primary" onClick={handleDryRun} loading={loading}>
              预览解析
            </Button>
          </Space>
        ) : step === 'preview' ? (
          <Space>
            <Button onClick={() => setStep('input')}>返回修改</Button>
            <Button type="primary" onClick={handleImport} loading={loading}>
              确认导入
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
          { title: '输入' },
          { title: '预览' },
          { title: '结果' },
        ]}
      />

      {step === 'input' && (
        <Form form={form} layout="vertical">
          <Form.Item
            name="spreadsheet_token"
            label="飞书表格 Token"
            rules={[{ required: true, message: '请输入表格 Token' }]}
            extra="从飞书电子表格 URL 中获取，如: https://xxx.feishu.cn/sheets/XXXXX 中的 XXXXX"
          >
            <Input placeholder="粘贴飞书表格 Token" />
          </Form.Item>
          <Form.Item
            name="sheet_id"
            label="工作表 ID（可选）"
            extra="留空则默认读取第一个工作表"
          >
            <Input placeholder="如 sheet1" />
          </Form.Item>
          <Alert
            type="info"
            showIcon
            message="支持两种交叉表格式"
            description={
              <div style={{ fontSize: 12, marginTop: 4 }}>
                <div>格式A：行=车间+能源类型，列=日期范围</div>
                <div>格式B：行=车间，列=日期范围×能源类型（双层表头）</div>
              </div>
            }
            style={{ marginTop: 8 }}
          />
        </Form>
      )}

      {step === 'preview' && dryRunResult && (
        <div>
          <Alert
            type={dryRunResult.errors.length > 0 ? 'warning' : 'success'}
            showIcon
            message={
              dryRunResult.errors.length > 0
                ? `解析完成，但有 ${dryRunResult.errors.length} 个问题`
                : '解析成功'
            }
            description={
              <div style={{ marginTop: 8 }}>
                <div>预计创建记录数：<Text strong>{dryRunResult.records_created}</Text></div>
              </div>
            }
          />
          {dryRunResult.errors.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>解析问题：</Text>
              <ul style={{ margin: '8px 0', paddingLeft: 20 }}>
                {dryRunResult.errors.map((err, i) => (
                  <li key={i} style={{ color: '#dd5b00', fontSize: 13 }}>{err}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {step === 'result' && finalResult && (
        <Result
          status={finalResult.errors.length > 0 ? 'warning' : 'success'}
          title={finalResult.errors.length > 0 ? '导入完成（有警告）' : '导入成功'}
          subTitle={
            <div>
              <div>新建车间：{finalResult.workshops_created} 个</div>
              <div>创建记录：{finalResult.records_created} 条</div>
              {finalResult.records_skipped > 0 && (
                <div>跳过记录：{finalResult.records_skipped} 条</div>
              )}
            </div>
          }
        >
          {finalResult.errors.length > 0 && (
            <div style={{ textAlign: 'left' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>导入问题：</Text>
              <ul style={{ margin: '8px 0', paddingLeft: 20 }}>
                {finalResult.errors.map((err, i) => (
                  <li key={i} style={{ color: '#dd5b00', fontSize: 13 }}>{err}</li>
                ))}
              </ul>
            </div>
          )}
        </Result>
      )}
    </Modal>
  )
}
