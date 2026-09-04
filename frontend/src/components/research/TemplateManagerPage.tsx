'use client'

import { useState, useEffect } from 'react'
import { Card, Button, Input, Select, App, Space, Table, Modal, Tabs } from 'antd'
import MDEditor from '@uiw/react-md-editor'
import { PlusOutlined, SaveOutlined } from '@ant-design/icons'

const { TextArea } = Input

export function TemplateManagerPage() {
  const { message } = App.useApp()
  const [templates, setTemplates] = useState<any[]>([])
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [currentMd, setCurrentMd] = useState('')
  const [templateName, setTemplateName] = useState('')
  const [category, setCategory] = useState('process_optimization')

  // 模拟加载模板（实际应调用 API）
  useEffect(() => {
    // fetch('/api/v1/research/templates/').then(...)
  }, [])

  const handleSave = async () => {
    if (!templateName || !currentMd) {
      message.warning('请填写模板名称和内容')
      return
    }
    
    try {
      // 调用后端保存接口
      // await fetch('/api/v1/research/templates/', { method: 'POST', body: ... })
      message.success('模板保存成功！')
      setIsModalOpen(false)
    } catch (e) {
      message.error('保存失败')
    }
  }

  const columns = [
    { title: '模板名称', dataIndex: 'name', key: 'name' },
    { title: '分类', dataIndex: 'category', key: 'category' },
    { 
      title: '操作', 
      key: 'action',
      render: (_: any, record: any) => (
        <Button type="link" onClick={() => {
          setCurrentMd(record.content_md)
          setTemplateName(record.name)
          setIsModalOpen(true)
        }}>编辑</Button>
      )
    },
  ]

  return (
    <div>
      <Card title="报告模板管理" extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setIsModalOpen(true)}>新建模板</Button>}>
        <Table dataSource={templates} columns={columns} rowKey="id" />
      </Card>

      <Modal
        title="编辑报告模板"
        open={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        width={1000}
        footer={[
          <Button key="cancel" onClick={() => setIsModalOpen(false)}>取消</Button>,
          <Button key="save" type="primary" icon={<SaveOutlined />} onClick={handleSave}>保存模板</Button>,
        ]}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Input placeholder="模板名称" value={templateName} onChange={e => setTemplateName(e.target.value)} />
          <Select value={category} onChange={setCategory} style={{ width: 200 }}>
            <Select.Option value="initiation">立项阶段</Select.Option>
            <Select.Option value="route_development">打通路线</Select.Option>
            <Select.Option value="process_optimization">工艺优化</Select.Option>
            <Select.Option value="pilot_study">中试研究</Select.Option>
            <Select.Option value="process_validation">工艺验证</Select.Option>
            <Select.Option value="registration_filing">申报资料</Select.Option>
            <Select.Option value="other">其他</Select.Option>
          </Select>
          <div data-color-mode="light">
            <MDEditor
              value={currentMd}
              onChange={(val) => setCurrentMd(val || "")}
              height={500}
              preview="live"
            />
          </div>
        </Space>
      </Modal>
    </div>
  )
}
