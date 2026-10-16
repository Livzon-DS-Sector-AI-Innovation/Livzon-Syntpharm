'use client'

import { useEffect, useRef, useState } from 'react'
import { Modal, Form, Input, InputNumber, Select, Button, Steps, Result, Space, App, Alert, Typography } from 'antd'
import { crossImportFromBitableAction } from '@/actions/energy'
import { useEnergySyncJob } from '@/hooks/useEnergySyncJob'

const { Text } = Typography

interface BitableCrossImportModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

type ImportStep = 'input' | 'result'

export function BitableCrossImportModal({ open, onClose, onSuccess }: BitableCrossImportModalProps) {
  const { message } = App.useApp()
  const [form] = Form.useForm()
  const [step, setStep] = useState<ImportStep>('input')
  const [loading, setLoading] = useState(false)
  const [importMode, setImportMode] = useState<'year' | 'month'>('year')
  const [jobId, setJobId] = useState<string | null>(null)
  const [startedAt, setStartedAt] = useState<number | null>(null)
  const notifiedJobId = useRef<string | null>(null)

  const { phase, result, errorMessage } = useEnergySyncJob(jobId, startedAt)

  useEffect(() => {
    if (phase !== 'done' || !jobId || notifiedJobId.current === jobId) return
    notifiedJobId.current = jobId
    // 只有轮询到 done 才刷新页面：月度记录与汇总都走浏览器侧 React Query，
    // 真正的刷新触发点是父组件的 onSuccess（内部 invalidateQueries）
    onSuccess()
  }, [phase, jobId, onSuccess])

  const handleClose = () => {
    setStep('input')
    setJobId(null)
    setStartedAt(null)
    notifiedJobId.current = null
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
      
      // 提交端点只回受理句柄（`{job_id, status:"running"}`），计数靠轮询
      const job = await crossImportFromBitableAction(data)
      setJobId(job.job_id)
      setStartedAt(Date.now())
      setStep('result')
    } catch (error: unknown) {
      if (error && typeof error === "object" && "errorFields" in error) return
      message.error('导入任务提交失败：' + ((error instanceof Error ? error.message : null) || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  const currentStep = step === 'input' ? 0 : 1
  const errorCount = result?.total_errors ?? result?.errors?.length ?? 0
  const shownErrors = (result?.errors ?? []).slice(0, 10)
  const isRunning = !loading && phase === 'running'

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
          <Button type="primary" onClick={handleClose} disabled={isRunning}>
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
                <div>• 已存在的记录会更新数值，被删除过的记录会复活</div>
              </div>
            }
            style={{ marginTop: 8 }}
          />
        </Form>
      )}

      {step === 'result' && isRunning && (
        <Result
          status="info"
          title="导入进行中"
          subTitle="正在从飞书多维表格读取数据并写入，按年份导入需要几十秒，请勿关闭页面。"
        />
      )}

      {step === 'result' && phase === 'failed' && (
        <Result
          status="error"
          title="导入失败"
          subTitle={errorMessage || '后台任务执行出错，请查看后端日志。'}
        />
      )}

      {step === 'result' && phase === 'unavailable' && (
        <Result
          status="warning"
          title="任务状态已不可查"
          subTitle="导入状态保存在后端进程内，服务重启或换实例后会查不到（D-11）。数据可能已写入，请关闭后刷新列表确认。"
        />
      )}

      {step === 'result' && phase === 'timeout' && (
        <Result
          status="info"
          title="导入仍在进行"
          subTitle="已超过 3 分钟仍未完成，页面停止轮询。数据可能稍后写入，请关闭后刷新列表确认。"
        />
      )}

      {step === 'result' && phase === 'done' && result && (
        <Result
          status={errorCount > 0 ? 'warning' : 'success'}
          title={errorCount > 0 ? '导入完成（有错误）' : '导入成功'}
          subTitle={
            <div>
              {result.year && <div>年份：{result.year}</div>}
              {result.table && <div>表格：{result.table}</div>}
              {result.months_imported !== undefined && (
                <div>导入月份数：{result.months_imported} 个月</div>
              )}
              <div>新建记录：<Text strong>{result.total_created ?? 0}</Text> 条</div>
              <div>更新记录：<Text strong>{result.total_updated ?? 0}</Text> 条</div>
              {errorCount > 0 && (
                <div>错误数：<Text type="danger">{errorCount}</Text></div>
              )}
            </div>
          }
        >
          {shownErrors.length > 0 && (
            <div style={{ textAlign: 'left', marginTop: 16 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>错误明细（最多 10 条）：</Text>
              <div style={{ marginTop: 8, fontSize: 13 }}>
                {shownErrors.map((err, i) => (
                  <div key={i} style={{ marginBottom: 4 }}>
                    <Text type="danger">{err}</Text>
                  </div>
                ))}
              </div>
            </div>
          )}
          {result.details && result.details.length > 0 && (
            <div style={{ textAlign: 'left', marginTop: 16 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>各月份详情：</Text>
              <div style={{ marginTop: 8, fontSize: 13 }}>
                {result.details.map((detail, i) => (
                  <div key={`${detail.table}-${i}`} style={{ marginBottom: 4 }}>
                    <Text>{detail.table}：</Text>
                    <Text type="success">新建 {detail.total_created ?? 0}</Text>
                    {' / '}
                    <Text type="warning">更新 {detail.total_updated ?? 0}</Text>
                    {' / '}
                    <Text type="secondary">解析 {detail.total_parsed ?? 0}</Text>
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
