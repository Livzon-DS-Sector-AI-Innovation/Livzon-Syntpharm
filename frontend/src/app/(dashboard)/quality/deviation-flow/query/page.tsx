'use client'

import { useState, useEffect, useMemo } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Space, Input, Select, Tag, Modal, message, Empty, Spin } from 'antd'
import {
  SearchOutlined, ReloadOutlined, EyeOutlined, EditOutlined, PlusOutlined,
  DeleteOutlined, AppstoreOutlined, TableOutlined, FileTextOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import { useRouter } from 'next/navigation'
import dayjs from 'dayjs'
import '../deviation-style.css'


const API_BASE = '/api/v1'

const STATUS_COLORS: Record<string, string> = {
  draft: 'default',
  basic_completed: 'processing',
  detail_completed: 'warning',
  completed: 'success',
}

const STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  basic_completed: '基础完成',
  detail_completed: '详情完成',
  completed: '已完成',
}

const URGENCY_COLORS: Record<string, string> = {
  '一般': 'green',
  '重要': 'orange',
  '严重': 'red',
}

const DEVIATION_TYPES_OPTIONS = [
  { value: 'ipc_defect', label: '过程控制（IPC）缺陷' },
  { value: 'foreign_object', label: '外来异物（有形）' },
  { value: 'calibration_maintenance', label: '校验/预防维修' },
  { value: 'mixup', label: '混淆' },
  { value: 'material_quality_defect', label: '物料质量缺陷' },
  { value: 'personnel_error', label: '人员失误' },
  { value: 'oos_result', label: '超标检验结果' },
  { value: 'documentation_defect', label: '文件记录缺陷' },
  { value: 'equipment_failure', label: '设备故障/过程中断' },
  { value: 'environment', label: '环境' },
  { value: 'other', label: '其它' },
]

