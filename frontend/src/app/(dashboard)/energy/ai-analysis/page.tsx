'use client'

import { useState, useEffect } from 'react'
import { Card, Button, DatePicker, Select, App, Spin, Alert, Typography, InputNumber } from 'antd'
import dayjs from 'dayjs'
import TargetModal from '@/components/energy/TargetModal'
import { 
  analyzeEnergyV2, 
  getTarget, 
  type AIAnalysisResult, 
  type UnitConsumptionTarget 
} from '@/lib/api/client/energy'

const { Title, Paragraph, Text } = Typography
const { MonthPicker } = DatePicker

export default function AIAnalysisPage() {
  const { message } = App.useApp()
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AIAnalysisResult | null>(null)
  const [workshopId, setWorkshopId] = useState<string | null>(null)
  const [analysisMonth, setAnalysisMonth] = useState<string | null>(null)
  const [production, setProduction] = useState<number | null>(null)
  const [workshops, setWorkshops] = useState<any[]>([])
  const [currentTarget, setCurrentTarget] = useState<UnitConsumptionTarget | null>(null)
  const [targetLoading, setTargetLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)

  // 获取车间列表
  useEffect(() => {
    fetch('/api/v1/energy/workshops')
      .then(res => res.json())
      .then(json => {
        if (json.code === 200) {
          setWorkshops(json.data.map((w: any) => ({ value: w.id, label: w.name })))
        }
      })
  }, [])

  // 当车间或月份变化时，查询目标
  useEffect(() => {
    if (workshopId && analysisMonth) {
      setTargetLoading(true)
      getTarget(workshopId, analysisMonth)
        .then(target => {
          setCurrentTarget(target)
        })
        .catch(err => {
          console.error('查询目标失败:', err)
          setCurrentTarget(null)
        })
        .finally(() => {
          setTargetLoading(false)
        })
    } else {
      setCurrentTarget(null)
    }
  }, [workshopId, analysisMonth])

  const handleAnalyze = async () => {
    // 验证月份格式
    if (!analysisMonth || !/^\d{4}-\d{2}$/.test(analysisMonth)) {
      message.error('月份格式不正确，应为 YYYY-MM 格式')
      return
    }

    if (!workshopId || !analysisMonth || !production || production <= 0) {
      message.warning('请选择车间、月份并输入有效的产量')
      return
    }

    setLoading(true)
    try {
      const data = await analyzeEnergyV2({
        workshop_id: workshopId,
        analysis_month: analysisMonth,
        manual_production: production,
        include_ai_suggestion: true,
      })
      setResult(data)
    } catch (error: any) {
      message.error(error.message || '分析请求失败')
    } finally {
      setLoading(false)
    }
  }

  const handleTargetSuccess = (target: UnitConsumptionTarget) => {
    setCurrentTarget(target)
    if (result && production) {
      handleAnalyze()
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'normal': return '#52c41a'
      case 'warning': return '#faad14'
      case 'critical': return '#f5222d'
      case 'unknown': return '#8c8c8c'
      default: return '#8c8c8c'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'normal': return '✅'
      case 'warning': return '⚠️'
      case 'critical': return '🚨'
      case 'unknown': return 'ℹ️'
      default: return 'ℹ️'
    }
  }

  return (
    <div style={{ padding: '24px', background: '#f5f5f5', minHeight: '100vh' }}>
      <Title level={2}>AI 能耗智能分析</Title>
      
      <Card style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
          <Select 
            placeholder="选择车间" 
            style={{ width: 200 }} 
            onChange={(val) => setWorkshopId(val)}
            options={workshops} 
          />
          
          <MonthPicker 
            placeholder="选择月份" 
            onChange={(date) => setAnalysisMonth(date ? date.format('YYYY-MM') : null)} 
          />
          
          <InputNumber
            placeholder="当月产量（kg）"
            value={production}
            onChange={(val) => setProduction(val)}
            min={1}
            precision={0}
            style={{ width: 200 }}
            addonAfter="kg"
          />
          
          <Button 
            type="primary" 
            onClick={handleAnalyze} 
            loading={loading}
            disabled={!workshopId || !analysisMonth || !production}
          >
            🤖 开始智能分析
          </Button>
        </div>

        {workshopId && analysisMonth && (
          <div style={{ marginTop: 16, padding: 12, background: '#fafafa', borderRadius: 4 }}>
            <Text strong>单耗目标：</Text>
            {targetLoading ? (
              <Spin size="small" />
            ) : currentTarget ? (
              <>
                <Text>{currentTarget.target_unit_consumption.toFixed(4)} kWh/kg</Text>
                <Button 
                  type="link" 
                  size="small" 
                  onClick={() => setModalOpen(true)}
                  style={{ marginLeft: 8 }}
                >
                  ✏️ 修改目标
                </Button>
              </>
            ) : (
              <>
                <Text type="secondary">未设定</Text>
                <Button 
                  type="primary" 
                  size="small" 
                  onClick={() => setModalOpen(true)}
                  style={{ marginLeft: 8 }}
                >
                  ➕ 设定目标
                </Button>
              </>
            )}
          </div>
        )}
      </Card>

      {loading && <Spin size="large" style={{ display: 'block', margin: '50px auto' }} />}

      {result && (
        <>
          <Card title="📊 单耗分析结果" style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', gap: 24, marginBottom: 16 }}>
              <div style={{ flex: 1, padding: 16, background: '#f0f5ff', borderRadius: 8, textAlign: 'center' }}>
                <Text type="secondary">实际单耗</Text>
                <div style={{ fontSize: 24, fontWeight: 'bold', marginTop: 8 }}>
                  {result.actual_unit_consumption.toFixed(4)} kWh/kg
                </div>
              </div>
              
              <div style={{ flex: 1, padding: 16, background: '#f6ffed', borderRadius: 8, textAlign: 'center' }}>
                <Text type="secondary">目标单耗</Text>
                <div style={{ fontSize: 24, fontWeight: 'bold', marginTop: 8 }}>
                  {result.target_unit_consumption?.toFixed(4) ?? '—'} kWh/kg
                </div>
              </div>
              
              <div style={{ flex: 1, padding: 16, background: '#fff7e6', borderRadius: 8, textAlign: 'center' }}>
                <Text type="secondary">偏差率</Text>
                <div style={{ 
                  fontSize: 24, 
                  fontWeight: 'bold', 
                  marginTop: 8,
                  color: getStatusColor(result.deviation_status)
                }}>
                  {result.deviation_rate !== null ? `${result.deviation_rate > 0 ? '+' : ''}${result.deviation_rate}%` : '—'}
                </div>
              </div>
            </div>
            
            <Alert
              message={`${getStatusIcon(result.deviation_status)} 状态：${
                result.deviation_status === 'normal' ? '正常' :
                result.deviation_status === 'warning' ? '警告（超出目标 5%-15%）' :
                result.deviation_status === 'critical' ? '严重超标（超出目标 &gt;15%）' :
                '未知（未设定目标）'
              }`}
              type={
                result.deviation_status === 'normal' ? 'success' :
                result.deviation_status === 'warning' ? 'warning' :
                result.deviation_status === 'critical' ? 'error' :
                'info'
              }
              showIcon
            />
          </Card>

          {result.ai_suggestion && (
            <Card title="🤖 AI 智能建议">
              <Paragraph strong>{result.ai_suggestion.summary}</Paragraph>
              
              <Title level={5}>详细分析</Title>
              <Paragraph>{result.ai_suggestion.detailed_analysis}</Paragraph>
              
              <Title level={5}>改进建议</Title>
              <ul>
                {result.ai_suggestion.recommendations.map((rec, idx) => (
                  <li key={idx} style={{ marginBottom: 8 }}>{rec}</li>
                ))}
              </ul>
              
              <Alert
                message={`置信度：${
                  result.ai_suggestion.confidence_level === 'high' ? '高' :
                  result.ai_suggestion.confidence_level === 'medium' ? '中' :
                  '低'
                }`}
                type="info"
                showIcon
              />
            </Card>
          )}
        </>
      )}

      <TargetModal
        open={modalOpen}
        workshopId={workshopId}
        workshopName={workshops.find(w => w.value === workshopId)?.label || ''}
        targetMonth={analysisMonth || ''}
        existingTarget={currentTarget}
        onClose={() => setModalOpen(false)}
        onSuccess={handleTargetSuccess}
      />
    </div>
  )
}
