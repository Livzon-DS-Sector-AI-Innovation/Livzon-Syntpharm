'use client'

/**
 * 阶段交付文档 → AI 生成研发报告的三步向导。
 *
 * 设计目标：用户在行内点一次「AI 生成」，看到的全部是已经预填好的内容，
 * 最少只需再点一次「开始生成」。因此第 1 步只做确认（不放下拉框让用户挑模板），
 * 第 2 步把三个可选字段预填好并允许整体跳过，第 3 步在任何情况下都能关掉弹窗，
 * 后台任务继续跑，进度会在交付文档那一行继续显示。
 */
import { useEffect, useMemo, useState } from 'react'
import { Alert, App, Button, Collapse, Descriptions, Flex, Input, Modal, Progress, Select, Space, Spin, Steps, Tag, Typography } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { generateDeliverable } from '@/actions/research/deliverables'
import {
  fetchDeliverableGenerationOptions,
  fetchDeliverableGenerationStatus,
} from '@/lib/api/client/research/rd-project'
import type { RdDeliverableGenerateResult } from '@/types/research/rd-project'
import { fetchReportGenDocumentBlob } from '@/lib/api/client/research/report-gen'
import { KnowledgeBaseModal } from './KnowledgeBaseModal'
import { summarizeKb, useKbDocuments, useKnowledgeBase } from './useKnowledgeBase'
import { DocxPreviewModal } from './DocxPreviewModal'
import { MarkdownPreviewModal } from './MarkdownPreviewModal'
import { withReturnTo } from '@/lib/navigation/returnTo'

const { Text, Paragraph } = Typography

const STEPS = [{ title: '确认内容' }, { title: '补充信息' }, { title: '生成结果' }]

interface FormState {
  title: string
  version: string
  docCode: string
  drugName: string
  supplement: string
}

interface Props {
  open: boolean
  onClose: () => void
  projectId: string
  stage: string
  deliverableType: string
  deliverableLabel: string
  /** 已存在的交付文档记录；为空表示这一行还没建记录，后端会自动补建 */
  deliverableId?: string | null
  /** 提交成功或任务完成时通知父组件刷新列表 */
  onSubmitted?: () => void
}

