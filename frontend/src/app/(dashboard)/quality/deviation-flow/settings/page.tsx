'use client'

import { useState, useEffect } from 'react'
import { Button, Space, Input, Select, Tag, Typography, Modal, Form, message, Divider, Switch, Alert, Spin } from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, UserOutlined, TeamOutlined,
  BellOutlined, ThunderboltOutlined, FileTextOutlined, RobotOutlined, ReloadOutlined,
  CheckCircleFilled, CloseCircleFilled, SettingOutlined, MailOutlined,
} from '@ant-design/icons'
import { saveDeviationSetting, deleteDeviationSetting, toggleDeviationSetting, setDefaultDeviationTemplate } from '@/actions/deviation'
import './settings.css'

const { Text } = Typography

const API_BASE = '/api/v1'

const DEVIATION_TYPES = [
  { value: 'ipc_defect', label: 'IPC缺陷' },
  { value: 'foreign_object', label: '外来异物' },
  { value: 'calibration_maintenance', label: '校验/维修' },
  { value: 'mixup', label: '混淆' },
  { value: 'material_quality_defect', label: '物料缺陷' },
  { value: 'personnel_error', label: '人员失误' },
  { value: 'oos_result', label: '超标结果' },
  { value: 'documentation_defect', label: '文件缺陷' },
  { value: 'equipment_failure', label: '设备故障' },
  { value: 'environment', label: '环境' },
  { value: 'other', label: '其它' },
]

const URGENCY_LEVELS = [
  { value: 'normal', label: '一般' },
  { value: 'important', label: '重要' },
  { value: 'serious', label: '严重' },
]

const DEPARTMENTS = [
  { value: '生产部', label: '生产部' },
  { value: '质量部', label: '质量部' },
  { value: '工程部', label: '工程部' },
  { value: '仓储部', label: '仓储部' },
  { value: '采购部', label: '采购部' },
  { value: '研发部', label: '研发部' },
]

const TRIGGER_TYPES = [
  { value: 'report_uploaded', label: '报告上传' },
  { value: 'basic_completed', label: '基础完成' },
  { value: 'detail_completed', label: '详情完成' },
  { value: 'completed', label: '流程完成' },
  { value: 'capa_reminder', label: 'CAPA提醒' },
  { value: 'overdue_warning', label: '逾期预警' },
]

const TEMPLATE_TYPES = [
  { value: 'new_deviation', label: '新建通知' },
  { value: 'basic_completed', label: '基础完成通知' },
  { value: 'detail_completed', label: '详情完成通知' },
  { value: 'completed', label: '完成通知' },
  { value: 'capa_reminder', label: 'CAPA提醒' },
  { value: 'overdue_warning', label: '逾期预警' },
]

type SectionKey = 'qa' | 'leader' | 'rule' | 'trigger' | 'template' | 'bot'

const SECTIONS: { key: SectionKey; icon: React.ReactNode; title: string; desc: string }[] = [
  { key: 'qa', icon: <UserOutlined />, title: 'QA 人员', desc: '接收偏差提醒的 QA 人员' },
  { key: 'leader', icon: <TeamOutlined />, title: '部门负责人', desc: '各部门偏差负责人' },
  { key: 'rule', icon: <BellOutlined />, title: '提醒规则', desc: '偏差类型与等级规则' },
  { key: 'trigger', icon: <ThunderboltOutlined />, title: '自动触发', desc: '流程自动提醒配置' },
  { key: 'template', icon: <FileTextOutlined />, title: '消息模板', desc: '飞书消息内容模板' },
  { key: 'bot', icon: <RobotOutlined />, title: '飞书机器人', desc: '消息推送机器人配置' },
]

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span className={`status-badge ${active ? 'active' : 'inactive'}`}>
      {active ? <CheckCircleFilled /> : <CloseCircleFilled />}
      {active ? '启用' : '禁用'}
    </span>
  )
}

