'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { Card, Row, Col, Typography, Button, Space, Spin } from 'antd'
import {
  BookOutlined,
  ProjectOutlined,
  FileSearchOutlined,
  SafetyCertificateOutlined,
  GlobalOutlined,
  FileTextOutlined,
  AuditOutlined,
  RightOutlined,
  ReloadOutlined,
  AppstoreOutlined,
  SolutionOutlined,
  MessageOutlined,
  ExperimentOutlined,
} from '@ant-design/icons'
import {
  fetchLedgerSummary,
  type LedgerSummary,
} from '@/lib/api/client/registration-ledger'

const { Title, Text, Paragraph } = Typography

interface StatCard {
  key: string
  title: string
  value: number
  description: string
  href: string
}

interface EntryItem {
  key: string
  title: string
  description: string
  icon: React.ReactNode
  href: string
}

export default function RegistrationPage() {
  const [summary, setSummary] = useState<LedgerSummary | null>(null)
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await fetchLedgerSummary()
      setSummary(data)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const statCards: StatCard[] = [
    {
      key: 'domestic',
      title: '国内已获批',
      value: summary?.domestic_count ?? 0,
      description: '国内获批品种数量',
      href: '/registration/ledger?type=domestic',
    },
    {
      key: 'overseas',
      title: '国外已获批',
      value: summary?.overseas_count ?? 0,
      description: `覆盖 ${summary?.overseas_countries ?? 0} 个国家/地区`,
      href: '/registration/ledger?type=overseas',
    },
    {
      key: 'international',
      title: '国际关联审评',
      value: summary?.international_review_count ?? 0,
      description: '国际关联审评品种数',
      href: '/registration/ledger?type=international',
    },
    {
      key: 'copp',
      title: 'COPP 证书',
      value: summary?.copp_count ?? 0,
      description: 'COPP 证书数量',
      href: '/registration/ledger?type=copp',
    },
    {
      key: 'wc',
      title: 'WC 证书',
      value: summary?.wc_count ?? 0,
      description: 'WC 证书数量',
      href: '/registration/ledger?type=wc',
    },
    {
      key: 'reviewing',
      title: '审评中',
      value: summary?.reviewing_count ?? 0,
      description: '正在审评的品种数',
      href: '/registration/ledger?type=reviewing',
    },
  ]

  const businessEntries: EntryItem[] = [
    {
      key: 'ledger',
      title: '注册台账',
      description: '管理注册证书和审评信息，支持 Excel 导入导出',
      icon: <BookOutlined />,
      href: '/registration/ledger',
    },
    {
      key: 'review',
      title: '审评进度查询',
      description: '查看各品种审评节点进度',
      icon: <FileSearchOutlined />,
      href: '/registration/review',
    },
    {
      key: 'projects',
      title: '注册项目管理',
      description: '管理注册项目、跟踪项目进度',
      icon: <ProjectOutlined />,
      href: '/registration/projects',
    },
    {
      key: 'regulation',
      title: '法规跟踪',
      description: '跟踪国内外法规动态变化',
      icon: <GlobalOutlined />,
      href: '/registration/regulation',
    },
    {
      key: 'dossier-writer',
      title: '申报资料撰写',
      description: '管理品种资料、模板、章节素材和导出文件',
      icon: <FileTextOutlined />,
      href: '/registration/dossier-writer',
    },
    {
      key: 'validation-audit',
      title: '验证文件审核',
      description: '验证文件审核与合规性检查',
      icon: <AuditOutlined />,
      href: '/registration/validation-audit',
    },
    {
      key: 'authorization-letter',
      title: '授权书管理',
      description: '生成和管理授权信，支持按品种快速生成',
      icon: <SolutionOutlined />,
      href: '/registration/authorization-letter',
    },
    {
      key: 'supplementary-reply',
      title: '发补回复',
      description: '基于 CDE 通知函自动生成发补回复草稿',
      icon: <MessageOutlined />,
      href: '/registration/supplementary-reply',
    },
    {
      key: 'reference-standard',
      title: '对照物质说明表',
      description: '管理对照物质信息和 COA，生成说明表文件',
      icon: <ExperimentOutlined />,
      href: '/registration/reference-standard',
    },
  ]

  const ledgerShortcuts: EntryItem[] = [
    {
      key: 'domestic',
      title: '国内已获批',
      description: '查看国内已获批品种信息',
      icon: <SafetyCertificateOutlined />,
      href: '/registration/ledger?type=domestic',
    },
    {
      key: 'overseas',
      title: '国外已获批',
      description: '查看海外获批品种及证书信息',
      icon: <GlobalOutlined />,
      href: '/registration/ledger?type=overseas',
    },
    {
      key: 'international',
      title: '国际关联审评',
      description: '查看国际关联审评品种进展',
      icon: <GlobalOutlined />,
      href: '/registration/ledger?type=international',
    },
    {
      key: 'copp',
      title: 'COPP 证书',
      description: '管理 COPP 证书信息',
      icon: <SafetyCertificateOutlined />,
      href: '/registration/ledger?type=copp',
    },
    {
      key: 'wc',
      title: 'WC 证书',
      description: '管理 WC 证书信息',
      icon: <SafetyCertificateOutlined />,
      href: '/registration/ledger?type=wc',
    },
    {
      key: 'reviewing',
      title: '审评中',
      description: '查看正在审评中的品种',
      icon: <FileSearchOutlined />,
      href: '/registration/ledger?type=reviewing',
    },
  ]

  return (
    <div className="space-y-6">
      {/* 顶部标题区 */}
      <div className="flex items-center justify-between">
        <div>
          <Title level={4} style={{ marginBottom: 4, color: 'var(--color-charcoal)' }}>
            注册管理
          </Title>
          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            汇总注册台账、审评进展、证书维护及申报资料相关功能
          </Paragraph>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
            刷新
          </Button>
          <Link href="/registration/ledger">
            <Button type="primary" icon={<BookOutlined />}>
              进入注册台账
            </Button>
          </Link>
        </Space>
      </div>

      {/* 统计看板区 */}
      <Spin spinning={loading}>
        <Row gutter={[16, 16]}>
          {statCards.map((card) => (
            <Col xs={12} sm={8} lg={4} key={card.key}>
              <Link href={card.href} style={{ display: 'block' }}>
                <Card
                  hoverable
                  styles={{ body: { padding: '20px' } }}
                  style={{ height: '100%' }}
                >
                  <div className="flex flex-col h-full">
                    <Text type="secondary" style={{ fontSize: 13, marginBottom: 8 }}>
                      {card.title}
                    </Text>
                    <Title level={2} style={{ marginBottom: 8, color: 'var(--color-charcoal)' }}>
                      {card.value}
                    </Title>
                    <Text type="secondary" style={{ fontSize: 12, flex: 1 }}>
                      {card.description}
                    </Text>
                    <div style={{ marginTop: 12 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        查看详情 <RightOutlined style={{ fontSize: 10 }} />
                      </Text>
                    </div>
                  </div>
                </Card>
              </Link>
            </Col>
          ))}
        </Row>
      </Spin>

      {/* 业务功能入口区 */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <AppstoreOutlined style={{ color: 'var(--color-primary)', fontSize: 16 }} />
          <Title level={5} style={{ marginBottom: 0, color: 'var(--color-charcoal)' }}>
            业务功能
          </Title>
        </div>
        <Row gutter={[16, 16]}>
          {businessEntries.map((entry) => (
            <Col xs={24} sm={12} lg={8} key={entry.key}>
              <Link href={entry.href} style={{ display: 'block' }}>
                <Card
                  hoverable
                  styles={{ body: { padding: '16px 20px' } }}
                  style={{ height: '100%' }}
                >
                  <div className="flex items-start gap-3">
                    <div
                      style={{
                        width: 36,
                        height: 36,
                        borderRadius: 8,
                        backgroundColor: 'var(--color-surface)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 16,
                        color: 'var(--color-primary)',
                        flexShrink: 0,
                      }}
                    >
                      {entry.icon}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <Text strong style={{ fontSize: 14, display: 'block', marginBottom: 4 }}>
                        {entry.title}
                      </Text>
                      <Text type="secondary" style={{ fontSize: 12, lineHeight: 1.5 }}>
                        {entry.description}
                      </Text>
                    </div>
                  </div>
                </Card>
              </Link>
            </Col>
          ))}
        </Row>
      </div>

      {/* 台账分类快捷入口区 */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <BookOutlined style={{ color: 'var(--color-primary)', fontSize: 16 }} />
          <Title level={5} style={{ marginBottom: 0, color: 'var(--color-charcoal)' }}>
            台账分类
          </Title>
        </div>
        <Row gutter={[16, 16]}>
          {ledgerShortcuts.map((entry) => (
            <Col xs={12} sm={8} lg={4} key={entry.key}>
              <Link href={entry.href} style={{ display: 'block' }}>
                <Card
                  hoverable
                  styles={{ body: { padding: '16px' } }}
                  style={{ height: '100%', textAlign: 'center' }}
                >
                  <div
                    style={{
                      fontSize: 24,
                      color: 'var(--color-primary)',
                      marginBottom: 8,
                    }}
                  >
                    {entry.icon}
                  </div>
                  <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                    {entry.title}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {entry.description}
                  </Text>
                </Card>
              </Link>
            </Col>
          ))}
        </Row>
      </div>

      {/* 底部提示 */}
      {summary && summary.domestic_count === 0 && summary.overseas_count === 0 && (
        <div style={{ textAlign: 'center', padding: '16px 0' }}>
          <Text type="secondary" style={{ fontSize: 13 }}>
            当前台账暂无记录，可进入{' '}
            <Link href="/registration/ledger" style={{ color: 'var(--color-primary)' }}>
              注册台账
            </Link>{' '}
            进行维护
          </Text>
        </div>
      )}
    </div>
  )
}
