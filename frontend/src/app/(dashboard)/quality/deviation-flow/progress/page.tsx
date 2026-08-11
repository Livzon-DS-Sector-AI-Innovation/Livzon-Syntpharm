'use client'

import { useState, useEffect } from 'react'
import { Card, Descriptions, Tag, Button, Space, Typography, Divider, Timeline, Upload, message } from 'antd'
import {
  ArrowLeftOutlined, EditOutlined, UploadOutlined, CheckCircleOutlined,
  FileTextOutlined, TeamOutlined, UserOutlined, FileProtectOutlined,
  InfoCircleOutlined, AlertOutlined, ToolOutlined, SafetyOutlined, SettingOutlined,
} from '@ant-design/icons'
import { useRouter, useSearchParams } from 'next/navigation'
import dayjs from 'dayjs'
import '../deviation-style.css'

const { Text } = Typography

const API_BASE = '/api/v1'

const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  draft: { color: 'default', label: '草稿' },
  basic_completed: { color: 'processing', label: '基础完成' },
  detail_completed: { color: 'warning', label: '详情完成' },
  completed: { color: 'success', label: '已完成' },
}

const URGENCY_COLORS: Record<string, string> = {
  normal: 'green',
  important: 'orange',
  serious: 'red',
}

function SectionCard({
  icon,
  title,
  children,
  className = '',
}: {
  icon: React.ReactNode
  title: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={`deviation-section-card ${className}`}>
      <div className="deviation-section-header">
        <div className="deviation-section-icon">{icon}</div>
        <h3 className="deviation-section-title">{title}</h3>
      </div>
      <div className="deviation-section-body">{children}</div>
    </div>
  )
}

