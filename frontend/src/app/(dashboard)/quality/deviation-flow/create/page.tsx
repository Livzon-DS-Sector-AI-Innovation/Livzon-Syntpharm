'use client'

import { useState, useEffect } from 'react'
import {
  Form, Input, Select, DatePicker, Button, Space,
  Typography, Divider, Upload, message, Steps, Modal, Tag,
} from 'antd'
import {
  SaveOutlined, UploadOutlined, PlusOutlined,
  FileTextOutlined, CheckCircleOutlined,
  UserOutlined, InfoCircleOutlined, AlertOutlined,
  ToolOutlined, PaperClipOutlined,
  SettingOutlined, ArrowRightOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { useRouter, useSearchParams } from 'next/navigation'
import { createDeviationFlow, updateDeviationFlow, submitDeviationFlow } from '@/actions/deviation'
import '../deviation-style.css'

const { Title: _Title, Text } = Typography
const { TextArea } = Input

const API_BASE = '/api/v1'

const DEVIATION_TYPES = [
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

const URGENCY_LEVELS = [
  { value: 'normal', label: '一般' },
  { value: 'important', label: '重要' },
  { value: 'serious', label: '严重' },
]

const DEPARTMENTS = [
  '生产部', '质量部', '工程部', '仓储部', '采购部', '研发部', '人事部', '行政部'
]

const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  draft: { color: 'default', label: '草稿' },
  basic_completed: { color: 'processing', label: '基础完成' },
  detail_completed: { color: 'warning', label: '详情完成' },
  completed: { color: 'success', label: '已完成' },
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

interface FeishuUser { open_id: string; name: string; is_active?: boolean; department?: string }
interface Attachment { id: string; file_name: string; uploaded_at?: string; file_path?: string }
export default function DeviationCreatePage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const editId = searchParams.get('edit')
  const [isEditMode, setIsEditMode] = useState(!!editId)
  const [currentDeviationId, setCurrentDeviationId] = useState<string | null>(editId)
  const [currentStatus, setCurrentStatus] = useState<string>('draft')
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [reporterInfo, setReporterInfo] = useState({
    name: '',
    department: '',
    time: '-'
  })
  const [qaUsers, setQaUsers] = useState<FeishuUser[]>([])
  const [deptLeaders, setDeptLeaders] = useState<FeishuUser[]>([])
  const [reporterOpenId, setReporterOpenId] = useState<string>('')
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [uploading, setUploading] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)')
    const update = () => setIsMobile(mq.matches)
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])

  useEffect(() => {
    loadReminderConfig()
  }, [])

  const loadReminderConfig = async () => {
    try {
      const [qaRes, leaderRes] = await Promise.all([
        fetch(`${API_BASE}/quality/deviation-settings/qa-users`),
        fetch(`${API_BASE}/quality/deviation-settings/leaders`),
      ])
      const qaResult = await qaRes.json()
      const leaderResult = await leaderRes.json()

      if (qaResult.code === 200) {
        setQaUsers(qaResult.data.filter((u: FeishuUser) => u.is_active !== false))
      }
      if (leaderResult.code === 200) {
        setDeptLeaders(leaderResult.data.filter((u: FeishuUser) => u.is_active !== false))
      }
    } catch (error) {
      console.error('加载提醒配置失败', error)
    }
  }

  useEffect(() => {
    if (editId) {
      loadDeviationData(editId)
    }
  }, [editId])

  const loadDeviationData = async (id: string) => {
    try {
      const response = await fetch(`${API_BASE}/quality/deviation-flow/${id}`)
      const result = await response.json()
      if (result.code === 200) {
        const data = result.data
        setCurrentStatus(data.status || 'draft')
        setCurrentDeviationId(id)
        setIsEditMode(true)

        form.setFieldsValue({
          theme: data.theme,
          occurred_date: data.occurred_date ? dayjs(data.occurred_date) : null,
          discovered_date: data.discovered_date ? dayjs(data.discovered_date) : null,
          responsible_department: data.responsible_department,
          occurred_area: data.occurred_area,
          deviation_type: data.deviation_type,
          urgency_level: data.urgency_level,
          product_name: data.product_name,
          batch_no: data.batch_no,
          equipment: data.equipment,
          standard_based_on: data.standard_based_on,
          deviation_description: data.deviation_description,
          risk_assessment: data.risk_assessment,
          temp_measures: data.temp_measures,
          related_deviation_no: data.related_deviation_no,
          related_capa: data.related_capa,
          remarks: data.remarks,
        })
        setReporterInfo({
          name: data.reporter || '当前用户',
          department: data.reporter_department || '生产部',
          time: data.report_time ? dayjs(data.report_time).format('YYYY-MM-DD HH:mm:ss') : '-'
        })
        if (data.reporter_feishu_open_id) {
          setReporterOpenId(data.reporter_feishu_open_id)
        }
        loadAttachments(id)
      }
    } catch (_error) {
      message.error('加载数据失败')
    }
  }

  const loadAttachments = async (deviationId: string) => {
    try {
      const response = await fetch(`${API_BASE}/quality/deviation-flow/${deviationId}/attachments`)
      const result = await response.json()
      if (result.code === 200) {
        setAttachments(result.data || [])
      }
    } catch (error) {
      console.error('加载附件失败:', error)
    }
  }

  const handleUpload = async (file: File) => {
    if (!currentDeviationId) {
      message.warning('请先保存偏差任务后再上传附件')
      return false
    }

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(`${API_BASE}/quality/deviation-flow/${currentDeviationId}/attachments`, {
        method: 'POST',
        body: formData,
      })
      const result = await response.json()

      if (result.code === 200) {
        message.success('附件上传成功')
        loadAttachments(currentDeviationId)
      } else {
        message.error(result.message || '上传失败')
      }
    } catch (_error) {
      message.error('上传失败，请重试')
    } finally {
      setUploading(false)
    }
    return false
  }

  const handleDownload = (attachment: Attachment) => {
    window.open(`${API_BASE}/quality/deviation-flow/attachments/${attachment.id}/download`, '_blank')
  }

  const validateReporterInfo = () => {
    if (currentStatus === 'draft' && !reporterInfo.name) {
      message.warning('请输入手机号查询填报人信息')
      return false
    }
    return true
  }

  const getCurrentStep = () => {
    switch (currentStatus) {
      case 'draft': return 0
      case 'basic_completed': return 1
      case 'detail_completed': return 2
      case 'completed': return 3
      default: return 0
    }
  }

  const saveData = async (apiPath: string, method: string) => {
    const values = form.getFieldsValue()
    const data = {
      theme: values.theme,
      occurred_date: values.occurred_date?.format('YYYY-MM-DD HH:mm:ss'),
      discovered_date: values.discovered_date?.format('YYYY-MM-DD HH:mm:ss'),
      responsible_department: values.responsible_department,
      occurred_area: values.occurred_area,
      deviation_type: values.deviation_type,
      urgency_level: values.urgency_level,
      product_name: values.product_name,
      batch_no: values.batch_no,
      equipment: values.equipment,
      standard_based_on: values.standard_based_on,
      deviation_description: values.deviation_description,
      risk_assessment: values.risk_assessment,
      temp_measures: values.temp_measures,
      related_deviation_no: values.related_deviation_no,
      related_capa: values.related_capa,
      remarks: values.remarks,
      qa_feishu_open_id: values.qa_user?.value || values.qa_user,
      qa_feishu_name: qaUsers.find(u => u.open_id === (values.qa_user?.value || values.qa_user))?.name || '',
      dept_leader_feishu_open_id: values.dept_leader?.value || values.dept_leader,
      dept_leader_feishu_name: deptLeaders.find(u => u.open_id === (values.dept_leader?.value || values.dept_leader))?.name || '',
      reporter: reporterInfo.name,
      reporter_department: values.reporter_department || reporterInfo.department,
      reporter_feishu_open_id: reporterOpenId,
    }

    if (method === 'POST') {
      return createDeviationFlow(data)
    } else {
      return updateDeviationFlow(currentDeviationId!, data)
    }
  }

  const handleSaveDraft = async () => {
    try {
      if (!validateReporterInfo()) return
      setLoading(true)

      if (isEditMode && currentDeviationId) {
        await saveData('', 'PUT')
      } else {
        const result = await saveData('', 'POST') as { data: { id: string } }
        setCurrentDeviationId(result.data.id)
        setIsEditMode(true)
      }

      message.success('保存成功')
    } catch (error: unknown) {
      message.error((error instanceof Error ? error.message : undefined) || '保存失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async () => {
    try {
      if (!validateReporterInfo()) return
      setLoading(true)

      let targetStatus = ''
      let confirmMessage = ''

      switch (currentStatus) {
        case 'draft':
          await form.validateFields(['theme', 'occurred_date', 'discovered_date', 'qa_user', 'dept_leader'])
          targetStatus = 'basic_completed'
          confirmMessage = '提交后将进入「基础完成」状态，可继续填写偏差详情。确定提交吗？'
          break
        case 'basic_completed':
          await form.validateFields(['deviation_description'])
          targetStatus = 'detail_completed'
          confirmMessage = '提交后将进入「详情完成」状态，可继续填写辅助信息。确定提交吗？'
          break
        case 'detail_completed':
          await form.validateFields(['temp_measures', 'related_capa'])
          targetStatus = 'completed'
          confirmMessage = '提交后将完成整个偏差流程。确定提交吗？'
          break
        default:
          message.warning('当前状态不允许提交')
          setLoading(false)
          return
      }

      const confirmed = await new Promise<boolean>((resolve) => {
        Modal.confirm({
          title: '确认提交',
          content: confirmMessage,
          onOk: () => resolve(true),
          onCancel: () => resolve(false),
        })
      })

      if (!confirmed) {
        setLoading(false)
        return
      }

      let deviationId = currentDeviationId
      if (!deviationId) {
        const saveResult = await saveData('', 'POST') as { data: { id: string } }
        deviationId = saveResult.data.id
        setCurrentDeviationId(deviationId)
        setIsEditMode(true)
      } else {
        await saveData('', 'PUT')
      }

      const result = await submitDeviationFlow(deviationId!, targetStatus)

      if (result.code === 200) {
        message.success(result.message as string)
        setCurrentStatus(targetStatus)

        if (targetStatus === 'completed') {
          Modal.success({
            title: '偏差已完成',
            content: '偏差流程已完成！' as string,
            onOk: () => router.push('/quality/deviation-flow/query'),
          })
        }
      } else {
        message.error((result.message as string) || '提交失败')
      }
    } catch (error: any) {
      if (error.errorFields) {
        message.error('请填写必填项')
      } else {
        message.error(error.message || '提交失败')
      }
    } finally {
      setLoading(false)
    }
  }

  const getSteps = () => {
    const stepItems = [
      { title: '基础信息', icon: <FileTextOutlined /> },
      { title: '偏差详情', icon: <InfoCircleOutlined /> },
      { title: '辅助信息', icon: <PlusOutlined /> },
      { title: '完成', icon: <CheckCircleOutlined /> },
    ]
    return stepItems
  }

  const statusInfo = STATUS_CONFIG[currentStatus] || STATUS_CONFIG.draft
  const showBasic = currentStatus === 'draft' || currentStatus === 'basic_completed' || currentStatus === 'detail_completed'
  const showDetail = currentStatus === 'basic_completed' || currentStatus === 'detail_completed'
  const showAuxiliary = currentStatus === 'detail_completed'

  return (
    <div className="deviation-page">
      <div className="deviation-header">
        <div className="deviation-header-left">
          <h1>
            <FileTextOutlined />
            {isEditMode ? '编辑偏差任务' : '新建偏差任务'}
            <Tag color={statusInfo.color} style={{ marginLeft: 8 }}>{statusInfo.label}</Tag>
          </h1>
          <p>记录偏差事件，跟踪处理流程，确保质量合规</p>
        </div>
        <div className="deviation-header-right">
          <Button icon={<ArrowRightOutlined />} onClick={() => router.push('/quality/deviation-flow/query')}>
            返回列表
          </Button>
        </div>
      </div>

      <div className="deviation-section-card deviation-steps-card">
        <div className="deviation-steps">
          <Steps current={getCurrentStep()} items={getSteps()} />
        </div>
      </div>

      <Form form={form} layout="vertical">
        {currentStatus === 'draft' && (
          <SectionCard
            icon={<UserOutlined />}
            title="填报人信息"
            className="deviation-reporter-card"
          >
            <div className="deviation-form-grid">
              <Form.Item label="填报人手机号" style={{ marginBottom: 0 }}>
                <Space.Compact style={{ width: '100%' }}>
                  <Form.Item name="reporter_mobile" noStyle>
                    <Input placeholder="请输入手机号获取填报人信息" />
                  </Form.Item>
                  <Button
                    type="primary"
                    onClick={async () => {
                      const mobile = form.getFieldValue('reporter_mobile')
                      if (!mobile) {
                        message.warning('请输入手机号')
                        return
                      }
                      try {
                        const response = await fetch(`${API_BASE}/quality/deviation-settings/feishu-user/by-mobile?mobile=${mobile}`)
                        const result = await response.json()
                        if (result.code === 200 && result.data) {
                          setReporterInfo({
                            name: result.data.name,
                            department: '',
                            time: dayjs().format('YYYY-MM-DD HH:mm:ss')
                          })
                          setReporterOpenId(result.data.open_id)
                          form.setFieldsValue({ reporter_department: '' })
                          message.success(`已获取填报人：${result.data.name}`)
                        } else {
                          message.warning(result.message || '未找到对应用户')
                        }
                      } catch {
                        message.error('查询失败，请检查后端服务')
                      }
                    }}
                  >
                    查询
                  </Button>
                </Space.Compact>
              </Form.Item>
              <Form.Item name="reporter_department" label="填报部门" style={{ marginBottom: 0 }}>
                <Select placeholder="请选择填报部门" allowClear>
                  {DEPARTMENTS.map(d => (
                    <Select.Option key={d} value={d}>{d}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
              <div>
                <div style={{ paddingTop: 4 }}>
                  {reporterInfo.name ? (
                    <Text type="secondary" style={{ fontSize: 13 }}>
                      填报人：<Text strong style={{ color: '#065f46' }}>{reporterInfo.name}</Text>
                      {reporterInfo.time && <><br />时间：{reporterInfo.time}</>}
                    </Text>
                  ) : (
                    <Text type="secondary" style={{ fontSize: 13 }}>
                      请输入手机号查询填报人信息
                    </Text>
                  )}
                </div>
              </div>
            </div>
          </SectionCard>
        )}

        {currentStatus !== 'draft' && reporterInfo.name && (
          <SectionCard
            icon={<CheckCircleOutlined />}
            title="填报人信息"
            className="deviation-reporter-done"
          >
            <Text type="secondary" style={{ fontSize: 13 }}>
              填报人：<Text strong style={{ color: '#166534' }}>{reporterInfo.name}</Text>
              {reporterInfo.department && ` | 填报部门：${reporterInfo.department}`}
              {reporterInfo.time && ` | 填报时间：${reporterInfo.time}`}
            </Text>
          </SectionCard>
        )}

        {showBasic && (
          <SectionCard icon={<AlertOutlined />} title="偏差基础信息">
            <div className="deviation-form-grid grid-1">
              <Form.Item name="theme" label="偏差主题" rules={[{ required: currentStatus === 'draft', message: '请输入偏差主题' }]}>
                <Input placeholder="请输入偏差主题" size="large" />
              </Form.Item>
            </div>
            <div className="deviation-form-grid">
              <Form.Item name="occurred_date" label="偏差发生日期" rules={[{ required: currentStatus === 'draft', message: '请选择发生日期' }]}>
                <DatePicker showTime style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="discovered_date" label="发现日期" rules={[{ required: currentStatus === 'draft', message: '请选择发现日期' }]}>
                <DatePicker showTime style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="responsible_department" label="责任部门">
                <Select placeholder="请选择责任部门" allowClear>
                  {DEPARTMENTS.map(d => (
                    <Select.Option key={d} value={d}>{d}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </div>
            <div className="deviation-form-grid">
              <Form.Item name="occurred_area" label="发生区域/车间">
                <Input placeholder="请输入发生区域" />
              </Form.Item>
              <Form.Item name="deviation_type" label="偏差类型">
                <Select placeholder="请选择偏差类型" allowClear showSearch optionFilterProp="children">
                  {DEVIATION_TYPES.map(t => (
                    <Select.Option key={t.value} value={t.value}>{t.label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
              <Form.Item name="urgency_level" label="紧急等级">
                <Select placeholder="请选择紧急等级" allowClear>
                  {URGENCY_LEVELS.map(l => (
                    <Select.Option key={l.value} value={l.value}>{l.label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </div>
          </SectionCard>
        )}

        {showDetail && (
          <SectionCard icon={<InfoCircleOutlined />} title="偏差详情">
            <div className="deviation-form-grid">
              <Form.Item name="product_name" label="涉及产品/物料">
                <Input placeholder="请输入涉及产品/物料" />
              </Form.Item>
              <Form.Item name="batch_no" label="批次号">
                <Input placeholder="请输入批次号" />
              </Form.Item>
              <Form.Item name="equipment" label="涉及设备/仪器">
                <Input placeholder="请输入涉及设备/仪器" />
              </Form.Item>
            </div>
            <div className="deviation-form-grid">
              <Form.Item name="standard_based_on" label="偏离标准依据" style={{ marginBottom: 0 }}>
                <Input placeholder="请输入规程/文件编号" />
              </Form.Item>
            </div>
            <Divider style={{ margin: '16px 0', fontSize: 13 }}>详细描述</Divider>
            <div className="deviation-form-grid grid-1">
              <Form.Item name="deviation_description" label="偏差完整经过描述" rules={[{ required: currentStatus === 'basic_completed', message: '请描述偏差经过' }]}>
                <TextArea rows={5} placeholder="请详细描述偏差发生的完整经过" />
              </Form.Item>
            </div>
            <div className="deviation-form-grid grid-1">
              <Form.Item name="risk_assessment" label="初步风险影响评估">
                <TextArea rows={4} placeholder="请评估对产品质量、数据完整性、环境合规、设备状态的影响" />
              </Form.Item>
            </div>
          </SectionCard>
        )}

        {showAuxiliary && (
          <>
            <SectionCard icon={<ToolOutlined />} title="辅助信息">
              <div className="deviation-form-grid grid-1">
                <Form.Item name="temp_measures" label="临时处置措施" rules={[{ required: true, message: '请填写临时处置措施' }]}>
                  <TextArea rows={4} placeholder="请记录现场即时整改、隔离、暂停生产等操作" />
                </Form.Item>
              </div>
              <div className="deviation-form-grid">
                <Form.Item name="related_deviation_no" label="关联偏差单号">
                  <Input placeholder="请输入关联偏差单号" />
                </Form.Item>
                <Form.Item name="related_capa" label="关联CAPA" rules={[{ required: true, message: '请输入关联CAPA' }]}>
                  <Input placeholder="请输入关联CAPA编号" />
                </Form.Item>
              </div>
              <div className="deviation-form-grid grid-1">
                <Form.Item name="remarks" label="备注说明">
                  <TextArea rows={3} placeholder="其他补充说明" />
                </Form.Item>
              </div>
            </SectionCard>

            <SectionCard icon={<PaperClipOutlined />} title="附件上传">
              <Upload.Dragger
                name="file"
                multiple={true}
                beforeUpload={handleUpload}
                showUploadList={false}
                disabled={uploading}
              >
                <p className="ant-upload-drag-icon">
                  <UploadOutlined />
                </p>
                <p className="ant-upload-text">点击或拖拽上传附件</p>
                <p className="ant-upload-hint">支持单个或批量上传偏差报告相关文件</p>
              </Upload.Dragger>

              {attachments.length > 0 && (
                <div className="deviation-attachment-list">
                  {attachments.map((item: Attachment) => (
                    <div key={item.id} className="deviation-attachment-item">
                      <div className="deviation-attachment-info">
                        <div className="deviation-attachment-icon">
                          <FileTextOutlined />
                        </div>
                        <div className="deviation-attachment-text">
                          <div className="deviation-attachment-name">{item.file_name}</div>
                          <div className="deviation-attachment-time">
                            上传时间: {item.uploaded_at ? dayjs(item.uploaded_at).format('YYYY-MM-DD HH:mm') : '-'}
                          </div>
                        </div>
                      </div>
                      <Button type="link" icon={<FileTextOutlined />} onClick={() => handleDownload(item)}>
                        下载
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </SectionCard>
          </>
        )}

        {currentStatus === 'completed' && (
          <>
            <div className="deviation-section-card">
              <div className="deviation-completed">
                <div className="deviation-completed-icon">
                  <CheckCircleOutlined />
                </div>
                <h2>偏差已完成</h2>
                <p>所有信息已填写完毕，偏差流程已完成。</p>
              </div>
            </div>

            {attachments.length > 0 && (
              <SectionCard icon={<PaperClipOutlined />} title="附件列表">
                <div className="deviation-attachment-list">
                  {attachments.map((item: Attachment) => (
                    <div key={item.id} className="deviation-attachment-item">
                      <div className="deviation-attachment-info">
                        <div className="deviation-attachment-icon">
                          <FileTextOutlined />
                        </div>
                        <div className="deviation-attachment-text">
                          <div className="deviation-attachment-name">{item.file_name}</div>
                          <div className="deviation-attachment-time">
                            上传时间: {item.uploaded_at ? dayjs(item.uploaded_at).format('YYYY-MM-DD HH:mm') : '-'}
                          </div>
                        </div>
                      </div>
                      <Button type="link" icon={<FileTextOutlined />} onClick={() => handleDownload(item)}>
                        下载
                      </Button>
                    </div>
                  ))}
                </div>
              </SectionCard>
            )}
          </>
        )}

        {currentStatus !== 'completed' && (
          <SectionCard icon={<SettingOutlined />} title="提醒接收人设置">
            <div className="deviation-form-grid">
              <Form.Item name="qa_user" label="接收提醒 QA 人员">
                <Select placeholder="请选择 QA 人员" showSearch labelInValue allowClear optionFilterProp="children">
                  {qaUsers.map(u => (
                    <Select.Option key={u.open_id} value={u.open_id}>{u.name}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
              <Form.Item name="dept_leader" label="部门负责人">
                <Select placeholder="请选择部门负责人" showSearch labelInValue allowClear optionFilterProp="children">
                  {deptLeaders.map(u => (
                    <Select.Option key={u.open_id} value={u.open_id}>{u.name}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </div>
          </SectionCard>
        )}

        {currentStatus !== 'completed' && (
          <div className="deviation-actions">
            <Button onClick={handleSaveDraft} loading={loading} icon={<SaveOutlined />}>
              保存
            </Button>
            <Button type="primary" onClick={handleSubmit} loading={loading} icon={<ArrowRightOutlined />}>
              {currentStatus === 'draft' && '提交基础信息'}
              {currentStatus === 'basic_completed' && '提交偏差详情'}
              {currentStatus === 'detail_completed' && '完成偏差'}
            </Button>
          </div>
        )}
      </Form>

      <div style={{ height: isMobile ? 80 : 0 }} />
    </div>
  )
}