function UserCard({ item, onEdit, onToggle, onDelete }: {
  item: any
  onEdit: () => void
  onToggle: () => void
  onDelete: () => void
}) {
  return (
    <div className="setting-card">
      <div className="setting-card-main">
        <div className="setting-card-icon user-icon">
          <UserOutlined />
        </div>
        <div className="setting-card-info">
          <Text strong className="setting-card-name">{item.name}</Text>
          <Text type="secondary" className="setting-card-meta">{item.open_id}</Text>
          {item.department && <Tag color="blue" className="setting-card-tag">{item.department}</Tag>}
        </div>
        <StatusBadge active={item.is_active} />
      </div>
      <div className="setting-card-actions">
        <Button type="link" size="small" icon={<EditOutlined />} onClick={onEdit}>编辑</Button>
        <Button type="link" size="small" onClick={onToggle}>{item.is_active ? '禁用' : '启用'}</Button>
        <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={onDelete}>删除</Button>
      </div>
    </div>
  )
}

function RuleCard({ item, onEdit, onToggle, onDelete }: {
  item: any
  onEdit: () => void
  onToggle: () => void
  onDelete: () => void
}) {
  const typeLabel = DEVIATION_TYPES.find(t => t.value === item.deviation_type)?.label || item.deviation_type || '全部'
  const levelLabel = URGENCY_LEVELS.find(l => l.value === item.urgency_level)?.label || item.urgency_level || '全部'
  const levelColor = item.urgency_level === 'serious' ? 'red' : item.urgency_level === 'important' ? 'orange' : 'green'

  return (
    <div className="setting-card">
      <div className="setting-card-main">
        <div className="setting-card-icon rule-icon">
          <BellOutlined />
        </div>
        <div className="setting-card-info">
          <Space wrap size={4}>
            <Tag>{typeLabel}</Tag>
            <Tag color={levelColor}>{levelLabel}</Tag>
            {item.auto_reminder && <Tag color="purple">自动</Tag>}
          </Space>
          <Text type="secondary" className="setting-card-meta">
            提醒时间: {item.reminder_time}
          </Text>
        </div>
        <StatusBadge active={item.is_active} />
      </div>
      <div className="setting-card-actions">
        <Button type="link" size="small" icon={<EditOutlined />} onClick={onEdit}>编辑</Button>
        <Button type="link" size="small" onClick={onToggle}>{item.is_active ? '禁用' : '启用'}</Button>
        <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={onDelete}>删除</Button>
      </div>
    </div>
  )
}

function TriggerCard({ item, onEdit, onToggle, onDelete }: {
  item: any
  onEdit: () => void
  onToggle: () => void
  onDelete: () => void
}) {
  const typeLabel = TRIGGER_TYPES.find(t => t.value === item.trigger_type)?.label || item.trigger_type

  return (
    <div className="setting-card">
      <div className="setting-card-main">
        <div className="setting-card-icon trigger-icon">
          <ThunderboltOutlined />
        </div>
        <div className="setting-card-info">
          <Text strong className="setting-card-name">{typeLabel}</Text>
          {item.trigger_condition && (
            <Text type="secondary" className="setting-card-meta">{item.trigger_condition}</Text>
          )}
          <Space wrap size={4} className="setting-card-tags">
            {item.notify_qa && <Tag color="blue">QA</Tag>}
            {item.notify_leader && <Tag color="green">负责人</Tag>}
            {item.notify_reporter && <Tag color="orange">填报人</Tag>}
          </Space>
        </div>
        <StatusBadge active={item.is_enabled} />
      </div>
      <div className="setting-card-actions">
        <Button type="link" size="small" icon={<EditOutlined />} onClick={onEdit}>编辑</Button>
        <Button type="link" size="small" onClick={onToggle}>{item.is_enabled ? '禁用' : '启用'}</Button>
        <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={onDelete}>删除</Button>
      </div>
    </div>
  )
}