interface DeviationFlowItem { id: string; deviation_no: string; theme?: string; deviation_type_label?: string; urgency_level_label?: string; status: string; status_label: string; responsible_department?: string; occurred_date?: string; reporter?: string; remaining_days?: number; completed_days?: number }
export default function DeviationQueryPage() {
  const router = useRouter()
  const [page, setPage] = useState(1)
  const [pageSize, _setPageSize] = useState(20)
  const [isMobile, setIsMobile] = useState(false)
  const [viewMode, setViewMode] = useState<'table' | 'card'>('table')

  const [keyword, setKeyword] = useState('')
  const [status, setStatus] = useState<string | undefined>()
  const [deviationType, setDeviationType] = useState<string | undefined>()
  const [urgencyLevel, setUrgencyLevel] = useState<string | undefined>()

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

  const queryParams = useMemo(() => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    })
    if (keyword) params.append('keyword', keyword)
    if (status) params.append('status', status)
    if (deviationType) params.append('deviation_type', deviationType)
    if (urgencyLevel) params.append('urgency_level', urgencyLevel)
    return params.toString()
  }, [page, pageSize, keyword, status, deviationType, urgencyLevel])

  const queryClient = useQueryClient()

  const { data: queryResult, isLoading: loading, refetch: loadData } = useQuery({
    queryKey: ['deviation-flow', queryParams],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/quality/deviation-flow?${queryParams}`)
      const result = await response.json()
      if (result.code === 200) return result.data
      return null
    },
  })

  const data = queryResult?.items || []
  const total = queryResult?.total || 0

  const handleSearch = () => {
    setPage(1)
  }

  const handleView = (record: DeviationFlowItem) => {
    router.push(`/quality/deviation-flow/progress?id=${record.id}`)
  }

  const handleEdit = (record: DeviationFlowItem) => {
    if (record.status === 'completed') {
      message.warning('已完成状态不能编辑')
      return
    }
    router.push(`/quality/deviation-flow/create?edit=${record.id}`)
  }

  const handleDelete = async (record: DeviationFlowItem) => {
    if (record.status !== 'draft') {
      message.warning('只有草稿状态可以删除')
      return
    }

    Modal.confirm({
      title: '确认删除',
      content: `确定要删除偏差单 ${record.deviation_no} 吗？`,
      onOk: async () => {
        try {
          const response = await fetch(`${API_BASE}/quality/deviation-flow/${record.id}`, {
            method: 'DELETE',
          })
          const result = await response.json()

          if (result.code === 200) {
            message.success('删除成功')
            queryClient.invalidateQueries({ queryKey: ['deviation-flow'] })
          } else {
            message.error(result.message || '删除失败')
          }
        } catch (_error) {
          message.error('删除失败')
        }
      },
    })
  }

  const _columns = [
    {
      title: '偏差编号',
      dataIndex: 'deviation_no',
      key: 'deviation_no',
      width: 130,
      render: (no: string) => <Tag color="blue">{no}</Tag>,
    },
    {
      title: '偏差主题',
      dataIndex: 'theme',
      key: 'theme',
      width: 200,
      ellipsis: true,
    },
    {
      title: '偏差类型',
      dataIndex: 'deviation_type_label',
      key: 'deviation_type',
      width: 100,
    },
    {
      title: '紧急等级',
      dataIndex: 'urgency_level_label',
      key: 'urgency_level',
      width: 80,
      render: (level: string) => (
        <Tag color={URGENCY_COLORS[level] || 'default'}>{level || '-'}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status_label',
      key: 'status',
      width: 100,
      render: (label: string, record: DeviationFlowItem) => (
        <Tag color={STATUS_COLORS[record.status]}>{label}</Tag>
      ),
    },
    {
      title: '责任部门',
      dataIndex: 'responsible_department',
      key: 'responsible_department',
      width: 100,
    },
    {
      title: '发生日期',
      dataIndex: 'occurred_date',
      key: 'occurred_date',
      width: 120,
    },
    {
      title: '填报人',
      dataIndex: 'reporter',
      key: 'reporter',
      width: 80,
    },
    {
      title: '剩余天数',
      key: 'days_countdown',
      width: 100,
      render: (_: unknown, record: DeviationFlowItem) => {
        if (record.status === 'completed') {
          return <Tag color="success">已完成({record.completed_days || 0}天)</Tag>
        }
        const remaining = record.remaining_days
        if (remaining === undefined || remaining === null) return '-'
        if (remaining <= 3) return <Tag color="error">仅剩 {remaining} 天</Tag>
        if (remaining <= 7) return <Tag color="warning">{remaining} 天</Tag>
        return <Tag color="blue">{remaining} 天</Tag>
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      fixed: 'right' as const,
      render: (_: unknown, record: DeviationFlowItem) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleView(record)}>
            查看
          </Button>
          {record.status !== 'completed' && (
            <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
              {record.status === 'draft' ? '编辑' : '继续填写'}
            </Button>
          )}
          {record.status === 'draft' && (
            <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record)}>
              删除
            </Button>
          )}
        </Space>
      ),
    },
  ]

  const renderCard = (item: DeviationFlowItem) => {
    const urgencyColor = URGENCY_COLORS[item.urgency_level_label || ''] || 'default'
    const statusColor = STATUS_COLORS[item.status || ''] || 'default'
    const remaining = item.remaining_days
    const isOverdue = remaining !== undefined && remaining !== null && remaining <= 3 && item.status !== 'completed'

    return (
      <div key={item.id} className="deviation-query-card">
        <div className="deviation-query-card-header">
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="deviation-query-card-title">
              <Tag color="blue" style={{ margin: 0, flexShrink: 0 }}>{item.deviation_no}</Tag>
              <span className="deviation-query-card-theme">{item.theme || '无主题'}</span>
            </div>
          </div>
          <Tag color={statusColor} style={{ flexShrink: 0 }}>{item.status_label}</Tag>
        </div>

        <div className="deviation-query-card-body">
          {item.deviation_type_label && (
            <div className="deviation-query-card-row">
              <span className="deviation-query-card-label">偏差类型</span>
              <span className="deviation-query-card-value">{item.deviation_type_label}</span>
            </div>
          )}
          <div className="deviation-query-card-row">
            <span className="deviation-query-card-label">紧急等级</span>
            <span className="deviation-query-card-value">
              <Tag color={urgencyColor} style={{ margin: 0 }}>{item.urgency_level_label || '-'}</Tag>
            </span>
          </div>
          <div className="deviation-query-card-row">
            <span className="deviation-query-card-label">责任部门</span>
            <span className="deviation-query-card-value">{item.responsible_department || '-'}</span>
          </div>
          <div className="deviation-query-card-row">
            <span className="deviation-query-card-label">发生日期</span>
            <span className="deviation-query-card-value">
              {item.occurred_date ? dayjs(item.occurred_date).format('YYYY-MM-DD') : '-'}
            </span>
          </div>
          <div className="deviation-query-card-row">
            <span className="deviation-query-card-label">填报人</span>
            <span className="deviation-query-card-value">{item.reporter || '-'}</span>
          </div>
          {item.status !== 'completed' && remaining !== undefined && remaining !== null && (
            <div className="deviation-query-card-row">
              <span className="deviation-query-card-label">剩余天数</span>
              <span className={`deviation-query-card-value ${isOverdue ? 'danger' : ''}`}>
                {remaining <= 3 ? `${remaining} 天` : `${remaining} 天`}
                {isOverdue && <ClockCircleOutlined style={{ marginLeft: 4, color: '#ef4444' }} />}
              </span>
            </div>
          )}
          {item.status === 'completed' && (
            <div className="deviation-query-card-row">
              <span className="deviation-query-card-label">完成天数</span>
              <span className="deviation-query-card-value">
                <Tag color="success" style={{ margin: 0 }}>{item.completed_days || 0} 天</Tag>
              </span>
            </div>
          )}
        </div>

        <div className="deviation-query-card-footer">
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleView(item)}
            className="deviation-query-card-btn-text"
          >
            查看
          </Button>
          {item.status !== 'completed' && (
            <Button
              size="small"
              type="primary"
              icon={<EditOutlined />}
              onClick={() => handleEdit(item)}
              className="deviation-query-card-btn-text"
            >
              {item.status === 'draft' ? '编辑' : '继续'}
            </Button>
          )}
          {item.status === 'draft' && (
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(item)}
              className="deviation-query-card-btn-text"
            >
              删除
            </Button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="deviation-page">
      <div className="deviation-header">
        <div className="deviation-header-left">
          <h1>
            <FileTextOutlined />
            偏差任务查询
          </h1>
          <p>查看和管理所有偏差任务记录</p>
        </div>
        <div className="deviation-header-right">
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => router.push('/quality/deviation-flow/create')}
            size={isMobile ? 'small' : 'middle'}
          >
            新建偏差
          </Button>
        </div>
      </div>

      <div className="deviation-section-card" style={{ marginBottom: 16 }}>
        <div className="deviation-section-body" style={{ padding: isMobile ? 14 : 20 }}>
          <div className="deviation-query-search">
            <Input
              placeholder="搜索偏差编号/主题"
              value={keyword}
              onChange={e => setKeyword(e.target.value)}
              allowClear
              onPressEnter={handleSearch}
              style={{ flex: isMobile ? '1' : 'auto', minWidth: isMobile ? '100%' : '200px' }}
              suffix={<SearchOutlined style={{ color: '#94a3b8' }} />}
            />
            <Select
              placeholder="状态"
              allowClear
              value={status}
              onChange={v => { setStatus(v); setPage(1) }}
              style={{ flex: isMobile ? '1' : 'auto', minWidth: isMobile ? '100%' : '120px' }}
            >
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <Select.Option key={value} value={value}>{label}</Select.Option>
              ))}
            </Select>
            <Select
              placeholder="偏差类型"
              allowClear
              showSearch
              optionFilterProp="children"
              value={deviationType}
              onChange={v => { setDeviationType(v); setPage(1) }}
              style={{ flex: isMobile ? '1' : 'auto', minWidth: isMobile ? '100%' : '140px' }}
            >
              {DEVIATION_TYPES_OPTIONS.map(opt => (
                <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>
              ))}
            </Select>
            <Select
              placeholder="紧急等级"
              allowClear
              value={urgencyLevel}
              onChange={v => { setUrgencyLevel(v); setPage(1) }}
              style={{ flex: isMobile ? '1' : 'auto', minWidth: isMobile ? '100%' : '100px' }}
            >
              <Select.Option value="normal">一般</Select.Option>
              <Select.Option value="important">重要</Select.Option>
              <Select.Option value="serious">严重</Select.Option>
            </Select>
            <Space>
              <Button
                type="primary"
                icon={<SearchOutlined />}
                onClick={handleSearch}
                size={isMobile ? 'small' : 'middle'}
              >
                搜索
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => loadData()}
                size={isMobile ? 'small' : 'middle'}
              >
                刷新
              </Button>
            </Space>
          </div>
        </div>
      </div>

      {!isMobile && (
        <div className="deviation-section-card" style={{ marginBottom: 16, padding: '12px 20px' }}>
          <Space>
            <Button
              type={viewMode === 'table' ? 'primary' : 'default'}
              icon={<TableOutlined />}
              onClick={() => setViewMode('table')}
              size="small"
            >
              表格
            </Button>
            <Button
              type={viewMode === 'card' ? 'primary' : 'default'}
              icon={<AppstoreOutlined />}
              onClick={() => setViewMode('card')}
              size="small"
            >
              卡片
            </Button>
          </Space>
        </div>
      )}

      <Spin spinning={loading}>
        {viewMode === 'table' && !isMobile ? (
          <div className="deviation-section-card">
            <div className="deviation-section-body" style={{ padding: 0 }}>
              <table className="deviation-query-table">
                <thead>
                  <tr>
                    <th style={{ width: 130 }}>偏差编号</th>
                    <th style={{ width: 200 }}>偏差主题</th>
                    <th style={{ width: 100 }}>偏差类型</th>
                    <th style={{ width: 80 }}>紧急等级</th>
                    <th style={{ width: 100 }}>状态</th>
                    <th style={{ width: 100 }}>责任部门</th>
                    <th style={{ width: 120 }}>发生日期</th>
                    <th style={{ width: 80 }}>填报人</th>
                    <th style={{ width: 100 }}>剩余天数</th>
                    <th style={{ width: 180, position: 'sticky', right: 0, background: '#f8fafc' }}>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {data.length > 0 ? (
                    data.map((item: any) => {
                      const urgencyColor = URGENCY_COLORS[item.urgency_level_label || ''] || 'default'
                      const statusColor = STATUS_COLORS[item.status || ''] || 'default'
                      const remaining = item.remaining_days
                      return (
                        <tr key={item.id}>
                          <td><Tag color="blue" style={{ margin: 0 }}>{item.deviation_no}</Tag></td>
                          <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.theme || '-'}</td>
                          <td>{item.deviation_type_label || '-'}</td>
                          <td><Tag color={urgencyColor} style={{ margin: 0 }}>{item.urgency_level_label || '-'}</Tag></td>
                          <td><Tag color={statusColor} style={{ margin: 0 }}>{item.status_label}</Tag></td>
                          <td>{item.responsible_department || '-'}</td>
                          <td>{item.occurred_date ? dayjs(item.occurred_date).format('YYYY-MM-DD') : '-'}</td>
                          <td>{item.reporter || '-'}</td>
                          <td>
                            {item.status === 'completed' ? (
                              <Tag color="success" style={{ margin: 0 }}>{item.completed_days || 0}天</Tag>
                            ) : remaining !== undefined && remaining !== null ? (
                              <Tag color={remaining <= 3 ? 'error' : remaining <= 7 ? 'warning' : 'blue'} style={{ margin: 0 }}>
                                {remaining} 天
                              </Tag>
                            ) : '-'}
                          </td>
                          <td style={{ position: 'sticky', right: 0, background: '#fff' }}>
                            <Space size="small">
                              <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleView(item)}>查看</Button>
                              {item.status !== 'completed' && (
                                <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(item)}>
                                  {item.status === 'draft' ? '编辑' : '继续'}
                                </Button>
                              )}
                              {item.status === 'draft' && (
                                <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(item)}>删除</Button>
                              )}
                            </Space>
                          </td>
                        </tr>
                      )
                    })
                  ) : (
                    <tr>
                      <td colSpan={10} style={{ textAlign: 'center', padding: '40px 0' }}>
                        {loading ? '' : <Empty description="暂无数据" />}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <>
            <div className="deviation-query-card-grid">
              {data.length > 0 ? (
                data.map(renderCard)
              ) : (
                <div className="deviation-empty-state">
                  <Empty description="暂无数据" />
                </div>
              )}
            </div>
          </>
        )}

        <div className="deviation-query-pagination">
          <span style={{ color: '#6b7280', fontSize: 13 }}>
            共 {total} 条
          </span>
          <Space>
            <Button
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
              size={isMobile ? 'small' : 'middle'}
            >
              上一页
            </Button>
            <span style={{ color: '#1f2937', fontWeight: 600, fontSize: 14 }}>
              {page} / {Math.max(1, Math.ceil(total / pageSize))}
            </span>
            <Button
              disabled={page * pageSize >= total}
              onClick={() => setPage(page + 1)}
              size={isMobile ? 'small' : 'middle'}
            >
              下一页
            </Button>
          </Space>
        </div>
      </Spin>
    </div>
  )
}