export default function DeviationProgressPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const deviationId = searchParams.get('id')
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)')
    const update = () => setIsMobile(mq.matches)
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])

  useEffect(() => {
    if (deviationId) {
      loadDetail()
    }
  }, [deviationId])

  const loadDetail = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/quality/deviation-flow/${deviationId}`)
      const result = await response.json()

      if (result.code === 200) {
        setData(result.data)
      } else {
        message.error(result.message || '加载失败')
      }
    } catch (error) {
      message.error('加载失败')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="deviation-page" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
        <h1 className="text-2xl font-semibold text-gray-800">偏差详情</h1>
        <Text type="secondary">加载中...</Text>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="deviation-page" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
        <h1 className="text-2xl font-semibold text-gray-800">偏差详情</h1>
        <Text type="secondary">偏差不存在</Text>
      </div>
    )
  }

  const statusConfig = STATUS_CONFIG[data.status] || { color: 'default', label: data.status }
  const urgencyColor = URGENCY_COLORS[data.urgency_level] || 'default'

  return (
    <div className="deviation-page">
      <div className="deviation-header">
        <div className="deviation-header-left">
          <h1>
            <FileProtectOutlined />
            偏差详情
            <Tag color={statusConfig.color} style={{ marginLeft: 8 }}>{statusConfig.label}</Tag>
          </h1>
          <p>偏差编号：{data.deviation_no}</p>
        </div>
        <div className="deviation-header-right">
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => router.push('/quality/deviation-flow/query')}
            size={isMobile ? 'small' : 'middle'}
          >
            {isMobile ? '' : '返回列表'}
          </Button>
        </div>
      </div>

      <SectionCard icon={<InfoCircleOutlined />} title="偏差信息">
        <div style={{ marginBottom: 16 }}>
          <Text strong style={{ fontSize: 16, color: '#1f2937' }}>{data.theme}</Text>
        </div>
        <div className="deviation-form-grid">
          <div className="deviation-info-item">
            <span className="deviation-info-label">偏差类型</span>
            <span className="deviation-info-value">
              <Tag style={{ margin: 0 }}>{data.deviation_type_label || data.deviation_type || '-'}</Tag>
            </span>
          </div>
          <div className="deviation-info-item">
            <span className="deviation-info-label">紧急等级</span>
            <span className="deviation-info-value">
              <Tag color={urgencyColor} style={{ margin: 0 }}>{data.urgency_level_label || data.urgency_level || '-'}</Tag>
            </span>
          </div>
          <div className="deviation-info-item">
            <span className="deviation-info-label">责任部门</span>
            <span className="deviation-info-value">{data.responsible_department || '-'}</span>
          </div>
          <div className="deviation-info-item">
            <span className="deviation-info-label">发生区域</span>
            <span className="deviation-info-value">{data.occurred_area || '-'}</span>
          </div>
          <div className="deviation-info-item">
            <span className="deviation-info-label">偏差发生日期</span>
            <span className="deviation-info-value">
              {data.occurred_date ? dayjs(data.occurred_date).format('YYYY-MM-DD HH:mm') : '-'}
            </span>
          </div>
          <div className="deviation-info-item">
            <span className="deviation-info-label">发现日期</span>
            <span className="deviation-info-value">
              {data.discovered_date ? dayjs(data.discovered_date).format('YYYY-MM-DD HH:mm') : '-'}
            </span>
          </div>
        </div>
      </SectionCard>

      <SectionCard icon={<FileTextOutlined />} title="偏差详情">
        <div className="deviation-form-grid">
          <div className="deviation-info-item">
            <span className="deviation-info-label">涉及产品/物料</span>
            <span className="deviation-info-value">{data.product_name || '-'}</span>
          </div>
          <div className="deviation-info-item">
            <span className="deviation-info-label">批次号</span>
            <span className="deviation-info-value">{data.batch_no || '-'}</span>
          </div>
          <div className="deviation-info-item">
            <span className="deviation-info-label">涉及设备/仪器</span>
            <span className="deviation-info-value">{data.equipment || '-'}</span>
          </div>
          <div className="deviation-info-item">
            <span className="deviation-info-label">偏离标准依据</span>
            <span className="deviation-info-value">{data.standard_based_on || '-'}</span>
          </div>
        </div>

        <div style={{ marginTop: 16 }}>
          <Text strong style={{ fontSize: 13, color: '#475569' }}>偏差经过描述</Text>
          <div style={{
            marginTop: 8,
            padding: 12,
            background: '#f8fafc',
            borderRadius: 8,
            fontSize: 13,
            lineHeight: 1.8,
            whiteSpace: 'pre-wrap',
            color: '#1f2937'
          }}>
            {data.deviation_description || '-'}
          </div>
        </div>

        {data.risk_assessment && (
          <div style={{ marginTop: 16 }}>
            <Text strong style={{ fontSize: 13, color: '#475569' }}>初步风险影响评估</Text>
            <div style={{
              marginTop: 8,
              padding: 12,
              background: '#fff7e6',
              borderRadius: 8,
              fontSize: 13,
              lineHeight: 1.8,
              whiteSpace: 'pre-wrap',
              color: '#d46b08'
            }}>
              {data.risk_assessment}
            </div>
          </div>
        )}
      </SectionCard>

      <SectionCard icon={<SafetyOutlined />} title="辅助信息">
        <div className="deviation-form-grid">
          <div className="deviation-info-item">
            <span className="deviation-info-label">临时处置措施</span>
            <span className="deviation-info-value">{data.temp_measures || '-'}</span>
          </div>
          <div className="deviation-info-item">
            <span className="deviation-info-label">关联偏差单号</span>
            <span className="deviation-info-value">{data.related_deviation_no || '-'}</span>
          </div>
          <div className="deviation-info-item">
            <span className="deviation-info-label">关联CAPA</span>
            <span className="deviation-info-value">{data.related_capa || '-'}</span>
          </div>
          <div className="deviation-info-item">
            <span className="deviation-info-label">备注</span>
            <span className="deviation-info-value">{data.remarks || '-'}</span>
          </div>
        </div>
      </SectionCard>

      <SectionCard icon={<UserOutlined />} title="填报信息">
        <div className="deviation-form-grid">
          <div className="deviation-info-item">
            <span className="deviation-info-label">填报人</span>
            <span className="deviation-info-value">
              <UserOutlined style={{ marginRight: 4 }} />
              {data.reporter || '-'}
            </span>
          </div>
          <div className="deviation-info-item">
            <span className="deviation-info-label">填报部门</span>
            <span className="deviation-info-value">{data.reporter_department || '-'}</span>
          </div>
          <div className="deviation-info-item">
            <span className="deviation-info-label">填报时间</span>
            <span className="deviation-info-value">
              {data.report_time ? dayjs(data.report_time).format('YYYY-MM-DD HH:mm') : '-'}
            </span>
          </div>
          <div className="deviation-info-item">
            <span className="deviation-info-label">创建时间</span>
            <span className="deviation-info-value">
              {data.created_at ? dayjs(data.created_at).format('YYYY-MM-DD HH:mm') : '-'}
            </span>
          </div>
        </div>
      </SectionCard>

      <SectionCard icon={<TeamOutlined />} title="提醒接收人">
        <div className="deviation-form-grid">
          <div className="deviation-info-item">
            <span className="deviation-info-label">QA人员</span>
            <span className="deviation-info-value">
              <TeamOutlined style={{ marginRight: 4 }} />
              {data.qa_feishu_name || '-'}
            </span>
          </div>
          <div className="deviation-info-item">
            <span className="deviation-info-label">部门负责人</span>
            <span className="deviation-info-value">
              <TeamOutlined style={{ marginRight: 4 }} />
              {data.dept_leader_feishu_name || '-'}
            </span>
          </div>
        </div>
      </SectionCard>

      <SectionCard icon={<ToolOutlined />} title="操作记录">
        <Timeline
          items={[
            {
              color: 'green',
              children: (
                <>
                  <div style={{ fontWeight: 600, color: '#1f2937' }}>创建偏差</div>
                  <div style={{ color: '#6b7280', fontSize: 13 }}>{data.reporter}</div>
                  <div style={{ color: '#94a3b8', fontSize: 12 }}>
                    {data.created_at ? dayjs(data.created_at).format('YYYY-MM-DD HH:mm') : '-'}
                  </div>
                </>
              ),
            },
            ...(data.status !== 'draft' ? [{
              color: 'blue',
              children: (
                <>
                  <div style={{ fontWeight: 600, color: '#1f2937' }}>提交偏差</div>
                  <div style={{ color: '#6b7280', fontSize: 13 }}>状态变更为「{data.status_label || data.status}」</div>
                  <div style={{ color: '#94a3b8', fontSize: 12 }}>
                    {data.updated_at ? dayjs(data.updated_at).format('YYYY-MM-DD HH:mm') : '-'}
                  </div>
                </>
              ),
            }] : []),
          ]}
        />
      </SectionCard>

      {data.status !== 'completed' && (
        <div className="deviation-actions">
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => router.push('/quality/deviation-flow/query')}
          >
            返回
          </Button>
          {data.status === 'draft' && (
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={() => router.push(`/quality/deviation-flow/create?edit=${data.id}`)}
            >
              编辑
            </Button>
          )}
        </div>
      )}

      <div style={{ height: isMobile ? 80 : 0 }} />
    </div>
  )
}