function TemplateCard({ item, onEdit, onToggle, onDelete, onSetDefault }: {
  item: any
  onEdit: () => void
  onToggle: () => void
  onDelete: () => void
  onSetDefault: () => void
}) {
  const typeLabel = TEMPLATE_TYPES.find(t => t.value === item.template_type)?.label || item.template_type

  return (
    <div className="setting-card">
      <div className="setting-card-main">
        <div className="setting-card-icon template-icon">
          <FileTextOutlined />
        </div>
        <div className="setting-card-info">
          <Space align="center" size={4}>
            <Text strong className="setting-card-name">{item.template_name}</Text>
            {item.is_default && <Tag color="gold">默认</Tag>}
          </Space>
          <Text type="secondary" className="setting-card-meta">{typeLabel}</Text>
          <Text type="secondary" className="setting-card-desc">{item.title_template}</Text>
        </div>
        <StatusBadge active={item.is_active} />
      </div>
      <div className="setting-card-actions">
        <Button type="link" size="small" icon={<EditOutlined />} onClick={onEdit}>编辑</Button>
        {!item.is_default && <Button type="link" size="small" onClick={onSetDefault}>设默认</Button>}
        <Button type="link" size="small" onClick={onToggle}>{item.is_active ? '禁用' : '启用'}</Button>
        <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={onDelete}>删除</Button>
      </div>
    </div>
  )
}

