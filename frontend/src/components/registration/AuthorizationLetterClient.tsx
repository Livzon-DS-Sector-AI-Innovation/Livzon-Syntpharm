'use client'

import { useEffect, useState } from 'react'
import { useQuery, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import { DataUnavailable } from '@/components/common/DataUnavailable'
import { Table, Input, Select, App, Modal, Form, Upload, Radio, Drawer, Spin, Empty, Popconfirm, Pagination } from 'antd'
import type { UploadFile } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { UploadOutlined, SearchOutlined } from '@ant-design/icons'
import {
  AuthorizationLetterListItem,
  AuthorizationLetterFilterOptions,
  AuthorizationLetterTrail,
  ProductInfo,
} from '@/types/registration'
import {
  fetchAuthorizationLetters,
  fetchAuthorizationLetterDownloadUrl,
  fetchAuthorizationLetterFilterOptions,
  fetchAuthorizationLetterTrails,
} from '@/lib/api/client/registration'
import { generateAuthorizationLetter, deleteAuthorizationLetter } from '@/actions/registration'
import { RegistrationPageHeader } from './RegistrationPageHeader'
import ui from './registration-ui.module.css'
import styles from './authorization-letter.module.css'
import { IconFile, IconPlus, IconTrash, RegSvg } from './registration-icons'
import dayjs from 'dayjs'

const IconLock = (
  <RegSvg size={15}>
    <rect x="3" y="11" width="18" height="11" rx="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </RegSvg>
)
const IconEmptySearch = (
  <RegSvg size={26}>
    <circle cx="11" cy="11" r="8" />
    <path d="m21 21-4.35-4.35" />
  </RegSvg>
)

interface Query {
  keyword: string
  product?: string
  year?: number
  page: number
  pageSize: number
}

const DEFAULT_QUERY: Query = { keyword: '', product: undefined, year: undefined, page: 1, pageSize: 20 }

interface AuthorizationLetterClientProps {
  initialLetters: AuthorizationLetterListItem[]
  initialTotal: number
  initialFilterOptions: AuthorizationLetterFilterOptions
  products: ProductInfo[]
}

export default function AuthorizationLetterClient({
  initialLetters,
  initialTotal,
  initialFilterOptions,
  products,
}: AuthorizationLetterClientProps) {
  const { message } = App.useApp()
  const queryClient = useQueryClient()

  // 筛选输入态（关键词输入框即时编辑，300ms 防抖后提交查询）
  const [keywordInput, setKeywordInput] = useState('')
  const [query, setQuery] = useState<Query>(DEFAULT_QUERY)

  useEffect(() => {
    const timer = setTimeout(() => {
      const kw = keywordInput.trim()
      setQuery(prev =>
        prev.keyword === kw && prev.page === 1 ? prev : { ...prev, keyword: kw, page: 1 }
      )
    }, 300)
    return () => clearTimeout(timer)
  }, [keywordInput])

  const applyProduct = (v?: string) =>
    setQuery(prev => ({ ...prev, product: v, page: 1 }))
  const applyYear = (v?: number) =>
    setQuery(prev => ({ ...prev, year: v, page: 1 }))
  const resetFilter = () => {
    setKeywordInput('')
    setQuery(DEFAULT_QUERY)
  }

  // 留痕抽屉
  const [selected, setSelected] = useState<AuthorizationLetterListItem | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  // 生成弹窗
  const [generateModalOpen, setGenerateModalOpen] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [form] = Form.useForm()
  const [templateSource, setTemplateSource] = useState<'builtin' | 'custom'>('builtin')
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [replacements, setReplacements] = useState<Array<{ old: string; new: string }>>([{ old: '', new: '' }])

  const isInitialQuery =
    query.page === 1 &&
    query.pageSize === DEFAULT_QUERY.pageSize &&
    !query.keyword &&
    !query.product &&
    !query.year

  const lettersQuery = useQuery({
    queryKey: ['authorization-letters', query],
    queryFn: () =>
      fetchAuthorizationLetters({
        keyword: query.keyword || undefined,
        product_name: query.product,
        year: query.year,
        page: query.page,
        page_size: query.pageSize,
      }),
    placeholderData: keepPreviousData,
    initialData: isInitialQuery ? { items: initialLetters, total: initialTotal } : undefined,
  })
  const letters = lettersQuery.data?.items ?? []
  const total = lettersQuery.data?.total ?? 0

  const optionsQuery = useQuery({
    queryKey: ['authorization-letter-filter-options'],
    queryFn: fetchAuthorizationLetterFilterOptions,
    initialData: initialFilterOptions,
  })
  const filterOptions = optionsQuery.data ?? initialFilterOptions

  const trailsQuery = useQuery({
    queryKey: ['authorization-letter-trails', selected?.id],
    queryFn: () => fetchAuthorizationLetterTrails(selected!.id),
    enabled: !!selected && drawerOpen,
  })
  const trails = trailsQuery.data ?? []

  const refreshAll = () => {
    void queryClient.invalidateQueries({ queryKey: ['authorization-letters'] })
    void queryClient.invalidateQueries({ queryKey: ['authorization-letter-filter-options'] })
  }

  // ── 行为 ──

  const openTrailDrawer = (record: AuthorizationLetterListItem) => {
    setSelected(record)
    setDrawerOpen(true)
  }

  const handleGenerate = async () => {
    try {
      const values = await form.validateFields()

      if (templateSource === 'custom' && fileList.length === 0) {
        message.error('请上传模板文件')
        return
      }

      setGenerating(true)

      const formData = new FormData()
      if (templateSource === 'custom') {
        formData.append('template', fileList[0].originFileObj as File)
        const validReplacements = replacements.filter(r => r.old && r.new)
        if (validReplacements.length > 0) {
          formData.append('replacements', JSON.stringify(validReplacements))
        }
      } else {
        formData.append('template_variant', 'zh')
      }

      const result = await generateAuthorizationLetter(formData, {
        product_name: values.product_name,
        registration_number: values.registration_number,
        preparation_unit: values.preparation_unit,
        preparation_name: values.preparation_name,
        administration_route: values.administration_route,
        remarks: values.remarks,
      })

      if (result.success) {
        message.success(`${result.message}，已自动记入留痕`)
        setGenerateModalOpen(false)
        form.resetFields()
        setFileList([])
        setTemplateSource('builtin')
        setReplacements([{ old: '', new: '' }])
        refreshAll()
      } else {
        message.error(result.message)
      }
    } catch (err: unknown) {
      message.error((err instanceof Error ? err.message : null) || '生成失败')
    } finally {
      setGenerating(false)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteAuthorizationLetter(id)
      message.success('删除成功')
      if (selected?.id === id) setDrawerOpen(false)
      refreshAll()
    } catch (err: unknown) {
      message.error((err instanceof Error ? err.message : null) || '删除失败')
    }
  }

  const handleDownload = async (record: AuthorizationLetterListItem) => {
    if (!record.output_file_name) {
      message.warning('该授权书暂无可用文件')
      return
    }
    const url = await fetchAuthorizationLetterDownloadUrl(record.id)
    const link = document.createElement('a')
    link.href = url
    link.download = record.output_file_name
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    message.success('已开始下载，已自动记入留痕')
    // 下载动作已写入留痕：刷新该记录的留痕时间线（若抽屉正开着同一条记录）
    void queryClient.invalidateQueries({ queryKey: ['authorization-letter-trails', record.id] })
  }

  const handleProductChange = (value: string) => {
    form.setFieldsValue({
      product_name: value,
      registration_number: products.find(p => p.product_name === value)?.registration_number || '',
    })
  }

  // ── 表格列（列宽与对齐按原型：首列左、末列右、中间居中） ──

  const columns: ColumnsType<AuthorizationLetterListItem> = [
    {
      title: '产品名称',
      dataIndex: 'product_name',
      key: 'product_name',
      width: '15%',
      align: 'left',
      render: (v: string) => <span className={styles.pName}>{v}</span>,
    },
    {
      title: '登记号',
      dataIndex: 'registration_number',
      key: 'registration_number',
      width: '14%',
      align: 'center',
      render: (v: string) => <span className={styles.code}>{v}</span>,
    },
    {
      title: '制剂单位',
      dataIndex: 'preparation_unit',
      key: 'preparation_unit',
      width: '13%',
      align: 'center',
    },
    {
      title: '制剂名称',
      dataIndex: 'preparation_name',
      key: 'preparation_name',
      width: '15%',
      align: 'center',
    },
    {
      title: '给药途径',
      dataIndex: 'administration_route',
      key: 'administration_route',
      width: '9%',
      align: 'center',
      render: (v: string) => <span className={ui.tagInfo}>{v}</span>,
    },
    {
      title: '生成时间 / 生成人',
      key: 'created_at',
      width: '18%',
      align: 'center',
      render: (_, r) => (
        <div>
          <div className={styles.genTime}>{dayjs(r.created_at).format('YYYY-MM-DD HH:mm')}</div>
          <div className={styles.genBy}>{r.created_by_name ? `${r.created_by_name} 生成` : '—'}</div>
        </div>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: '16%',
      align: 'right',
      render: (_, record) => (
        <div className={styles.opGroup}>
          <button type="button" className={styles.opLink} onClick={() => void handleDownload(record)}>
            下载
          </button>
          <button type="button" className={styles.opLinkGray} onClick={() => openTrailDrawer(record)}>
            记录
          </button>
          <Popconfirm
            title="删除后不可恢复，确定删除该授权书记录？"
            okText="确定"
            cancelText="取消"
            okButtonProps={{ danger: true }}
            onConfirm={() => void handleDelete(record.id)}
          >
            <button type="button" className={styles.opDel} title="删除">
              {IconTrash}
            </button>
          </Popconfirm>
        </div>
      ),
    },
  ]

  return (
    <div className={ui.regUi}>
      <RegistrationPageHeader
        icon={IconFile}
        title="授权书管理"
        sub="按品种为制剂公司生成授权书，支持下载与归档"
        actions={
          <button type="button" className={ui.btnPrimary} onClick={() => setGenerateModalOpen(true)}>
            {IconPlus}
            生成授权书
          </button>
        }
      />

      <div className={ui.panel}>
        {/* 筛选区：关键词 + 品种 + 年份（可叠加），重置恢复全量 */}
        <div className={styles.toolbar}>
          <div className={styles.toolbarGroup}>
            <Input
              placeholder="搜索：产品名称 / 制剂单位 / 制剂名称"
              prefix={<SearchOutlined style={{ color: 'var(--ink-3)' }} />}
              value={keywordInput}
              onChange={e => setKeywordInput(e.target.value)}
              style={{ width: 280 }}
              allowClear
            />
            <Select
              placeholder="全部品种"
              value={query.product}
              onChange={v => applyProduct(v)}
              style={{ minWidth: 160 }}
              allowClear
              showSearch
              options={(filterOptions.products ?? []).map(p => ({ label: p, value: p }))}
            />
            <Select
              placeholder="全部年份"
              value={query.year}
              onChange={v => applyYear(v)}
              style={{ minWidth: 120 }}
              allowClear
              options={(filterOptions.years ?? []).map(y => ({ label: `${y}`, value: y }))}
            />
            <button type="button" className={ui.btn} onClick={resetFilter}>
              重置
            </button>
          </div>
          <div className={styles.toolbarRight}>
            <span className={styles.cntChip}>共 {total} 条</span>
            <span className={styles.toolbarHint}>点「记录」查看该授权书的生成与下载留痕</span>
          </div>
        </div>

        <div className={`${ui.tableWrap} ${styles.tableStd}`}>
          <Table
            columns={columns}
            dataSource={letters}
            rowKey="id"
            loading={lettersQuery.isPending}
            pagination={false}
            tableLayout="fixed"
            size="middle"
            locale={{
              emptyText: lettersQuery.isError ? (
                <DataUnavailable compact onRetry={() => void lettersQuery.refetch()} />
              ) : (
                <div className={styles.empty}>
                  <div className={styles.emptyIco}>{IconEmptySearch}</div>
                  <div className={styles.emptyT1}>没有符合条件的授权书</div>
                  <div className={styles.emptyT2}>试试放宽筛选条件，或点右上角「生成授权书」新建</div>
                </div>
              ),
            }}
          />
        </div>

        <div className={styles.tableFoot}>
          <span className={styles.totalText}>共 {total} 条</span>
          <Pagination
            current={query.page}
            pageSize={query.pageSize}
            total={total}
            onChange={p => setQuery(prev => ({ ...prev, page: p }))}
            showSizeChanger={false}
          />
        </div>
      </div>

      {/* 留痕抽屉 */}
      <Drawer
        size={520}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false)
          setSelected(null)
        }}
        title={
          selected && (
            <div>
              <div className={styles.drawerName}>
                {selected.product_name}
                <span className={ui.tagInfo}>{selected.registration_number}</span>
              </div>
              <div className={styles.drawerSub}>
                {selected.preparation_unit} · {selected.preparation_name}
              </div>
            </div>
          )
        }
        styles={{ body: { padding: 0 } }}
      >
        <div className={`${ui.tokenScope} ${styles.drawerBody}`}>
          {selected && (
            <>
              <div className={styles.kvGrid}>
                <div className={styles.kv}>
                  <div className={styles.kvK}>制剂单位</div>
                  <div className={styles.kvV}>{selected.preparation_unit}</div>
                </div>
                <div className={styles.kv}>
                  <div className={styles.kvK}>给药途径</div>
                  <div className={styles.kvV}>{selected.administration_route}</div>
                </div>
                <div className={styles.kv}>
                  <div className={styles.kvK}>生成时间</div>
                  <div className={styles.kvV}>{dayjs(selected.created_at).format('YYYY-MM-DD HH:mm')}</div>
                </div>
                <div className={styles.kv}>
                  <div className={styles.kvK}>生成人</div>
                  <div className={styles.kvV}>{selected.created_by_name || '—'}</div>
                </div>
              </div>

              <div className={styles.lockHint}>
                {IconLock}
                留痕记录由系统自动生成，不可删除或修改
              </div>

              <div className={styles.secTitle} style={{ marginTop: 18 }}>
                生成与下载记录 <span className={styles.secCnt}>{trails.length} 条</span>
              </div>
              <Spin spinning={trailsQuery.isPending}>
                <div className={styles.logList}>
                  {trails.map((t: AuthorizationLetterTrail) => {
                    const isGen = t.action === 'generate'
                    const label = isGen ? '生成' : '下载'
                    return (
                      <div key={t.id} className={`${styles.logItem} ${isGen ? styles.logGen : styles.logDl}`}>
                        <div className={styles.logDot} />
                        <div className={styles.logAct}>
                          {label} <span className={styles.logBadge}>{label}</span>
                        </div>
                        <div className={styles.logDesc}>{t.detail}</div>
                        <div className={styles.logMeta}>
                          {dayjs(t.created_at).format('YYYY-MM-DD HH:mm')} · {t.created_by_name || '系统'}
                        </div>
                      </div>
                    )
                  })}
                  {trails.length === 0 && !trailsQuery.isPending && <Empty description="暂无留痕记录" />}
                </div>
              </Spin>
            </>
          )}
        </div>
      </Drawer>

      {/* 生成弹窗（流程维持现状） */}
      <Modal
        title="生成授权书"
        open={generateModalOpen}
        onOk={() => void handleGenerate()}
        onCancel={() => {
          setGenerateModalOpen(false)
          form.resetFields()
          setFileList([])
          setTemplateSource('builtin')
          setReplacements([{ old: '', new: '' }])
        }}
        confirmLoading={generating}
        width={600}
        className={styles.modalRoot}
      >
        <div className={ui.tokenScope}>
          <Form form={form} layout="vertical">
            <Form.Item
              name="product_name"
              label="产品名称"
              rules={[{ required: true, message: '请选择产品名称' }]}
            >
              <Select
                placeholder="请选择产品"
                showSearch
                onChange={handleProductChange}
                options={products.map(p => ({ label: p.product_name, value: p.product_name }))}
              />
            </Form.Item>

            <Form.Item
              name="registration_number"
              label="登记号"
              rules={[{ required: true, message: '请输入登记号' }]}
            >
              <Input placeholder="选择产品后自动填充" disabled />
            </Form.Item>

            <Form.Item
              name="preparation_unit"
              label="制剂单位名称"
              rules={[{ required: true, message: '请输入制剂单位名称' }]}
            >
              <Input placeholder="如：国药集团致君（深圳）制药有限公司" />
            </Form.Item>

            <Form.Item
              name="preparation_name"
              label="制剂名称"
              rules={[{ required: true, message: '请输入制剂名称' }]}
            >
              <Input placeholder="如：注射用头孢他啶" />
            </Form.Item>

            <Form.Item
              name="administration_route"
              label="给药途径"
              rules={[{ required: true, message: '请输入给药途径' }]}
            >
              <Input placeholder="如：注射" />
            </Form.Item>

            <Form.Item label="模板来源" required>
              <Radio.Group
                value={templateSource}
                onChange={e => setTemplateSource(e.target.value)}
                options={[
                  { label: '内置中文模板', value: 'builtin' },
                  { label: '上传自定义模板', value: 'custom' },
                ]}
              />
            </Form.Item>

            {templateSource === 'builtin' && (
              <div style={{ marginTop: -12, marginBottom: 16, fontSize: 15, color: 'var(--ink-3)' }}>
                使用内置中文授权书模板，上述表单内容将自动填入对应位置
              </div>
            )}

            {templateSource === 'custom' && (
              <>
                <Form.Item
                  name="template"
                  label="模板文件"
                  rules={[{ required: true, message: '请上传模板文件' }]}
                >
                  <Upload
                    beforeUpload={() => false}
                    fileList={fileList}
                    onChange={({ fileList }) => setFileList(fileList)}
                    maxCount={1}
                    accept=".docx"
                  >
                    <button type="button" className={ui.btn}>
                      <UploadOutlined />
                      选择 .docx 模板文件
                    </button>
                  </Upload>
                </Form.Item>

                <Form.Item label="替换规则" required>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {replacements.map((item, index) => (
                      <div key={index} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        <Input
                          placeholder="原文本"
                          value={item.old}
                          onChange={e => {
                            const next = [...replacements]
                            next[index].old = e.target.value
                            setReplacements(next)
                          }}
                          style={{ flex: 1 }}
                        />
                        <span>→</span>
                        <Input
                          placeholder="新文本"
                          value={item.new}
                          onChange={e => {
                            const next = [...replacements]
                            next[index].new = e.target.value
                            setReplacements(next)
                          }}
                          style={{ flex: 1 }}
                        />
                        {replacements.length > 1 && (
                          <button
                            type="button"
                            className={styles.opDel}
                            title="删除规则"
                            onClick={() => setReplacements(replacements.filter((_, i) => i !== index))}
                          >
                            {IconTrash}
                          </button>
                        )}
                      </div>
                    ))}
                    <button
                      type="button"
                      className={ui.btn}
                      onClick={() => setReplacements([...replacements, { old: '', new: '' }])}
                    >
                      {IconPlus} 添加替换规则
                    </button>
                    <div style={{ fontSize: 15, color: 'var(--ink-3)' }}>
                      提示：.docx 模板按原文本整词替换；.doc 旧格式模板要求原文本和新文本字数相同
                    </div>
                  </div>
                </Form.Item>
              </>
            )}

            <Form.Item name="remarks" label="备注">
              <Input.TextArea rows={3} placeholder="可选" />
            </Form.Item>
          </Form>
        </div>
      </Modal>
    </div>
  )
}