export function DeliverableGenerateWizard({
  open,
  onClose,
  projectId,
  stage,
  deliverableType,
  deliverableLabel,
  deliverableId,
  onSubmitted,
}: Props) {
  const { message: msgApi } = App.useApp()
  const router = useRouter()
  const [manualStep, setManualStep] = useState<number | null>(null)
  const [submitted, setSubmitted] = useState<RdDeliverableGenerateResult | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [kbOpen, setKbOpen] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [comparisonOpen, setComparisonOpen] = useState(false)
  const [comparisonText, setComparisonText] = useState('')
  const [comparisonLoading, setComparisonLoading] = useState(false)
  // 表单/模板都是「后端预填值 + 用户改动」：改动按 key 存草稿，换了交付文档或预填版本就
  // 自动回落到新的预填值，不需要在 effect 里 setState（否则会触发级联渲染）
  const [formDraft, setFormDraft] = useState<{ key: string; value: FormState } | null>(null)
  const [templateDraft, setTemplateDraft] = useState<{ key: string; value: string | null } | null>(null)

  const optionsQuery = useQuery({
    queryKey: ['deliverable-generation-options', projectId, stage, deliverableType, deliverableId ?? 'new'],
    queryFn: () => fetchDeliverableGenerationOptions({ projectId, stage, deliverableType, deliverableId }),
    enabled: open,
    staleTime: 30_000,
  })
  const options = optionsQuery.data

  const kbQuery = useKnowledgeBase(projectId, open)
  const kbId = kbQuery.data?.[0]?.id
  const docsQuery = useKbDocuments(kbId)
  const kbSummary = useMemo(() => summarizeKb(docsQuery.data ?? []), [docsQuery.data])

  const formKey = `${deliverableId ?? 'new'}:${options?.default_version ?? ''}`
  const form: FormState =
    formDraft?.key === formKey
      ? formDraft.value
      : {
          title: options?.default_title ?? '',
          version: options?.default_version ?? '',
          docCode: options?.default_doc_code ?? '',
          drugName: options?.default_drug_name ?? '',
          supplement: '',
        }
  const setForm = (value: FormState) => setFormDraft({ key: formKey, value })

  const templateId =
    templateDraft?.key === formKey ? templateDraft.value : (options?.recommended_template_id ?? null)
  const setTemplateId = (value: string | null) => setTemplateDraft({ key: formKey, value })

  // 已在生成的任务直接把用户带到第 3 步；用户手动前进/后退后以手动为准
  const step = manualStep ?? (options?.active_job ? 2 : 0)
  const setStep = setManualStep

  const targetId = submitted?.deliverable_id ?? (options?.active_job ? options.deliverable_id : null)

  const statusQuery = useQuery({
    queryKey: ['deliverable-generation-status', targetId],
    queryFn: () => fetchDeliverableGenerationStatus(targetId as string),
    enabled: open && step === 2 && !!targetId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'queued' || status === 'running' ? 3000 : false
    },
  })
  const status = statusQuery.data

  // 出稿即刷新父列表，让那一行马上出现附件名与「待核对」徽标
  useEffect(() => {
    if (status?.status === 'completed') onSubmitted?.()
  }, [status?.status, onSubmitted])

  const submit = async (useDefaults: boolean) => {
    if (!options) return
    setSubmitting(true)
    try {
      const result = await generateDeliverable({
        project_id: projectId,
        stage,
        deliverable_type: deliverableType,
        deliverable_id: options.deliverable_id ?? null,
        template_id: templateId ?? options.recommended_template_id ?? null,
        title: useDefaults ? null : form.title.trim() || null,
        version: useDefaults ? null : form.version.trim() || null,
        doc_code: useDefaults ? null : form.docCode.trim() || null,
        drug_name: useDefaults ? null : form.drugName.trim() || null,
        supplement_text: useDefaults ? null : form.supplement.trim() || null,
      })
      setSubmitted(result)
      setStep(2)
      onSubmitted?.()
      msgApi.success(result.reused ? '已有生成任务在跑，已接上它的进度' : '已提交生成，完成后自动归档到这份交付文档')
    } catch (error) {
      msgApi.error(error instanceof Error ? error.message : '提交失败，请稍后重试')
    } finally {
      setSubmitting(false)
    }
  }

  const retry = () => {
    setSubmitted(null)
    setStep(0)
    void optionsQuery.refetch()
  }

  const templates = options?.templates ?? []
  const recommended = templates.find((item) => item.id === templateId) ?? null
  const hasTemplate = !!options?.recommended_template_id
  const docDownloadUrl = targetId ? `/api/v1/research/rd-stage-deliverables/${targetId}/download` : null
  const jobId = submitted?.job_id ?? status?.job_id ?? null

  /** 预览对照表：按需拉一次 Markdown，不随轮询反复拉 */
  const openComparison = async () => {
    setComparisonOpen(true)
    if (!jobId || comparisonText || comparisonLoading) return
    setComparisonLoading(true)
    try {
      const blob = await fetchReportGenDocumentBlob(jobId, 'comparison')
      setComparisonText(await blob.text())
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '对照表加载失败')
    } finally {
      setComparisonLoading(false)
    }
  }

  const footer =
    step === 0
      ? [
          <Button key="cancel" onClick={onClose}>
            取消
          </Button>,
          <Button key="next" type="primary" disabled={!options} onClick={() => setStep(1)}>
            下一步
          </Button>,
        ]
      : step === 1
        ? [
            <Button key="prev" onClick={() => setStep(0)}>
              上一步
            </Button>,
            <Button key="skip" onClick={() => void submit(true)} loading={submitting}>
              跳过，直接生成
            </Button>,
            <Button key="submit" type="primary" onClick={() => void submit(false)} loading={submitting}>
              开始生成
            </Button>,
          ]
        : [
            <Button key="close" onClick={onClose}>
              关闭
            </Button>,
            status?.status === 'failed' ? (
              <Button key="retry" type="primary" onClick={retry}>
                重试
              </Button>
            ) : status?.status === 'completed' ? (
              <Button key="again" onClick={retry}>
                重新生成
              </Button>
            ) : null,
          ]

  return (
    <>
      <Modal
        open={open}
        title={`AI 生成 · ${deliverableLabel}`}
        width={760}
        onCancel={onClose}
        footer={<Flex justify="end" gap={8}>{footer}</Flex>}
        destroyOnClose
        afterClose={() => {
          // 关闭即彻底复位：下次打开是「这条交付文档当前状态」而不是上次的残影
          setManualStep(null)
          setSubmitted(null)
          setFormDraft(null)
          setTemplateDraft(null)
        }}
      >
        <Steps current={step} items={STEPS} size="small" style={{ marginBottom: 20 }} />

        {optionsQuery.isLoading ? (
          <Flex justify="center" style={{ padding: '48px 0' }}>
            <Spin tip="正在准备模板与资料…" />
          </Flex>
        ) : optionsQuery.isError || !options ? (
          <Alert type="error" showIcon message="加载生成信息失败" description="请关闭弹窗后重试；若持续失败，请联系管理员检查模板配置。" />
        ) : (
          <>
            {step === 0 && (
              <Flex vertical gap={16}>
                <Space size={[8, 8]} wrap>
                  <Tag color="blue">{options.project_name}</Tag>
                  <Tag>{options.stage_label}</Tag>
                  <Tag color="geekblue">{options.deliverable_type_label}</Tag>
                  <Text type="secondary">系统已按阶段和文档类型选好模板，确认无误即可继续</Text>
                </Space>

                {hasTemplate && recommended ? (
                  <div style={{ border: '1px solid #b7eb8f', background: '#f6ffed', borderRadius: 8, padding: 16 }}>
                    <Flex justify="space-between" align="center" wrap gap={8}>
                      <div>
                        <Flex align="center" gap={8}>
                          <Text strong>{recommended.name}</Text>
                          {recommended.version_no ? <Tag color="green">v{recommended.version_no}</Tag> : null}
                          <Tag color="blue">自动匹配</Tag>
                        </Flex>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {recommended.file_name ?? '模板母本'}
                        </Text>
                      </div>
                      {templates.length > 1 ? (
                        <Select
                          size="small"
                          style={{ minWidth: 220 }}
                          value={templateId ?? undefined}
                          onChange={(value) => setTemplateId(value)}
                          options={templates.map((item) => ({
                            value: item.id,
                            label: `${item.name}${item.has_file ? '' : '（缺母本文件）'}`,
                            disabled: !item.has_file,
                          }))}
                          placeholder="换一个模板"
                        />
                      ) : null}
                    </Flex>
                  </div>
                ) : (
                  <Alert
                    type="warning"
                    showIcon
                    message="这类文档还没有可用的 Word 模板"
                    description={
                      <Flex vertical gap={8} align="flex-start">
                        <span>
                          系统不会自动替你新建模板。请先上传母本并启用，再回来生成。
                          {templates.length > 0
                            ? `当前阶段有 ${templates.length} 个其它类型的模板，但不能拿来出这份文档。`
                            : ''}
                        </span>
                        <Button size="small" onClick={() => router.push('/research/deliverable-templates')}>
                          去上传模板
                        </Button>
                      </Flex>
                    }
                  />
                )}

                <Descriptions size="small" column={2} bordered>
                  <Descriptions.Item label="报告标题" span={2}>
                    {form.title}
                  </Descriptions.Item>
                  <Descriptions.Item label="版本号">{form.version}</Descriptions.Item>
                  <Descriptions.Item label="文件编号">{form.docCode || '未填'}</Descriptions.Item>
                  <Descriptions.Item label="资料准备" span={2}>
                    {kbSummary.parsed > 0 ? (
                      <Text>
                        项目知识库共 {kbSummary.total} 份，其中 {kbSummary.parsed} 份已入库可检索
                        {kbSummary.pending > 0 ? `，另有 ${kbSummary.pending} 份处理中` : ''}
                      </Text>
                    ) : (
                      <Flex gap={8} wrap align="center">
                        <Text type="warning">项目还没有可检索的资料，报告会有较多「待补充」</Text>
                        <Button size="small" onClick={() => setKbOpen(true)}>
                          上传资料
                        </Button>
                      </Flex>
                    )}
                  </Descriptions.Item>
                </Descriptions>

                <Text type="secondary" style={{ fontSize: 12 }}>
                  生成会用到这份模板 + 项目登记信息 + 项目资料库；完成后自动归档到这条交付文档，并在研发报告里留一份记录。
                </Text>
              </Flex>
            )}

            {step === 1 && (
              <Flex vertical gap={14}>
                <Alert type="info" showIcon message="下面三项都已按项目信息填好，可以直接开始生成；只有确实要改时再动。" />
                <Flex gap={12} wrap>
                  <Flex vertical gap={4} style={{ flex: 1, minWidth: 220 }}>
                    <Text type="secondary">文件编号</Text>
                    <Input value={form.docCode} onChange={(e) => setForm({ ...form, docCode: e.target.value })} />
                  </Flex>
                  <Flex vertical gap={4} style={{ flex: 1, minWidth: 220 }}>
                    <Text type="secondary">品种名称</Text>
                    <Input value={form.drugName} onChange={(e) => setForm({ ...form, drugName: e.target.value })} />
                  </Flex>
                </Flex>
                <Flex vertical gap={4}>
                  <Text type="secondary">补充说明（可留空）</Text>
                  <Input.TextArea
                    rows={3}
                    value={form.supplement}
                    placeholder="例如本批次要重点体现的工艺调整、客户关注项"
                    onChange={(e) => setForm({ ...form, supplement: e.target.value })}
                  />
                </Flex>
                <Collapse
                  size="small"
                  items={[
                    {
                      key: 'advanced',
                      label: '高级设置',
                      children: (
                        <Flex vertical gap={10}>
                          <Flex vertical gap={4}>
                            <Text type="secondary">报告标题</Text>
                            <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
                          </Flex>
                          <Flex gap={12} wrap>
                            <Flex vertical gap={4} style={{ flex: 1, minWidth: 200 }}>
                              <Text type="secondary">版本号</Text>
                              <Input
                                value={form.version}
                                onChange={(e) => setForm({ ...form, version: e.target.value })}
                              />
                            </Flex>
                            <Flex vertical gap={4} style={{ flex: 1, minWidth: 200 }}>
                              <Text type="secondary">模板</Text>
                              <Select
                                value={templateId ?? undefined}
                                onChange={(value) => setTemplateId(value)}
                                options={templates.map((item) => ({
                                  value: item.id,
                                  label: `${item.name}${item.has_file ? '' : '（缺母本文件）'}`,
                                  disabled: !item.has_file,
                                }))}
                              />
                            </Flex>
                          </Flex>
                        </Flex>
                      ),
                    },
                  ]}
                />
              </Flex>
            )}

            {step === 2 && (
              <Flex vertical gap={16}>
                {status?.status === 'failed' ? (
                  <Alert
                    type="error"
                    showIcon
                    message="生成失败"
                    description={status.error_message ?? '任务执行中断，请点「重试」重新生成。'}
                  />
                ) : status?.status === 'completed' ? (
                  <Alert
                    type="success"
                    showIcon
                    message="已生成并归档到这条交付文档"
                    description={
                      <span>
                        {status.slot_filled} 项内容已自动填写
                        {status.slot_gap > 0 ? `，还有 ${status.slot_gap} 项待补充` : ''}
                        。下载后核对一遍，再把交付状态改为「已完成」。
                      </span>
                    }
                  />
                ) : (
                  <>
                    <Progress
                      percent={status?.progress ?? 0}
                      status={status?.status === 'queued' ? 'normal' : 'active'}
                    />
                    <Paragraph type="secondary" style={{ margin: 0 }}>
                      {status?.current_step ?? '任务已排队，正在分配生成资源…'}
                    </Paragraph>
                  </>
                )}

                {(status?.slot_total ?? 0) > 0 && (
                  <Space size={16}>
                    <Text>共 {status?.slot_total} 项</Text>
                    <Text type="success">已填 {status?.slot_filled}</Text>
                    <Text type="warning">待补充 {status?.slot_gap}</Text>
                  </Space>
                )}

                {status?.status === 'completed' && (
                  <Space wrap>
                    {jobId ? (
                      <Button type="primary" onClick={() => setPreviewOpen(true)}>
                        预览成品
                      </Button>
                    ) : null}
                    {docDownloadUrl ? (
                      <Button href={docDownloadUrl} target="_blank">
                        下载 Word
                      </Button>
                    ) : null}
                    {jobId ? (
                      <Button onClick={() => void openComparison()} loading={comparisonLoading}>
                        查看对照表
                      </Button>
                    ) : null}
                    {jobId ? (
                      <Button
                        onClick={() =>
                          router.push(
                            withReturnTo(
                              `/research/reports/generation/${jobId}`,
                              `/research/projects/${projectId}?tab=deliverables`,
                            ),
                          )
                        }
                      >
                        打开报告详情
                      </Button>
                    ) : null}
                  </Space>
                )}

                <Text type="secondary" style={{ fontSize: 12 }}>
                  关闭弹窗不会打断生成，进度会继续显示在这条交付文档上。
                </Text>
              </Flex>
            )}
          </>
        )}
      </Modal>

      <KnowledgeBaseModal
        open={kbOpen}
        projectId={projectId}
        onClose={() => setKbOpen(false)}
        onChanged={() => void optionsQuery.refetch()}
      />

      <DocxPreviewModal
        open={previewOpen}
        title={`${deliverableLabel}预览`}
        loadBlob={() => {
          if (!jobId) return Promise.reject(new Error('还没有生成结果'))
          return fetchReportGenDocumentBlob(jobId, 'document')
        }}
        onClose={() => setPreviewOpen(false)}
      />
      <MarkdownPreviewModal
        open={comparisonOpen}
        title={`${deliverableLabel} · 填充项对照表`}
        markdown={comparisonLoading ? '正在加载对照表…' : comparisonText}
        onClose={() => setComparisonOpen(false)}
      />
    </>
  )
}