export default function DeviationSettingsPage() {
  const [loading, setLoading] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const [activeSection, setActiveSection] = useState<SectionKey>('qa')
  const [qaUsers, setQaUsers] = useState<any[]>([])
  const [leaders, setLeaders] = useState<any[]>([])
  const [rules, setRules] = useState<any[]>([])
  const [autoTriggers, setAutoTriggers] = useState<any[]>([])
  const [messageTemplates, setMessageTemplates] = useState<any[]>([])
  const [feishuBot, setFeishuBot] = useState<any>(null)

  const [qaModalVisible, setQaModalVisible] = useState(false)
  const [leaderModalVisible, setLeaderModalVisible] = useState(false)
  const [editingQA, setEditingQA] = useState<any>(null)
  const [editingLeader, setEditingLeader] = useState<any>(null)
  const [editingRule, setEditingRule] = useState<any>(null)
  const [ruleModalVisible, setRuleModalVisible] = useState(false)
  const [editingTrigger, setEditingTrigger] = useState<any>(null)
  const [triggerModalVisible, setTriggerModalVisible] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<any>(null)
  const [templateModalVisible, setTemplateModalVisible] = useState(false)
  const [botModalVisible, setBotModalVisible] = useState(false)

  const [form] = Form.useForm()
  const [templateForm] = Form.useForm()
  const [botForm] = Form.useForm()

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)')
    const update = () => setIsMobile(mq.matches)
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [qaRes, leaderRes, ruleRes, triggerRes, templateRes, botRes] = await Promise.all([
        fetch(`${API_BASE}/quality/deviation-settings/qa-users`),
        fetch(`${API_BASE}/quality/deviation-settings/leaders`),
        fetch(`${API_BASE}/quality/deviation-settings/rules`),
        fetch(`${API_BASE}/quality/deviation-settings/auto-triggers`),
        fetch(`${API_BASE}/quality/deviation-settings/message-templates`),
        fetch(`${API_BASE}/quality/deviation-settings/feishu-bot`),
      ])

      const [qaResult, leaderResult, ruleResult, triggerResult, templateResult, botResult] = await Promise.all([
        qaRes.json(), leaderRes.json(), ruleRes.json(),
        triggerRes.json(), templateRes.json(), botRes.json(),
      ])

      if (qaResult.code === 200) setQaUsers(qaResult.data || [])
      if (leaderResult.code === 200) setLeaders(leaderResult.data || [])
      if (ruleResult.code === 200) setRules(ruleResult.data || [])
      if (triggerResult.code === 200) setAutoTriggers(triggerResult.data || [])
      if (templateResult.code === 200) setMessageTemplates(templateResult.data || [])
      if (botResult.code === 200) setFeishuBot(botResult.data)
    } catch {
      message.error('加载数据失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async (url: string, method: string, values: any, successMsg: string) => {
    try {
      const result = await saveDeviationSetting(url, method, values)
      if (result.code === 200) {
        message.success(successMsg)
        loadData()
        return true
      } else {
        message.error(result.message || '操作失败')
        return false
      }
    } catch {
      message.error('操作失败')
      return false
    }
  }

  const handleDelete = async (url: string, successMsg: string) => {
    try {
      const result = await deleteDeviationSetting(url)
      if (result.code === 200) {
        message.success(successMsg)
        loadData()
      } else {
        message.error(result.message || '删除失败')
      }
    } catch {
      message.error('删除失败')
    }
  }

  const handleToggle = async (url: string) => {
    try {
      const result = await toggleDeviationSetting(url)
      if (result.code === 200) {
        message.success('状态切换成功')
        loadData()
      }
    } catch {
      message.error('操作失败')
    }
  }

  const queryFeishuUser = async (mobile: string, targetForm: any) => {
    if (!mobile) {
      message.warning('请输入手机号')
      return
    }
    try {
      const response = await fetch(`${API_BASE}/quality/deviation-settings/feishu-user/by-mobile?mobile=${mobile}`)
      const result = await response.json()
      if (result.code === 200 && result.data) {
        targetForm.setFieldsValue({
          name: result.data.name,
          open_id: result.data.open_id,
        })
        message.success(`已获取用户：${result.data.name}`)
      } else {
        message.warning(result.message || '未找到对应用户')
      }
    } catch {
      message.error('查询失败')
    }
  }

  const confirmDelete = (content: string, onOk: () => void) => {
    Modal.confirm({
      title: '确认删除',
      content,
      okText: '删除',
      okButtonProps: { danger: true },
      onOk,
    })
  }

  const getSectionData = () => {
    switch (activeSection) {
      case 'qa': return qaUsers
      case 'leader': return leaders
      case 'rule': return rules
      case 'trigger': return autoTriggers
      case 'template': return messageTemplates
      default: return []
    }
  }

  const renderSectionContent = () => {
    const data = getSectionData()
    const section = SECTIONS.find(s => s.key === activeSection)

    const renderEmpty = () => (
      <div className="setting-empty">
        <MailOutlined className="setting-empty-icon" />
        <Text type="secondary">暂无数据</Text>
      </div>
    )

    return (
      <div className="setting-section-content">
        <div className="setting-section-header">
          <div className="setting-section-title">
            <span className={`setting-section-icon ${activeSection}-icon`}>{section?.icon}</span>
            <span>{section?.title}</span>
            <Tag className="setting-count-tag">{data.length}</Tag>
          </div>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              form.resetFields()
              if (activeSection === 'qa') { setEditingQA(null); setQaModalVisible(true) }
              else if (activeSection === 'leader') { setEditingLeader(null); setLeaderModalVisible(true) }
              else if (activeSection === 'rule') { setEditingRule(null); setRuleModalVisible(true) }
              else if (activeSection === 'trigger') { setEditingTrigger(null); setTriggerModalVisible(true) }
              else if (activeSection === 'template') { setEditingTemplate(null); templateForm.resetFields(); setTemplateModalVisible(true) }
            }}
          >
            新增
          </Button>
        </div>

        <div className="setting-card-list">
          {data.length === 0 ? renderEmpty() : data.map((item: any) => {
            if (activeSection === 'qa') {
              return (
                <UserCard
                  key={item.id}
                  item={item}
                  onEdit={() => { setEditingQA(item); form.setFieldsValue(item); setQaModalVisible(true) }}
                  onToggle={() => handleToggle(`${API_BASE}/quality/deviation-settings/qa-users/${item.id}/toggle`)}
                  onDelete={() => confirmDelete(`删除 ${item.name}？`, () => handleDelete(`${API_BASE}/quality/deviation-settings/qa-users/${item.id}`, '删除成功'))}
                />
              )
            }
            if (activeSection === 'leader') {
              return (
                <UserCard
                  key={item.id}
                  item={item}
                  onEdit={() => { setEditingLeader(item); form.setFieldsValue(item); setLeaderModalVisible(true) }}
                  onToggle={() => handleToggle(`${API_BASE}/quality/deviation-settings/leaders/${item.id}/toggle`)}
                  onDelete={() => confirmDelete(`删除 ${item.name}？`, () => handleDelete(`${API_BASE}/quality/deviation-settings/leaders/${item.id}`, '删除成功'))}
                />
              )
            }
            if (activeSection === 'rule') {
              return (
                <RuleCard
                  key={item.id}
                  item={item}
                  onEdit={() => { setEditingRule(item); form.setFieldsValue(item); setRuleModalVisible(true) }}
                  onToggle={() => handleToggle(`${API_BASE}/quality/deviation-settings/rules/${item.id}/toggle`)}
                  onDelete={() => confirmDelete('删除该规则？', () => handleDelete(`${API_BASE}/quality/deviation-settings/rules/${item.id}`, '删除成功'))}
                />
              )
            }
            if (activeSection === 'trigger') {
              return (
                <TriggerCard
                  key={item.id}
                  item={item}
                  onEdit={() => { setEditingTrigger(item); form.setFieldsValue(item); setTriggerModalVisible(true) }}
                  onToggle={() => handleToggle(`${API_BASE}/quality/deviation-settings/auto-triggers/${item.id}/toggle`)}
                  onDelete={() => confirmDelete('删除该配置？', () => handleDelete(`${API_BASE}/quality/deviation-settings/auto-triggers/${item.id}`, '删除成功'))}
                />
              )
            }
            if (activeSection === 'template') {
              return (
                <TemplateCard
                  key={item.id}
                  item={item}
                  onEdit={() => { setEditingTemplate(item); templateForm.setFieldsValue(item); setTemplateModalVisible(true) }}
                  onToggle={() => handleToggle(`${API_BASE}/quality/deviation-settings/message-templates/${item.id}/toggle`)}
                  onDelete={() => confirmDelete('删除该模板？', () => handleDelete(`${API_BASE}/quality/deviation-settings/message-templates/${item.id}`, '删除成功'))}
                  onSetDefault={async () => {
                    const r = await setDefaultDeviationTemplate(item.id)
                    if (r.code === 200) { message.success('设置成功'); loadData() }
                  }}
                />
              )
            }
            return null
          })}
        </div>
      </div>
    )
  }

  const renderBotContent = () => (
    <div className="setting-section-content">
      <div className="setting-section-header">
        <div className="setting-section-title">
          <span className="setting-section-icon bot-icon"><RobotOutlined /></span>
          <span>飞书机器人</span>
        </div>
      </div>

      {feishuBot ? (
        <div className="bot-config-card">
          <div className="bot-config-header">
            <div className="bot-config-avatar">
              <RobotOutlined />
            </div>
            <div className="bot-config-title">
              <Text strong>{feishuBot.bot_name || '飞书机器人'}</Text>
              <StatusBadge active={feishuBot.is_enabled} />
            </div>
          </div>
          <div className="bot-config-body">
            <div className="bot-config-row">
              <Text type="secondary">App ID</Text>
              <Text copyable style={{ fontFamily: 'monospace' }}>{feishuBot.app_id}</Text>
            </div>
            <div className="bot-config-row">
              <Text type="secondary">App Secret</Text>
              <Text type="secondary">已配置</Text>
            </div>
            {feishuBot.bot_token && (
              <div className="bot-config-row">
                <Text type="secondary">Bot Token</Text>
                <Text copyable style={{ fontFamily: 'monospace' }}>{feishuBot.bot_token}</Text>
              </div>
            )}
          </div>
          <div className="bot-config-footer">
            <Button type="primary" icon={<EditOutlined />} onClick={() => { botForm.setFieldsValue(feishuBot); setBotModalVisible(true) }}>修改</Button>
            <Button onClick={() => handleToggle(`${API_BASE}/quality/deviation-settings/feishu-bot/toggle`)}>
              {feishuBot.is_enabled ? '禁用' : '启用'}
            </Button>
            <Button danger icon={<DeleteOutlined />} onClick={() => confirmDelete('删除机器人配置？', () => handleDelete(`${API_BASE}/quality/deviation-settings/feishu-bot`, '删除成功'))}>
              删除
            </Button>
          </div>
        </div>
      ) : (
        <div className="setting-empty bot-empty">
          <RobotOutlined className="setting-empty-icon" />
          <Text type="secondary">尚未配置飞书机器人</Text>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { botForm.resetFields(); setBotModalVisible(true) }}>添加配置</Button>
        </div>
      )}
    </div>
  )

  return (
    <div className="settings-page">
      <div className="settings-header">
        <div className="settings-header-content">
          <SettingOutlined className="settings-header-icon" />
          <div>
            <h1>偏差提醒设置</h1>
            <p>配置提醒人员、规则和消息模板</p>
          </div>
        </div>
        <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
          刷新
        </Button>
      </div>

      <div className="settings-nav">
        {SECTIONS.map(section => (
          <button
            key={section.key}
            className={`settings-nav-item ${activeSection === section.key ? 'active' : ''}`}
            onClick={() => setActiveSection(section.key)}
          >
            {section.icon}
            <span>{section.title}</span>
          </button>
        ))}
      </div>

      <Spin spinning={loading}>
        <div className="settings-content">
          {activeSection === 'bot' ? renderBotContent() : renderSectionContent()}
        </div>
      </Spin>

      <Modal
        title={editingQA ? '编辑 QA 人员' : '添加 QA 人员'}
        open={qaModalVisible}
        onOk={async () => {
          const values = await form.validateFields()
          const url = editingQA ? `${API_BASE}/quality/deviation-settings/qa-users/${editingQA.id}` : `${API_BASE}/quality/deviation-settings/qa-users`
          if (await handleSave(url, editingQA ? 'PUT' : 'POST', values, editingQA ? '更新成功' : '添加成功')) {
            setQaModalVisible(false)
          }
        }}
        onCancel={() => setQaModalVisible(false)}
        width={isMobile ? '95vw' : 480}
        className="settings-modal"
      >
        <Alert title="输入手机号查询，自动获取飞书用户信息" type="info" showIcon style={{ marginBottom: 16 }} />
        <Form form={form} layout="vertical">
          <Form.Item label="手机号">
            <Space.Compact style={{ width: '100%' }}>
              <Form.Item name="mobile" noStyle><Input placeholder="请输入手机号" /></Form.Item>
              <Button type="primary" onClick={() => queryFeishuUser(form.getFieldValue('mobile'), form)}>查询</Button>
            </Space.Compact>
          </Form.Item>
          <Form.Item name="name" label="姓名" rules={[{ required: true }]}>
            <Input placeholder="查询后自动填充" />
          </Form.Item>
          <Form.Item name="open_id" label="飞书 OpenID" rules={[{ required: true }]}>
            <Input placeholder="查询后自动填充" disabled />
          </Form.Item>
          <Form.Item name="department" label="部门">
            <Select placeholder="选择部门" allowClear>
              {DEPARTMENTS.map(d => <Select.Option key={d.value} value={d.value}>{d.label}</Select.Option>)}
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={editingLeader ? '编辑部门负责人' : '添加部门负责人'}
        open={leaderModalVisible}
        onOk={async () => {
          const values = await form.validateFields()
          const url = editingLeader ? `${API_BASE}/quality/deviation-settings/leaders/${editingLeader.id}` : `${API_BASE}/quality/deviation-settings/leaders`
          if (await handleSave(url, editingLeader ? 'PUT' : 'POST', values, editingLeader ? '更新成功' : '添加成功')) {
            setLeaderModalVisible(false)
          }
        }}
        onCancel={() => setLeaderModalVisible(false)}
        width={isMobile ? '95vw' : 480}
        className="settings-modal"
      >
        <Alert title="输入手机号查询，自动获取飞书用户信息" type="info" showIcon style={{ marginBottom: 16 }} />
        <Form form={form} layout="vertical">
          <Form.Item label="手机号">
            <Space.Compact style={{ width: '100%' }}>
              <Form.Item name="mobile" noStyle><Input placeholder="请输入手机号" /></Form.Item>
              <Button type="primary" onClick={() => queryFeishuUser(form.getFieldValue('mobile'), form)}>查询</Button>
            </Space.Compact>
          </Form.Item>
          <Form.Item name="name" label="姓名" rules={[{ required: true }]}>
            <Input placeholder="查询后自动填充" />
          </Form.Item>
          <Form.Item name="open_id" label="飞书 OpenID" rules={[{ required: true }]}>
            <Input placeholder="查询后自动填充" disabled />
          </Form.Item>
          <Form.Item name="department" label="负责部门" rules={[{ required: true }]}>
            <Select placeholder="选择部门">
              {DEPARTMENTS.map(d => <Select.Option key={d.value} value={d.value}>{d.label}</Select.Option>)}
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={editingRule ? '编辑提醒规则' : '添加提醒规则'}
        open={ruleModalVisible}
        onOk={async () => {
          const values = await form.validateFields()
          const url = editingRule ? `${API_BASE}/quality/deviation-settings/rules/${editingRule.id}` : `${API_BASE}/quality/deviation-settings/rules`
          if (await handleSave(url, editingRule ? 'PUT' : 'POST', values, editingRule ? '更新成功' : '添加成功')) {
            setRuleModalVisible(false)
          }
        }}
        onCancel={() => setRuleModalVisible(false)}
        width={isMobile ? '95vw' : 520}
        className="settings-modal"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="deviation_type" label="偏差类型">
            <Select placeholder="全部类型" allowClear>
              {DEVIATION_TYPES.map(t => <Select.Option key={t.value} value={t.value}>{t.label}</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="urgency_level" label="紧急等级">
            <Select placeholder="全部等级" allowClear>
              {URGENCY_LEVELS.map(l => <Select.Option key={l.value} value={l.value}>{l.label}</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="reminder_time" label="提醒时间" rules={[{ required: true }]} initialValue="08:30">
            <Input placeholder="格式：HH:mm" />
          </Form.Item>
          <Form.Item name="auto_reminder" label="自动提醒" valuePropName="checked" initialValue={true}>
            <Switch checkedChildren="开" unCheckedChildren="关" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={editingTrigger ? '编辑触发配置' : '添加触发配置'}
        open={triggerModalVisible}
        onOk={async () => {
          const values = await form.validateFields()
          const url = editingTrigger ? `${API_BASE}/quality/deviation-settings/auto-triggers/${editingTrigger.id}` : `${API_BASE}/quality/deviation-settings/auto-triggers`
          if (await handleSave(url, editingTrigger ? 'PUT' : 'POST', values, editingTrigger ? '更新成功' : '添加成功')) {
            setTriggerModalVisible(false)
          }
        }}
        onCancel={() => setTriggerModalVisible(false)}
        width={isMobile ? '95vw' : 520}
        className="settings-modal"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="trigger_type" label="触发类型" rules={[{ required: true }]}>
            <Select placeholder="选择触发类型">
              {TRIGGER_TYPES.map(t => <Select.Option key={t.value} value={t.value}>{t.label}</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="trigger_condition" label="触发条件">
            <Input placeholder="如：偏差类型=生产偏差" />
          </Form.Item>
          <Divider plain style={{ fontSize: 12 }}>通知对象</Divider>
          <Form.Item name="notify_qa" label="通知 QA 人员" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
          <Form.Item name="notify_leader" label="通知部门负责人" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
          <Form.Item name="notify_reporter" label="通知填报人" valuePropName="checked" initialValue={false}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={editingTemplate ? '编辑消息模板' : '添加消息模板'}
        open={templateModalVisible}
        onOk={async () => {
          const values = await templateForm.validateFields()
          const url = editingTemplate ? `${API_BASE}/quality/deviation-settings/message-templates/${editingTemplate.id}` : `${API_BASE}/quality/deviation-settings/message-templates`
          if (await handleSave(url, editingTemplate ? 'PUT' : 'POST', values, editingTemplate ? '更新成功' : '添加成功')) {
            setTemplateModalVisible(false)
          }
        }}
        onCancel={() => setTemplateModalVisible(false)}
        width={isMobile ? '95vw' : 600}
        className="settings-modal"
      >
        <Form form={templateForm} layout="vertical">
          <Form.Item name="template_type" label="模板类型" rules={[{ required: true }]}>
            <Select placeholder="选择模板类型">
              {TEMPLATE_TYPES.map(t => <Select.Option key={t.value} value={t.value}>{t.label}</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="template_name" label="模板名称" rules={[{ required: true }]}>
            <Input placeholder="如：紧急偏差通知模板" />
          </Form.Item>
          <Form.Item name="title_template" label="标题模板" rules={[{ required: true }]}>
            <Input placeholder='【偏差提醒】{{deviation_no}}' />
          </Form.Item>
          <Form.Item name="content_template" label="内容模板" rules={[{ required: true }]}>
            <Input.TextArea rows={5} placeholder="支持变量：{{deviation_no}}、{{theme}}、{{urgency_level}}等" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={feishuBot ? '修改飞书机器人' : '添加飞书机器人'}
        open={botModalVisible}
        onOk={async () => {
          const values = await botForm.validateFields()
          if (await handleSave(`${API_BASE}/quality/deviation-settings/feishu-bot`, feishuBot ? 'PUT' : 'POST', values, feishuBot ? '更新成功' : '添加成功')) {
            setBotModalVisible(false)
          }
        }}
        onCancel={() => setBotModalVisible(false)}
        width={isMobile ? '95vw' : 520}
        className="settings-modal"
      >
        <Alert title="前往飞书开放平台创建企业自建应用，获取 App ID 和 App Secret" type="info" showIcon style={{ marginBottom: 16 }} />
        <Form form={botForm} layout="vertical">
          <Form.Item name="bot_name" label="机器人名称">
            <Input placeholder="如：偏差管理机器人" />
          </Form.Item>
          <Form.Item name="app_id" label="App ID" rules={[{ required: true }]}>
            <Input placeholder="如：cli_xxxxxxxxxxxxxx" />
          </Form.Item>
          <Form.Item name="app_secret" label="App Secret" rules={[{ required: true }]}>
            <Input.Password placeholder="不修改请留空" />
          </Form.Item>
          <Divider plain style={{ fontSize: 12 }}>可选配置</Divider>
          <Form.Item name="bot_token" label="Bot Token">
            <Input.Password placeholder="Webhook 机器人的 Bot Token" />
          </Form.Item>
          <Form.Item name="encrypt_key" label="加密密钥">
            <Input.Password placeholder="用于消息加密" />
          </Form.Item>
          <Form.Item name="verification_token" label="验证 Token">
            <Input.Password placeholder="用于回调验证" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
