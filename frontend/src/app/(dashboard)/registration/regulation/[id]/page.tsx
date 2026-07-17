'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { Spin, Button, Tag, App } from 'antd'
import {
  ArrowLeftOutlined, LinkOutlined, FileTextOutlined,
  WarningOutlined, CheckCircleOutlined, ClockCircleOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import Link from 'next/link'
import { DocumentDetail, fetchDocumentDetail } from '@/lib/api/client/regulatory-tracker'
import { markDocumentRead } from '@/actions/regulatory-tracker'

// 影响等级配置
const IMPACT_CONFIG: Record<string, { color: string; bg: string; label: string }> = {
  high: { color: '#dc2626', bg: '#fef2f2', label: '高影响' },
  medium: { color: '#d97706', bg: '#fffbeb', label: '中影响' },
  low: { color: '#475569', bg: '#f8fafc', label: '低影响' },
  none: { color: '#94a3b8', bg: '#f8fafc', label: '无影响' },
}

// 结构化影响评估类型
interface ImpactAssessment {
  regulation_type?: string
  impact_level?: 'high' | 'medium' | 'low' | 'none'
  relevance_level?: 'direct' | 'indirect' | 'unrelated'
  lifecycle_impacts?: Array<{ area: string; affected: boolean; reason?: string }>
  departments?: string[]
  ctd_sections?: string[]
  recommended_actions?: string[]
  notification_required?: boolean
  evidence?: string[]
  evidence_excerpts?: string[]
  focus_required?: boolean
  archive_recommended?: boolean
  confidence?: number
}

// 文件要点维度
const KEY_POINT_DIMENSIONS = [
  { key: '药品研制和注册管理', areas: ['药品研发', '注册申报', '审评审批'] },
  { key: '药品生产质量管理', areas: ['生产制造', '工艺验证', '技术转移', '质量控制'] },
  { key: '药品经营和使用监管', areas: [] },
  { key: '药品上市后监管', areas: ['变更管理', '持续改进', '退市管理'] },
  { key: '法律责任', areas: [] },
]

// 部门列表
const DEPARTMENTS = ['注册', 'QA', 'QC', '研发', '生产', '验证']

export default function RegulatoryDocumentDetailPage() {
  const { message } = App.useApp()
  const params = useParams()
  const docId = params.id as string

  const [doc, setDoc] = useState<DocumentDetail | null>(null)
  const [loading, setLoading] = useState(true)

  const loadDetail = async () => {
    setLoading(true)
    try {
      const data = await fetchDocumentDetail(docId)
      setDoc(data)
      // 自动标记已读
      if (data.isNew) {
        try {
          await markDocumentRead(docId)
        } catch { /* ignore */ }
      }
    } catch {
      message.error('加载法规详情失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadDetail() }, [docId])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Spin size="large" />
      </div>
    )
  }

  if (!doc) {
    return (
      <div className="text-center py-20 text-gray-500">
        <FileTextOutlined style={{ fontSize: 48, marginBottom: 16 }} />
        <p>法规文档不存在</p>
        <Link href="/registration/regulation/list">
          <Button type="link">返回列表</Button>
        </Link>
      </div>
    )
  }

  // 解析结构化影响评估数据
  const getImpactAssessment = (): ImpactAssessment | null => {
    if (!doc.aiKeyPoints) return null
    if (Array.isArray(doc.aiKeyPoints)) return null
    if (typeof doc.aiKeyPoints !== 'object') return null
    return doc.aiKeyPoints as unknown as ImpactAssessment
  }

  const impactData = getImpactAssessment()
  const impactLevel = impactData?.impact_level || 'none'
  const impactConfig = IMPACT_CONFIG[impactLevel] || IMPACT_CONFIG.none

  // 判断 AI 状态
  const isAnalyzed = doc.aiAnalysisStatus === 'completed' && impactData
  const isFailed = doc.aiAnalysisStatus === 'failed'
  const isPending = !doc.aiAnalysisStatus || doc.aiAnalysisStatus === 'pending' || doc.aiAnalysisStatus === 'analyzing'

  // 获取相关部门影响
  const getDepartmentImpacts = () => {
    if (!impactData?.lifecycle_impacts) return {}
    const deptMap: Record<string, Array<{ area: string; reason?: string }>> = {}
    
    // 简化的部门映射
    const areaToDept: Record<string, string[]> = {
      '药品研发': ['研发'],
      '注册申报': ['注册'],
      '审评审批': ['注册'],
      '生产制造': ['生产'],
      '工艺验证': ['生产', '验证'],
      '技术转移': ['研发', '生产'],
      '质量控制': ['QA', 'QC'],
      '变更管理': ['注册', 'QA', '生产'],
      '持续改进': ['生产', 'QA'],
      '退市管理': ['注册', 'QA'],
    }

    impactData.lifecycle_impacts.forEach(item => {
      if (item.affected) {
        const depts = areaToDept[item.area] || []
        depts.forEach(dept => {
          if (!deptMap[dept]) deptMap[dept] = []
          deptMap[dept].push({ area: item.area, reason: item.reason })
        })
      }
    })

    return deptMap
  }

  // 获取文件要点
  const getKeyPoints = () => {
    if (!impactData?.lifecycle_impacts) return {}
    const result: Record<string, Array<{ area: string; affected: boolean; reason?: string }>> = {}
    
    KEY_POINT_DIMENSIONS.forEach(dim => {
      const impacts = impactData.lifecycle_impacts!.filter(item => 
        dim.areas.includes(item.area)
      )
      if (impacts.length > 0) {
        result[dim.key] = impacts
      }
    })

    return result
  }

  const deptImpacts = getDepartmentImpacts()
  const keyPoints = getKeyPoints()

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      {/* 顶部导航 */}
      <div className="flex items-center justify-between">
        <Link href="/registration/regulation/list">
          <Button icon={<ArrowLeftOutlined />}>返回列表</Button>
        </Link>
        {doc.originalUrl && (
          <Button icon={<LinkOutlined />} href={doc.originalUrl} target="_blank">
            查看原文
          </Button>
        )}
      </div>

      {/* 1. 顶部结论区 */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h1 className="text-xl font-semibold text-gray-900 mb-4">{doc.title}</h1>
        
        <div className="flex items-center gap-4 mb-4">
          <Tag color={impactConfig.color} style={{ backgroundColor: impactConfig.bg }}>
            {impactConfig.label}
          </Tag>
          {impactData?.regulation_type && (
            <span className="text-sm text-gray-500">{impactData.regulation_type}</span>
          )}
          <span className="text-sm text-gray-400">
            {doc.sourceName || 'CDE'} · {doc.publishDate ? dayjs(doc.publishDate).format('YYYY-MM-DD') : ''}
          </span>
        </div>

        {isAnalyzed && doc.aiSummary && (
          <div className="text-gray-700 leading-relaxed">
            <span className="text-gray-400">AI判断：</span>{doc.aiSummary}
          </div>
        )}

        {isPending && (
          <div className="text-gray-400 flex items-center gap-2">
            <ClockCircleOutlined />
            该历史法规尚未完成 AI 回填，将在 Task7 统一处理。
          </div>
        )}

        {isFailed && (
          <div className="text-gray-400 flex items-center gap-2">
            <WarningOutlined />
            AI 评估失败，V1 暂不支持手动重新分析。
          </div>
        )}
      </div>

      {/* 以下内容仅在已分析时显示 */}
      {isAnalyzed && impactData && (
        <>
          {/* 2. 法规指南解读 */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">法规指南解读</h2>
            
            <div className="space-y-3">
              <div>
                <span className="text-sm text-gray-500">文件适用范围：</span>
                <span className="text-gray-700 ml-2">
                  {impactData.regulation_type || '未指定'}
                </span>
              </div>
              
              <div>
                <span className="text-sm text-gray-500">与原料药企业关系：</span>
                <span className="text-gray-700 ml-2">
                  {impactData.relevance_level === 'direct' && '直接相关'}
                  {impactData.relevance_level === 'indirect' && '间接相关'}
                  {impactData.relevance_level === 'unrelated' && '无关'}
                  {!impactData.relevance_level && '未评估'}
                </span>
              </div>

              <div>
                <span className="text-sm text-gray-500">适用岗位：</span>
                <span className="text-gray-700 ml-2">
                  {impactData.departments && impactData.departments.length > 0
                    ? impactData.departments.join('、')
                    : '无特定岗位影响'}
                </span>
              </div>
            </div>
          </div>

          {/* 3. 工作建议 */}
          {impactData.recommended_actions && impactData.recommended_actions.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">工作建议</h2>
              
              <div className="space-y-4">
                {DEPARTMENTS.map(dept => {
                  const impacts = deptImpacts[dept]
                  if (!impacts || impacts.length === 0) return null
                  
                  return (
                    <div key={dept} className="border-l-2 border-blue-200 pl-4">
                      <div className="font-medium text-gray-800 mb-2">{dept}</div>
                      <ul className="space-y-1">
                        {impacts.map((item, idx) => (
                          <li key={idx} className="text-sm text-gray-600">
                            <span className="text-gray-400">{item.area}：</span>
                            {item.reason || '建议评估影响'}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )
                })}

                {/* 通用建议 */}
                <div className="border-l-2 border-gray-200 pl-4">
                  <div className="font-medium text-gray-800 mb-2">通用建议</div>
                  <ul className="space-y-1">
                    {impactData.recommended_actions.map((action, idx) => (
                      <li key={idx} className="text-sm text-gray-600">
                        {action}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* 4. 文件要点总结 */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">文件要点总结</h2>
            
            <div className="space-y-3">
              {KEY_POINT_DIMENSIONS.map(dim => {
                const impacts = keyPoints[dim.key]
                const hasAffected = impacts?.some(i => i.affected)
                
                return (
                  <div key={dim.key} className="flex items-start gap-3">
                    <div className="w-40 flex-shrink-0 text-sm text-gray-500">{dim.key}</div>
                    <div className="flex-1">
                      {hasAffected ? (
                        <div className="space-y-1">
                          {impacts?.filter(i => i.affected).map((item, idx) => (
                            <div key={idx} className="text-sm text-gray-700">
                              {item.area}：{item.reason || '有影响'}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <span className="text-sm text-gray-300">不涉及</span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* 5. 影响分析 */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">影响分析</h2>
            
            <div className="space-y-4">
              {/* 生命周期影响 */}
              {impactData.lifecycle_impacts && impactData.lifecycle_impacts.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-gray-700 mb-2">生命周期影响</div>
                  <div className="grid grid-cols-2 gap-2">
                    {impactData.lifecycle_impacts.filter(i => i.affected).map((item, idx) => (
                      <div key={idx} className="text-sm text-gray-600 flex items-center gap-2">
                        <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 12 }} />
                        <span>{item.area}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 影响部门 */}
              {impactData.departments && impactData.departments.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-gray-700 mb-2">影响部门</div>
                  <div className="flex flex-wrap gap-2">
                    {impactData.departments.map((dept, idx) => (
                      <Tag key={idx} className="text-xs">{dept}</Tag>
                    ))}
                  </div>
                </div>
              )}

              {/* CTD 章节 */}
              {impactData.ctd_sections && impactData.ctd_sections.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-gray-700 mb-2">CTD 章节</div>
                  <div className="flex flex-wrap gap-2">
                    {impactData.ctd_sections.map((section, idx) => (
                      <Tag key={idx} color="blue" className="text-xs">{section}</Tag>
                    ))}
                  </div>
                </div>
              )}

              {/* 分析依据 */}
              {impactData.evidence && impactData.evidence.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-gray-700 mb-2">分析依据</div>
                  <div className="bg-gray-50 rounded p-3">
                    <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
                      {impactData.evidence.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* 分析时间 */}
              {doc.aiAnalyzedAt && (
                <div className="text-xs text-gray-400 pt-2 border-t">
                  分析时间：{dayjs(doc.aiAnalyzedAt).format('YYYY-MM-DD HH:mm:ss')}
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* 正文内容 */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">正文内容</h2>
        {doc.detailText ? (
          <div className="text-gray-600 leading-relaxed whitespace-pre-wrap max-h-96 overflow-y-auto">
            {doc.detailText}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400">暂无正文内容</div>
        )}
      </div>

      {/* 相关法规 */}
      {doc.relatedDocuments && doc.relatedDocuments.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">相关法规</h2>
          <div className="space-y-2">
            {doc.relatedDocuments.map((item) => (
              <div key={item.id} className="flex items-center gap-2 py-1">
                <Link
                  href={`/registration/regulation/${item.id}`}
                  className="text-blue-600 hover:text-blue-800"
                >
                  {item.title}
                </Link>
                <span className="text-xs text-gray-400">
                  {item.publishDate ? dayjs(item.publishDate).format('YYYY-MM-DD') : ''}
                  {item.classification && ` · ${item.classification}`}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
